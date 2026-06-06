import csv
from collections import deque
from pathlib import Path
from typing import Optional
from db.abstract_store import *

CSV_NAME = "taxa.csv"


class MemoryStore(AbstractStore):

    def __init__(
            self,
            path: str = "./data",
            reset: bool = False,
    ) -> None:
        self.q = deque()
        self.s = set()

        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)

        csv_path = path / CSV_NAME

        if reset and csv_path.exists():
            csv_path.unlink()

        self.file = open(csv_path, "a", newline="", encoding="utf-8")

        self.writer = csv.DictWriter(
            self.file,
            fieldnames=[
                "id",
                "parent",
                "category",
                "rank",
                "scientific_name",
                "authority_year",
                "geological_range",
                "english_name",
            ]
        )

        if csv_path.stat().st_size == 0:
            self.writer.writeheader()

    def pop(self) -> Optional[str]:
        if not self.q:
            return None

        return self.q.popleft()

    def push(self, page_id: str) -> bool:
        if page_id in self.s:
            return False

        self.s.add(page_id)
        self.q.append(page_id)

        return True

    def mark_done(self, page_id: str) -> None:
        pass

    def mark_failed(self, page_id: str) -> None:
        pass

    def write(self, item: dict) -> None:
        row = item.copy()
        row["category"] = CATEGORY.get(row["category"])

        self.writer.writerow(row)
        self.file.flush()

    def close(self) -> None:
        self.file.close()
