import argparse
from concurrent.futures import (
    ThreadPoolExecutor,
    wait,
    FIRST_COMPLETED,
)
import threading
from typing import Optional
from biolib_parser import resolve_page
from db.abstract_store import AbstractStore
from db.memory_store import MemoryStore
from db.sqlite_store import SqliteStore

LOG_MODE = {
    'none': 0,
    'summary': 1,
    'detail': 2,
}


def log_summary(
        log_mode: int,
        title: str,
        stats: dict,
        pending: int,
) -> None:
    if log_mode == LOG_MODE['none']:
        return
    print(
        f'[{title}] '
        f"processed={stats['processed']}, "
        f"failed={stats['failed']}, "
        f"children={stats['children']}, "
        f"synonyms={stats['synonyms']}, "
        f'pending={pending}',
        flush=True,
    )


def log_done(
        log_mode: int,
        page_id: int,
        child_cnt: int,
        synonym_cnt: int,
) -> None:
    if log_mode != LOG_MODE['detail']:
        return
    print(
        f'[DONE] '
        f'page={page_id}, '
        f'children={child_cnt}, '
        f'synonyms={synonym_cnt}',
        flush=True,
    )


def log_failed(
        log_mode: int,
        page_id: int,
        error: Exception,
) -> None:
    if log_mode != LOG_MODE['detail']:
        return
    print(
        f'[FAILED] '
        f'page={page_id}, '
        f'error={error}',
        flush=True,
    )


# main loop
def main(
        init_page: Optional[int] = 14772,
        store: AbstractStore = None,
        workers: int = 8,
        batch_size: int = 50,
        log_mode: int = LOG_MODE['summary'],
) -> None:
    stop_event = threading.Event()  # event to stop all worker threads
    stats = {
        'processed': 0,
        'failed': 0,
        'children': 0,
        'synonyms': 0,
    }
    if init_page is not None:
        store.push([init_page])
    log_summary(
        log_mode,
        'START',
        stats,
        len(store),
    )
    executor = ThreadPoolExecutor(
        max_workers=workers,
        thread_name_prefix='T',
    )

    try:
        while not stop_event.is_set():  # while not interrupted by user
            page_ids = store.pop(batch_size)
            if not page_ids:  # if no pending pages
                log_summary(
                    log_mode,
                    'FINISHED',
                    stats,
                    len(store),
                )
                break

            # submit tasks to the thread pool
            futures = {
                executor.submit(resolve_page, page_id): page_id  # map each Future to its page_id
                for page_id in page_ids  # all page_ids as task arguments
            }  # the executing worker thread is not determined here
            pending = set(futures)  # extract keys of futures
            child_page_ids = []
            taxa_items = []
            synonym_items = []
            done_page_ids = []
            failed_page_ids = []

            while pending and not stop_event.is_set():
                done, pending = wait(
                    pending,  # futures to wait for
                    timeout=0.5,  # wait at most 0.5s
                    return_when=FIRST_COMPLETED,  # return when any future completes
                )

                for future in done:
                    curr_page_id = futures[future]  # look up the page_id for the future
                    try:
                        content_of_interest = future.result()  # get the task result or raise the task exception
                    except Exception as e:
                        failed_page_ids.append(curr_page_id)
                        stats['processed'] += 1
                        stats['failed'] += 1
                        log_failed(
                            log_mode,
                            curr_page_id,
                            e,
                        )
                        continue

                    child_cnt = 0
                    synonym_cnt = 0

                    for item in content_of_interest:
                        # use curr_page_id as parent
                        item['parent'] = curr_page_id
                        new_page_id = item['id']

                        # item referring to a child
                        if new_page_id and new_page_id != '':
                            child_cnt += 1
                            taxa_items.append(item)
                            child_page_ids.append(int(new_page_id))

                        # item with empty 'id' referring to a synonym
                        else:
                            synonym_cnt += 1
                            synonym_items.append(item)

                    done_page_ids.append(curr_page_id)
                    stats['processed'] += 1
                    stats['children'] += child_cnt
                    stats['synonyms'] += synonym_cnt
                    log_done(
                        log_mode,
                        curr_page_id,
                        child_cnt,
                        synonym_cnt,
                    )

            if stop_event.is_set():
                failed_page_ids.extend([
                    futures[future]
                    for future in pending
                ])  # mark remaining tasks in the batch as failed
                stats['failed'] += len(pending)

            # store the batch
            store.write_taxa(taxa_items)
            store.write_synonym(synonym_items)
            store.push(child_page_ids)
            store.mark_done(done_page_ids)
            store.mark_failed(failed_page_ids)
            log_summary(
                log_mode,
                'BATCH',
                stats,
                len(store),
            )

    except KeyboardInterrupt:
        stop_event.set()
        log_summary(
            log_mode,
            'STOPPED',
            stats,
            len(store),
        )
    finally:
        stop_event.set()
        executor.shutdown(wait=True)  # wait for running tasks to finish
        store.close()


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
        '--batch-size',
        type=int,
        default=50,
        help='number of pages popped from database each batch',
    )
    parser.add_argument(
        '--log',
        choices=['none', 'summary', 'detail'],
        default='summary',
        help='log level'
    )
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()

    main(
        init_page=args.init_page if args.reset else None,
        store=(
            MemoryStore(reset=args.reset)
            if args.store == 'memory'
            else SqliteStore(reset=args.reset)
        ),
        workers=args.workers,
        batch_size=args.batch_size,
        log_mode=LOG_MODE[args.log],
    )
