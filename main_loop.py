import argparse
from biolib_parser import resolve_page
from typing import Optional
from db.abstract_store import AbstractStore
from db.sqlite_store import SqliteStore
from db.memory_store import MemoryStore

LOG_MODE = {
    "none": 0,
    "summary": 1,
    "detail": 2,
}


# main loop
def main(
        init_page: Optional[str] = "14772",
        store: AbstractStore = None,
        log_mode: int = LOG_MODE["summary"],
):
    if init_page is not None:
        store.push(init_page)

    if log_mode == LOG_MODE["summary"]:
        print(f"[START] pages_pending={len(store)}")

    while True:
        curr_page_id = store.pop()
        if curr_page_id is None:
            break

        if log_mode == LOG_MODE["detail"]:
            print(f"\nProcessing {curr_page_id}..")

        try:
            content_of_interest = resolve_page(curr_page_id)
            child_cnt = 0
            synonym_cnt = 0

            for item in content_of_interest:
                # add parent column
                item["parent"] = curr_page_id

                new_page_id = item["id"]

                # item referring to a child
                if new_page_id and new_page_id != "":
                    child_cnt += 1
                    store.write(item)
                    store.push(new_page_id)

                    if log_mode == LOG_MODE["detail"]:
                        print(f"\tPush child {new_page_id}")

                # item referring to a synonym
                else:
                    # give synonym a man-made id
                    synonym_cnt += 1
                    item["id"] = f"{curr_page_id}-{synonym_cnt}"
                    store.write(item)

                    if log_mode == LOG_MODE["detail"]:
                        print(f"\tAdd synonym {item['id']}")

            store.mark_done(curr_page_id)

            if log_mode == LOG_MODE["summary"]:
                print(
                    f"[DONE] page={curr_page_id}, "
                    f"children_pushed={child_cnt}, "
                    f"synonyms_added={synonym_cnt}"
                )

        except Exception as e:
            store.mark_failed(curr_page_id)

            if log_mode == LOG_MODE["summary"]:
                print(f"[FAILED] page={curr_page_id}, error={e}")
            elif log_mode == LOG_MODE["detail"]:
                print(f"Failed {curr_page_id}: {e}")


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--init-page",
        default="14772",
        help="starting BioLib page id",
    )

    parser.add_argument(
        "--store",
        choices=["memory", "sqlite"],
        default="sqlite",
        help="storage backend"
    )

    parser.add_argument(
        "--reset",
        action="store_true",
        help="reset existing data before crawling"
    )

    parser.add_argument(
        "--log",
        choices=["none", "summary", "detail"],
        default="summary",
        help="log level"
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    main(
        init_page=args.init_page if args.reset else None,
        store=(
            MemoryStore(reset=args.reset)
            if args.store == "memory"
            else SqliteStore(reset=args.reset)
        ),
        log_mode=LOG_MODE[args.log],
    )
