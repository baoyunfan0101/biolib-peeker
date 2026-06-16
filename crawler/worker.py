from biolib_parser import resolve_page
from crawler.model import PageContent


def worker_task(
        page_id: int,
) -> PageContent:
    try:
        return PageContent(
            page_id=page_id,
            content_of_interest=resolve_page(page_id),
            error=None,
        )
    except Exception as e:
        return PageContent(
            page_id=page_id,
            content_of_interest=None,
            error=e,
        )