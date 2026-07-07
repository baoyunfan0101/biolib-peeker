from __future__ import annotations

import logging
import sys

from rubberneck import ComponentSpec, Engine
from rubberneck.downloader.middleware.retry import RetryDownloaderMiddleware
from rubberneck.logger import LoggerAction

from biolib_pipeline import BioLibSQLitePipeline
from biolib_spider import (
    BioLibHarvestingGuardMiddleware,
    BioLibPolitenessMiddleware,
    BioLibSecurityCheckMiddleware,
    BioLibSpider,
)

INIT_PAGE = 14772
RESET = False
WORKERS = 8
DATA_PATH = './data'
SUMMARY_EVERY = 1
LOG_FILE = 'biolib.log'
AGENTS = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 115Browser/35.30.0 Chromium/125.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.100 Safari/537.36 OPR/63.0.3368.43',
    'Mozilla/5.0 (Windows NT 10.0; WOW64; Trident/7.0; LCTE; rv:11.0) like Gecko',
    'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.25 Safari/537.36 Core/1.70.3722.400 QQBrowser/10.5.3739.400',
    'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36 QIHU 360SE',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36 NetType/WIFI MicroMessenger/7.0.20.1781(0x6700143B) WindowsWechat(0x63090819) XWEB/8519 Flue',
)
HEADERS = tuple(
    {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Cache-Control': 'max-age=0',
        'Priority': 'u=0, i',
        'Sec-Ch-Ua': '"Chromium";v="125", "Not.A/Brand";v="24"',
        'Sec-Ch-Ua-Mobile': '?0',
        'Sec-Ch-Ua-Platform': '"Windows"',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': agent,
    }
    for agent in AGENTS
)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format='%(message)s',
        handlers=(
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(LOG_FILE, encoding='utf-8'),
        ),
        force=True,
    )
    logging.info('[BOOT] starting BioLib crawler')

    engine = Engine(
        BioLibSpider(init_page=INIT_PAGE),
        scheduler=ComponentSpec(
            'sqlite',
            {
                'path': DATA_PATH,
                'filename': 'request_queue.db',
                'reset': RESET,
            },
        ),
        downloader=ComponentSpec(
            'session_pool',
            {
                'pool_size': WORKERS,
                'timeout': (5.0, 30.0),
                'headers': HEADERS,
            },
        ),
        pipeline=BioLibSQLitePipeline(
            path=DATA_PATH,
            reset=RESET,
        ),
        logger=ComponentSpec(
            'standard',
            {
                'summary_every': SUMMARY_EVERY,
                'actions': (
                    LoggerAction.START,
                    LoggerAction.FINISH,
                    LoggerAction.STOPPING,
                    LoggerAction.STOPPED,
                    LoggerAction.DONE,
                    LoggerAction.FAILED,
                    LoggerAction.SUMMARY,
                ),
            },
        ),
        downloader_middlewares=(
            BioLibPolitenessMiddleware(),
            RetryDownloaderMiddleware(max_retries=1),
            ComponentSpec('referer'),
            BioLibSecurityCheckMiddleware(),
            BioLibHarvestingGuardMiddleware(),
            ComponentSpec('cookies', order=700, options={'max_jars': WORKERS}),
        ),
        downloader_workers=WORKERS,
        spider_workers=WORKERS,
        pipeline_workers=WORKERS,
    )
    engine.run()


if __name__ == '__main__':
    main()
