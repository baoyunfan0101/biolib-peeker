from dataclasses import dataclass
from typing import Optional


@dataclass
class PageContent:
    page_id: int
    content_of_interest: Optional[list[dict]]
    error: Optional[Exception]


@dataclass
class BatchShipment:
    taxa_items: list[dict]
    synonym_items: list[dict]
    child_page_ids: list[int]
    done_page_ids: list[int]
    failed_page_ids: list[int]


@dataclass
class CrawlerStats:
    done: int = 0
    failed: int = 0
    children: int = 0
    synonyms: int = 0
