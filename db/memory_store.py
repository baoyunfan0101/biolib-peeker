import csv
from collections import deque
from pathlib import Path
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

    def pop(
            self,
            limit: int,
    ) -> list[int]:
        if limit <= 0:
            return []

        page_ids = []

        while self.queue and len(page_ids) < limit:
            page_id = self.queue.popleft()

            if page_id in self.done:
                continue

            self.processing.add(page_id)
            page_ids.append(page_id)

        return page_ids

    def push(
            self,
            page_ids: list[int],
    ) -> int:
        if not page_ids:
            return 0

        inserted = 0

        for page_id in page_ids:
            if page_id in self.seen:
                continue

            self.seen.add(page_id)
            self.queue.append(page_id)
            inserted += 1

        return inserted

    def mark_done(
            self,
            page_ids: list[int],
    ) -> int:
        if not page_ids:
            return 0

        updated = 0

        for page_id in page_ids:
            self.processing.discard(page_id)

            if page_id not in self.done:
                self.done.add(page_id)
                updated += 1

        return updated

    def mark_failed(
            self,
            page_ids: list[int],
    ) -> int:
        if not page_ids:
            return 0

        updated = 0

        for page_id in page_ids:
            self.processing.discard(page_id)

            if page_id not in self.failed:
                self.failed.add(page_id)
                updated += 1

        return updated

    def write_taxa(
            self,
            items: list[dict],
    ) -> int:
        if not items:
            return 0

        for item in items:
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

        return len(items)

    def write_synonym(
            self,
            items: list[dict],
    ) -> int:
        if not items:
            return 0

        for item in items:
            self.synonym_writer.writerow({
                'parent': item['parent'],
                'category': CATEGORY.get(item['category']),
                'synonym': item['scientific_name'],
                'authority_year': item['authority_year'],
            })

        self.synonym_file.flush()

        return len(items)

    def close(self) -> None:
        self.taxa_file.close()
        self.synonym_file.close()

    def __len__(self) -> int:
        return len(self.queue)
