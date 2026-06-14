import argparse
from concurrent.futures import ThreadPoolExecutor
import threading
import time
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


# main loop
def main(
        init_page: Optional[int] = 14772,
        store: AbstractStore = None,
        log_mode: int = LOG_MODE['summary'],
        workers: int = 8,
        idle_rounds: int = 30,
        idle_sleep: float = 1.0,
):
    if workers > 1 and not isinstance(store, SqliteStore):
        raise ValueError('multi-threading is only supported with SqliteStore')
    stop_event = threading.Event()  # event to stop all worker threads

    if init_page is not None:
        store.push(init_page)
    if log_mode == LOG_MODE['summary']:
        print(f'[START] pages_pending={len(store)}')

    def worker():
        thread_name = threading.current_thread().name

        try:
            idle_cnt = 0
            while not stop_event.is_set():  # while not interrupted by user
                curr_page_id = store.pop()
                if stop_event.is_set():  # if interrupted by user
                    if curr_page_id is not None:
                        store.mark_failed(curr_page_id)
                    break
                if curr_page_id is None:  # if no pending pages
                    idle_cnt += 1
                    if idle_cnt >= idle_rounds:
                        break
                    time.sleep(idle_sleep)
                    continue
                idle_cnt = 0
                if log_mode == LOG_MODE['detail']:
                    print(f'{thread_name}: Processing {curr_page_id}..')

                try:
                    content_of_interest = resolve_page(curr_page_id)
                    child_cnt = 0
                    synonym_cnt = 0

                    for item in content_of_interest:
                        # add parent column
                        item['parent'] = curr_page_id
                        new_page_id = item['id']

                        # item referring to a child
                        if new_page_id and new_page_id != '':
                            child_cnt += 1
                            store.write_taxa(item)
                            store.push(new_page_id)
                            if log_mode == LOG_MODE['detail']:
                                print(f'\t{thread_name}: Push child {new_page_id}')

                        # item with empty 'id' referring to a synonym
                        else:
                            synonym_cnt += 1
                            store.write_synonym(item)
                            if log_mode == LOG_MODE['detail']:
                                print(f"\t{thread_name}: Add synonym {item['scientific_name']}")

                    store.mark_done(curr_page_id)
                    if log_mode == LOG_MODE['summary']:
                        print(
                            f'[DONE] {thread_name}: page={curr_page_id}, '
                            f'children_pushed={child_cnt}, '
                            f'synonyms_added={synonym_cnt}',
                            flush=True
                        )
                except Exception as e:
                    store.mark_failed(curr_page_id)
                    if log_mode == LOG_MODE['summary']:
                        print(f'[FAILED] {thread_name}: page={curr_page_id}, error={e}')
                    elif log_mode == LOG_MODE['detail']:
                        print(f'{thread_name}: Failed {curr_page_id}: {e}')
        finally:
            store.close()

    executor = ThreadPoolExecutor(
        max_workers=workers,
        thread_name_prefix='T',
    )
    futures = [
        executor.submit(worker)
        for _ in range(workers)
    ]  # submit worker tasks to the thread pool
    try:
        for future in futures:
            future.result()  # wait for all worker threads to finish
    except KeyboardInterrupt:
        stop_event.set()
        print('[STOPPED] interrupted by user')
    finally:
        store.close()
        executor.shutdown()


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
        '--idle-rounds',
        type=int,
        default=30,
        help='consecutive empty polls before worker exit'
    )
    parser.add_argument(
        '--idle-sleep',
        type=float,
        default=1.0,
        help='sleep time between empty polls in seconds'
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
        idle_rounds=args.idle_rounds,
        idle_sleep=args.idle_sleep,
        log_mode=LOG_MODE[args.log],
    )
