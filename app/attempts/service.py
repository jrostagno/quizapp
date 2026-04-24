from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.attempts.models import Answer, Attempt
from app.attempts.repository import AttemptRepository
from app.attempts.schemas import (
    AnswerSubmission,
    AttemptDetail,
    AttemptQuestionDetail,
    AttemptResult,
    AttemptStartRequest,
    AttemptSubmitRequest,
    QuestionResult,
)
from app.attempts.scoring import compute_percentage, feedback_for_percentage
from app.core.errors import (
    AttemptAlreadySubmittedError,
    AttemptNotFoundError,
    InvalidAnswerSubmissionError,
)
from app.notifications.service import NotificationService
from app.quizzes.models import Option, Quiz
from app.quizzes.service import QuizService
from app.users.models import User
from app.users.service import UserService


class AttemptService:
    def __init__(
        self,
        repository: AttemptRepository,
        user_service: UserService,
        quiz_service: QuizService,
        notification_service: NotificationService,
        session: AsyncSession,
    ) -> None:
        self.repository = repository
        self.user_service = user_service
        self.quiz_service = quiz_service
        self.notification_service = notification_service
        self.session = session

    async def start_attempt(self, data: AttemptStartRequest) -> tuple[Attempt, User, Quiz]:
        quiz = await self.quiz_service.get_quiz(data.quiz_id)
        user = await self.user_service.upsert_by_email(name=data.name, email=data.email)

        attempt = Attempt(user_id=user.id, quiz_id=quiz.id)
        await self.repository.add(attempt)
        await self.session.commit()
        await self.session.refresh(attempt)

        return attempt, user, quiz

    async def submit_attempt(self, attempt_id: int, data: AttemptSubmitRequest) -> AttemptResult:
        attempt = await self.repository.get_with_quiz(attempt_id)
        if attempt is None:
            raise AttemptNotFoundError(attempt_id)
        if attempt.submitted_at is not None:
            raise AttemptAlreadySubmittedError(attempt_id)

        self._validate_submission(attempt.quiz, data.answers)

        correct_by_question: dict[int, Option] = {}
        options_by_id: dict[int, Option] = {}
        for question in attempt.quiz.questions:
            for option in question.options:
                options_by_id[option.id] = option
                if option.is_correct:
                    correct_by_question[question.id] = option

        questions_by_id = {q.id: q for q in attempt.quiz.questions}

        score = 0
        answer_rows: list[Answer] = []
        question_results: list[QuestionResult] = []

        for submission in data.answers:
            question = questions_by_id[submission.question_id]
            selected = options_by_id[submission.option_id]
            correct = correct_by_question[submission.question_id]
            is_correct = selected.id == correct.id
            if is_correct:
                score += 1

            answer_rows.append(
                Answer(
                    attempt_id=attempt.id,
                    question_id=submission.question_id,
                    option_id=submission.option_id,
                )
            )
            question_results.append(
                QuestionResult(
                    question_id=submission.question_id,
                    selected_option_id=submission.option_id,
                    correct_option_id=correct.id,
                    is_correct=is_correct,
                    explanation=question.explanation,
                )
            )

        total = len(attempt.quiz.questions)
        percentage = compute_percentage(score, total)
        feedback = feedback_for_percentage(percentage)
        submitted_at = datetime.now(UTC)

        attempt.submitted_at = submitted_at
        attempt.score = score
        attempt.percentage = percentage

        self.repository.add_answers(answer_rows)
        await self.notification_service.queue_for_attempt(attempt.id)

        await self.session.commit()

        question_results.sort(key=lambda r: questions_by_id[r.question_id].position)

        return AttemptResult(
            attempt_id=attempt.id,
            submitted_at=submitted_at,
            score=score,
            total=total,
            percentage=percentage,
            feedback=feedback,
            questions=question_results,
        )

    async def get_attempt_detail(self, attempt_id: int) -> AttemptDetail:
        attempt = await self.repository.get_detail(attempt_id)
        if attempt is None:
            raise AttemptNotFoundError(attempt_id)

        quiz = attempt.quiz
        questions_by_id = {q.id: q for q in quiz.questions}
        options_by_id = {opt.id: opt for q in quiz.questions for opt in q.options}
        correct_by_question: dict[int, int] = {}
        for question in quiz.questions:
            for option in question.options:
                if option.is_correct:
                    correct_by_question[question.id] = option.id

        question_details: list[AttemptQuestionDetail] = []
        if attempt.submitted_at is not None:
            for answer in attempt.answers:
                question = questions_by_id[answer.question_id]
                selected = options_by_id[answer.option_id]
                correct_id = correct_by_question[question.id]
                question_details.append(
                    AttemptQuestionDetail(
                        question_id=question.id,
                        body=question.body,
                        position=question.position,
                        selected_option_id=selected.id,
                        correct_option_id=correct_id,
                        is_correct=selected.id == correct_id,
                        explanation=question.explanation,
                    )
                )
            question_details.sort(key=lambda q: q.position)

        feedback = (
            feedback_for_percentage(attempt.percentage) if attempt.percentage is not None else None
        )

        return AttemptDetail(
            id=attempt.id,
            user_id=attempt.user_id,
            quiz_id=quiz.id,
            quiz_title=quiz.title,
            started_at=attempt.started_at,
            submitted_at=attempt.submitted_at,
            score=attempt.score,
            total=len(quiz.questions),
            percentage=attempt.percentage,
            feedback=feedback,
            questions=question_details,
        )

    @staticmethod
    def _validate_submission(quiz: Quiz, answers: list[AnswerSubmission]) -> None:
        question_ids = {q.id for q in quiz.questions}
        answered_ids = [a.question_id for a in answers]

        if len(set(answered_ids)) != len(answered_ids):
            raise InvalidAnswerSubmissionError(
                "Duplicate question_id in answers.",
                details={"answered_ids": answered_ids},
            )

        answered_set = set(answered_ids)
        if answered_set != question_ids:
            missing = sorted(question_ids - answered_set)
            extra = sorted(answered_set - question_ids)
            raise InvalidAnswerSubmissionError(
                "Answers must cover exactly the quiz's questions.",
                details={"missing": missing, "extra": extra},
            )

        options_by_question: dict[int, set[int]] = {
            q.id: {opt.id for opt in q.options} for q in quiz.questions
        }
        for answer in answers:
            if answer.option_id not in options_by_question[answer.question_id]:
                raise InvalidAnswerSubmissionError(
                    (
                        f"option_id {answer.option_id} does not belong to "
                        f"question_id {answer.question_id}."
                    ),
                    details={
                        "question_id": answer.question_id,
                        "option_id": answer.option_id,
                    },
                )
