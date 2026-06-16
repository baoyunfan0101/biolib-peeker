import argparse
from crawler.logger import CrawlerLogger
from crawler.scheduler import Scheduler
from crawler.warehouse_keeper import WarehouseKeeper
from db.memory_store import MemoryStore
from db.sqlite_store import SqliteStore


# main loop
def main(
        init_page: int = 14772,
        store_type: str = 'sqlite',
        reset: bool = False,
        workers: int = 8,
        log_mode: str = 'summary',
        log_every: int = 50,
) -> None:
    store = (
        MemoryStore(reset=reset)
        if store_type == 'memory'
        else SqliteStore(reset=reset)
    )
    if reset or len(store) == 0:  # db is reset or pending pages
        store.push([init_page])

    keeper = WarehouseKeeper(store)

    logger = CrawlerLogger(
        log_mode=log_mode,
        log_every=log_every,
    )

    scheduler = Scheduler(
        keeper=keeper,
        logger=logger,
        workers=workers,
    )

    scheduler.run()


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--init-page',
        type=int,
        default=14772,
        help='starting BioLib page id',
    )
    parser.add_argument(
        '--store',
        choices=['memory', 'sqlite'],
        default='sqlite',
        help='storage backend'
    )
    parser.add_argument(
        '--reset',
        action='store_true',
        help='reset existing data before crawling'
    )
    parser.add_argument(
        '--workers',
        type=int,
        default=8,
        help='number of worker threads'
    )
    parser.add_argument(
        '--log-mode',
        choices=['none', 'summary', 'detail'],
        default='summary',
        help='log level'
    )
    parser.add_argument(
        '--log-every',
        type=int,
        default=50,
        help='summary log interval in completed pages',
    )
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()

    main(
        init_page=args.init_page,
        store_type=args.store,
        reset=args.reset,
        workers=args.workers,
        log_mode=args.log_mode,
        log_every=args.log_every,
    )
