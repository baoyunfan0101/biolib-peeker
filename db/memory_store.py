import csv
from collections import deque
from pathlib import Path
from typing import Optional
from db.abstract_store import *

TAXA_NAME = 'taxa.csv'
SYNONYM_NAME = 'synonyms.csv'


class MemoryStore(AbstractStore):

    def __init__(
            self,
            path: str = './data',
            reset: bool = False,
    ) -> None:
        self.queue = deque()
        self.seen = set()
        self.processing = set()
        self.done = set()
        self.failed = set()

        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        taxa_path = path / TAXA_NAME
        synonym_path = path / SYNONYM_NAME

        if reset:
            if taxa_path.exists():
                taxa_path.unlink()
            if synonym_path.exists():
                synonym_path.unlink()

        self.taxa_file = open(taxa_path, 'a', newline='', encoding='utf-8')
        self.synonym_file = open(synonym_path, 'a', newline='', encoding='utf-8')

        self.taxa_writer = csv.DictWriter(
            self.taxa_file,
            fieldnames=[
                'id',
                'parent',
                'category',
                'rank',
                'scientific_name',
                'authority_year',
                'geological_range',
                'english_name',
            ]
        )
        self.synonym_writer = csv.DictWriter(
            self.synonym_file,
            fieldnames=[
                'parent',
                'category',
                'synonym',
                'authority_year',
            ]
        )

        if taxa_path.stat().st_size == 0:
            self.taxa_writer.writeheader()
        if synonym_path.stat().st_size == 0:
            self.synonym_writer.writeheader()

        self.taxa_writer.writerow({
            'id': 14772,
            'parent': -1,
            'category': CATEGORY['included'],
            'rank': RANK['root'],
            'scientific_name': 'Vitae',
            'authority_year': '',
            'geological_range': '',
            'english_name': 'living organisms',
        })
        self.taxa_file.flush()

    def pop(self) -> Optional[int]:
        while self.queue:
            page_id = self.queue.popleft()
            if page_id in self.done:
                continue
            self.processing.add(page_id)
            return page_id

        return None

    def push(self, page_id: int) -> bool:
        if page_id in self.seen:
            return False
        self.seen.add(page_id)
        self.queue.append(page_id)

        return True

    def mark_done(self, page_id: int) -> None:
        self.processing.discard(page_id)
        self.done.add(page_id)

    def mark_failed(self, page_id: int) -> None:
        self.processing.discard(page_id)
        self.failed.add(page_id)

    def write_taxa(self, item: dict) -> None:
        self.taxa_writer.writerow({
            'id': item['id'],
            'parent': item['parent'],
            'category': CATEGORY.get(item['category']),
            'rank': RANK.get(item['rank']),
            'scientific_name': item['scientific_name'],
            'authority_year': item['authority_year'],
            'geological_range': item['geological_range'],
            'english_name': item['english_name'],
        })
        self.taxa_file.flush()

    def write_synonym(self, item: dict) -> None:
        self.synonym_writer.writerow({
            'parent': item['parent'],
            'category': CATEGORY.get(item['category']),
            'synonym': item['scientific_name'],
            'authority_year': item['authority_year'],
        })
        self.synonym_file.flush()

    def close(self) -> None:
        self.taxa_file.close()
        self.synonym_file.close()

    def __len__(self) -> int:
        return len(self.queue)
