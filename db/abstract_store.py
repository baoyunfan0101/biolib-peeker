from abc import ABC, abstractmethod
from typing import Optional

__all__ = ['AbstractStore', 'PAGE_STATUS', 'CATEGORY', 'RANK']

PAGE_STATUS = {
    'PENDING': 0,
    'PROCESSING': 1,
    'DONE': 2,
    'FAILED': 3,
}

CATEGORY = {
    'included': 10,
    'unplaced': 20,
    'hybrids': 30,
    'fossil_included': 40,
    'fossil_unplaced': 41,
    'nomina_dubia': 50,
    'nomina_nuda': 51,
    'synonyms': 100,
    'synonyms_included': 110,
    'synonyms_nomen_nudum': 111,
    'synonyms_partim.': 112,
    'synonyms_misspelling': 113,
    'unjustified_emendation': 120,
    'unjustified_replacement_name': 121,
}

RANK = {  # sorted by hierarchy
    'root': 1,
    'system': 10,
    'domain': 30,
    'superregnum': 50,
    'regnum': 51,
    'subregnum': 52,
    'kingdom': 60,
    'divisio': 70,
    'subdivisio': 80,
    'superphylum': 100,
    'phylum': 101,
    'subphylum': 102,
    'infraphylum': 103,
    'superclassis': 200,
    'class': 201,
    'subclass': 202,
    'infraclass': 203,
    'cohor': 250,
    'superorder': 300,
    'order': 301,
    'suborder': 302,
    'infraorder': 303,
    'parvorder': 304,
    'falanga': 350,
    'superfamily': 400,
    'family': 401,
    'subfamily': 402,
    'supertribus': 450,
    'tribus': 451,
    'subtribus': 452,
    'intergeneric': 500,
    'genus': 501,
    'subgenus': 502,
    'section': 503,
    'species': 601,
    'subspecies': 610,
    'varietas': 620,
    'form': 621,
    'cultivar': 622,
    'agregate': 630,
    'chimera': 631,
    'group': 640,
    'hybrid': 650,
}


class AbstractStore(ABC):
    @abstractmethod
    def pop(self) -> Optional[int]:
        pass

    @abstractmethod
    def push(self, page_id: int) -> bool:
        pass

    @abstractmethod
    def mark_done(self, page_id: int) -> None:
        pass

    @abstractmethod
    def mark_failed(self, page_id: int) -> None:
        pass

    @abstractmethod
    def write_taxa(self, item: dict) -> None:
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
