from crawler.model import CrawlerStats

LOG_MODE = {
    'none': 0,
    'summary': 1,
    'detail': 2,
}


class CrawlerLogger:
    def __init__(
            self,
            log_mode: str = 'summary',
            log_every: int = 50,
    ) -> None:
        self.log_mode = LOG_MODE.get(log_mode)
        self.log_every = log_every
        self.last_logged = CrawlerStats()

    def summary(
            self,
            title: str,
            stats: CrawlerStats,
            pending: int,
            inflight: int,
    ) -> None:
        if self.log_mode is None or self.log_mode == LOG_MODE['none']:
            return
        print(
            f'[{title}] '
            f'done={stats.done} (+{stats.done - self.last_logged.done}), '
            f'failed={stats.failed} (+{stats.failed - self.last_logged.failed}), '
            f'children={stats.children} (+{stats.children - self.last_logged.children}), '
            f'synonyms={stats.synonyms} (+{stats.synonyms - self.last_logged.synonyms}), '
            f'pending={pending}, '
            f'inflight={inflight}',
            flush=True,
        )
        self.last_logged = CrawlerStats(
            done=stats.done,
            failed=stats.failed,
            children=stats.children,
            synonyms=stats.synonyms,
        )

    def done(
            self,
            page_id: int,
            child_cnt: int,
            synonym_cnt: int,
    ) -> None:
        if self.log_mode != LOG_MODE['detail']:
            return
        print(
            f'[DONE] '
            f'page={page_id}, '
            f'children={child_cnt}, '
            f'synonyms={synonym_cnt}',
            flush=True,
        )

    def failed(
            self,
            page_id: int,
            error: Exception,
    ) -> None:
        if self.log_mode != LOG_MODE['detail']:
            return
        print(
            f'[FAILED] '
            f'page={page_id}, '
            f'error={error}',
            flush=True,
        )

    def maybe_summary(
            self,
            title: str,
            stats: CrawlerStats,
            pending: int,
            inflight: int,
    ) -> None:
        if self.log_every <= 0 or stats.done - self.last_logged.done < self.log_every:
            return

        self.summary(
            title=title,
            stats=stats,
            pending=pending,
            inflight=inflight,
        )
