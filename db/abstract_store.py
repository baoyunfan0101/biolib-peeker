from abc import ABC, abstractmethod
from typing import Optional

__all__ = ["AbstractStore", "CATEGORY"]

CATEGORY = {
    "included": 10,
    "unplaced": 20,
    "hybrids": 30,
    "fossil_included": 40,
    "fossil_unplaced": 41,
    "nomina_dubia": 50,
    "nomina_nuda": 51,
    "synonyms": 100,
    "synonyms_included": 110,
    "synonyms_nomen_nudum": 111,
    "synonyms_partim.": 112,
    "synonyms_misspelling": 113,
    "unjustified_emendation": 120,
    "unjustified_replacement_name": 121,
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
    def write_synonym(self, item: dict) -> None:
        pass

    @abstractmethod
    def close(self) -> None:
        pass

    @abstractmethod
    def __len__(self) -> int:
        pass
