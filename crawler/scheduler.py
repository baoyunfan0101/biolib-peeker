from concurrent.futures import (
    FIRST_COMPLETED,
    Future,
    ThreadPoolExecutor,
    wait,
)
from crawler.logger import CrawlerLogger
from crawler.model import (
    BatchShipment,
    CrawlerStats,
    PageContent,
)
from crawler.warehouse_keeper import WarehouseKeeper
from crawler.worker import worker_task


class Scheduler:
    def __init__(
            self,
            keeper: WarehouseKeeper,
            logger: CrawlerLogger,
            workers: int = 8,
    ) -> None:
        self.keeper = keeper
        self.logger = logger
        self.workers = workers

        self.stats = CrawlerStats()
        self.inflight: dict[Future, int] = {}  # map each Future to its page_id

    def run(self) -> None:
        executor = ThreadPoolExecutor(
            max_workers=self.workers,
            thread_name_prefix='T',
        )

        try:
            self.logger.summary(
                title='START',
                stats=self.stats,
                pending=len(self.keeper),
                inflight=len(self.inflight),
            )

            self._fill_workers(executor)

            while self.inflight:
                done_futures, _ = wait(
                    self.inflight,  # futures to wait for, equivalent to self.inflight.keys()
                    timeout=0.5,  # wait at most 0.5s
                    return_when=FIRST_COMPLETED,  # return when any future completes
                )

                for future in done_futures:
                    self.inflight.pop(future)  # remove completed future

                    page_content = future.result()  # get the task result or raise the task exception
                    shipment = self._pack_shipment(page_content)

                    self.keeper.receive(shipment)
                    self._fill_workers(executor)

                    self.logger.maybe_summary(
                        title='RUNNING',
                        stats=self.stats,
                        pending=len(self.keeper),
                        inflight=len(self.inflight),
                    )

            self.logger.summary(
                title='FINISHED',
                stats=self.stats,
                pending=len(self.keeper),
                inflight=len(self.inflight),
            )

        except KeyboardInterrupt:
            self.logger.summary(
                title='STOPPED',
                stats=self.stats,
                pending=len(self.keeper),
                inflight=len(self.inflight),
            )

        finally:
            executor.shutdown(wait=True)
            self.keeper.close()

    def _fill_workers(
            self,
            executor: ThreadPoolExecutor,
    ) -> None:
        if len(self.inflight) >= self.workers:
            return

        page_ids = self.keeper.dispatch(self.workers)  # maintain workers <= inflight < 2 * workers

        for page_id in page_ids:
            future = executor.submit(worker_task, page_id)  # submit tasks to the thread pool
            self.inflight[future] = page_id  # look up the page_id for the future

    def _pack_shipment(
            self,
            page_content: PageContent,
    ) -> BatchShipment:
        if page_content.error is not None:
            self.stats.failed += 1

            self.logger.failed(
                page_id=page_content.page_id,
                error=page_content.error,
            )

            return BatchShipment(
                taxa_items=[],
                synonym_items=[],
                child_page_ids=[],
                done_page_ids=[],
                failed_page_ids=[page_content.page_id],
            )

        taxa_items = []
        synonym_items = []
        child_page_ids = []

        for item in page_content.content_of_interest:
            item['parent'] = page_content.page_id  # use current page_id as parent
            new_page_id = item['id']

            if new_page_id and new_page_id != '':
                taxa_items.append(item)
                child_page_ids.append(int(new_page_id))  # item with 'id' referring to a child
            else:
                synonym_items.append(item)  # item without 'id' referring to a synonym

        self.stats.done += 1
        self.stats.children += len(taxa_items)
        self.stats.synonyms += len(synonym_items)

        self.logger.done(
            page_id=page_content.page_id,
            child_cnt=len(taxa_items),
            synonym_cnt=len(synonym_items),
        )

        return BatchShipment(
            taxa_items=taxa_items,
            synonym_items=synonym_items,
            child_page_ids=child_page_ids,
            done_page_ids=[page_content.page_id],
            failed_page_ids=[],
        )
