from __future__ import annotations

from dataclasses import replace
import random
import time
from urllib.parse import urlencode

from bs4 import BeautifulSoup
from rubberneck import EngineAction, EngineEvent, Failure, Request, Response, Spider
from rubberneck.downloader.base import DownloaderResult
from rubberneck.downloader.middleware.base import DownloaderMiddleware
from rubberneck.downloader.middleware.challenge import ChallengeDownloaderMiddleware

from biolib_parser import ROOT_URL, parse_taxon_response, taxon_request


class BioLibSpider(Spider):
    name = 'biolib'

    def __init__(self, init_page: int = 14772) -> None:
        self.init_page = init_page

    def start_requests(self):
        yield taxon_request(self.init_page)

    def parse(self, response: Response):
        if response.status >= 400:
            yield Failure(response, RuntimeError(f'HTTP {response.status}'), 'spider')
            return

        try:
            yield from parse_taxon_response(response)
        except Exception as error:
            yield Failure(response, error, 'spider')
            return


class BioLibSecurityCheckMiddleware(ChallengeDownloaderMiddleware):
    def is_challenge_page(self, request: Request, response: Response) -> bool:
        soup = BeautifulSoup(response.text, 'html.parser')
        return soup.find('input', {'name': 'action', 'value': 'passcheck'}) is not None

    def handle_challenge_page(
        self,
        request: Request,
        response: Response,
    ) -> DownloaderResult:
        body = urlencode({
            'cntbtn': 'Continue',
            'action': 'passcheck',
            'hpsec': '',
        }).encode('ascii')

        headers = dict(request.headers)
        headers['Content-Type'] = 'application/x-www-form-urlencoded'

        yield Request(
            ROOT_URL,
            method='POST',
            headers=headers,
            body=body,
            meta=dict(request.meta),
        )


class BioLibPolitenessMiddleware(DownloaderMiddleware):
    def process_input(self, request: Request) -> Request:
        ratio = (0.6 - 0.2) / (9.5 - 0.2)
        alpha = 2.0
        beta = alpha * ((1 / ratio) - 1)
        time.sleep(0.2 + (9.5 - 0.2) * random.betavariate(alpha, beta))
        return request


class BioLibHarvestingGuardMiddleware(DownloaderMiddleware):
    def process_output(
        self,
        request: Request,
        output: DownloaderResult,
    ) -> DownloaderResult:
        values = list(output)
        for value in values:
            if isinstance(value, Response) and 'Harvesting server' in value.text:
                return (
                    EngineEvent(
                        EngineAction.STOP_GRACEFULLY,
                        {'reason': f'Harvesting server triggered while getting: {request.url}'},
                    ),
                )
        return values
