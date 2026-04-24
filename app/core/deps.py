from typing import Annotated

from arq.connections import ArqRedis
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session


def get_arq_pool(request: Request) -> ArqRedis | None:
    return getattr(request.app.state, "arq_pool", None)


SessionDep = Annotated[AsyncSession, Depends(get_session)]
ArqPoolDep = Annotated[ArqRedis | None, Depends(get_arq_pool)]
