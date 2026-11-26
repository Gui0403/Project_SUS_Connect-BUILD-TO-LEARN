from typing import Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel

T = TypeVar("T")


class PageParams:
    """Parâmetros de paginação: ?limit=20&offset=0 (máximo 100 por página)."""

    def __init__(
        self,
        limit: int = Query(20, ge=1, le=100),
        offset: int = Query(0, ge=0),
    ):
        self.limit = limit
        self.offset = offset

class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int
    