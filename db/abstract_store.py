from abc import ABC, abstractmethod
from typing import Optional

__all__ = ["PAGE_STATUS", "CATEGORY", "AbstractStore"]

PAGE_STATUS = {
    "PENDING": 0,
    "PROCESSING": 1,
    "DONE": 2,
    "FAILED": 3,
}

CATEGORY = {
    "included": 1,
    "unplaced": 2,
    "hybrid": 3,
    "fossil_included": 4,
    "fossil_unplaced": 5,
    "scientific_synonyms": 6,
}


class AbstractStore(ABC):
    @abstractmethod
    def pop(self) -> Optional[str]:
        pass

    @abstractmethod
    def push(self, page_id: str) -> bool:
        pass

    @abstractmethod
    def mark_done(self, page_id: str) -> None:
        pass

    @abstractmethod
    def mark_failed(self, page_id: str) -> None:
        pass

    @abstractmethod
    def write(self, item: dict) -> None:
        pass

    @abstractmethod
    def close(self) -> None:
        pass

    @abstractmethod
    def __len__(self) -> int:
        pass
