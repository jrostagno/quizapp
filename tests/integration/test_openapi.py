from httpx import AsyncClient

EXPECTED_TAGS = {"health", "quizzes", "attempts", "users"}

SCHEMAS_REQUIRING_EXAMPLES = [
    "QuizCreate",
    "QuizDetail",
    "QuizListItem",
    "AttemptStartRequest",
    "AttemptStartResponse",
    "AttemptSubmitRequest",
    "AttemptResult",
    "AttemptDetail",
    "AttemptListItem",
    "UserStats",
    "UserRead",
]


async def test_openapi_has_all_expected_tags_with_descriptions(client: AsyncClient) -> None:
    response = await client.get("/openapi.json")
    assert response.status_code == 200

    spec = response.json()
    tags = spec.get("tags", [])
    tag_names = {tag["name"] for tag in tags}
    assert tag_names >= EXPECTED_TAGS

    for tag in tags:
        assert tag.get("description"), f"tag {tag['name']} missing description"


async def test_openapi_every_operation_has_summary_and_tags(client: AsyncClient) -> None:
    response = await client.get("/openapi.json")
    spec = response.json()

    for path, methods in spec["paths"].items():
        for method, op in methods.items():
            assert op.get("summary"), f"{method.upper()} {path} missing summary"
            assert op.get("tags"), f"{method.upper()} {path} missing tags"


async def test_openapi_key_schemas_have_examples(client: AsyncClient) -> None:
    response = await client.get("/openapi.json")
    spec = response.json()
    schemas = spec["components"]["schemas"]

    for name in SCHEMAS_REQUIRING_EXAMPLES:
        schema = schemas.get(name)
        assert schema is not None, f"schema {name} missing from OpenAPI"
        assert schema.get("examples"), f"schema {name} has no examples"
