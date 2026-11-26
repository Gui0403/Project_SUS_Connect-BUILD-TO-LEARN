"""Armazenamento de arquivos atrás de uma interface (ADR-05).

Hoje guarda em disco (um volume do Docker). Trocar por S3 depois significa escrever
outra classe com os mesmos 3 métodos, sem mexer em rotas nem regras de negócio.
"""

from functools import lru_cache
from pathlib import Path
from typing import Protocol

from app.config import settings


class FileStorage(Protocol):
    def save(self, key: str, data: bytes) -> None: ...

    def read(self, key: str) -> bytes: ...

    def delete(self, key: str) -> None: ...

class LocalFileStorage:
    def __init__(self, base_dir: str):
        self._base = Path(base_dir).resolve()
        self._base.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        path = (self._base / key ).resolve()
        if path.parent != self._base: #impede "../" e subpastas inesperadas
            raise ValueError("invalid storage key")
        return path

    def save(self, key: str, data: bytes) -> None:
        self._path(key).write_bytes(data)

    def read(self,key: str) -> bytes:
        return self._path(key).read_bytes()

    def delete(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)

@lru_cache
def get_storage() -> FileStorage:
    """Dependência do FastAPI: pode ser trocada nos testes ou por outra implementação."""
    return LocalFileStorage(settings.exam_storage_dir)