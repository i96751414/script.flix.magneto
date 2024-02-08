import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor

import requests

from lib.formatter import ExtendedFormatter
from lib.parsers import HTMLParser, JSONParser, XMLParser

try:
    # noinspection PyUnresolvedReferences
    from typing import List, Dict
except ImportError:
    pass

try:
    from urllib.parse import urljoin
except ImportError:
    # noinspection PyUnresolvedReferences
    from urlparse import urljoin

_formatter = ExtendedFormatter()


class Parser(object):
    # noinspection PyShadowingBuiltins
    def __init__(self, url, data, type="html", mutate=None):
        self.url = url
        self.data = data
        self.mutate = mutate or {}

        if type == "html":
            self.clazz = HTMLParser
        elif type == "json":
            self.clazz = JSONParser
        elif type == "xml":
            self.clazz = XMLParser
        else:
            raise ValueError("type must be one of html/json/xml")

    def update_result(self, result, content):
        self.clazz(content).update_result(self.data, result)
        for key, value in self.mutate.items():
            self._mutate_result(result, key, value)

    @staticmethod
    def _mutate_result(result, key, value):
        result[key] = _formatter.format(value, **result)


class ResultsParser(Parser):
    def __init__(self, rows, *args, **kwargs):
        super(ResultsParser, self).__init__(*args, **kwargs)
        self.rows = rows

    def parse_results(self, content):
        results = self.clazz(content).parse_results(self.rows, self.data)
        for key, value in self.mutate.items():
            for result in results:
                self._mutate_result(result, key, value)
        return results


def _run(pool, func, iterable):
    if pool is None:
        return [func(data) for data in iterable]
    return list(pool.map(func, iterable))


class Scraper(object):
    _spaces_re = re.compile(r"\s+")
    _user_agent = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/102.0.5005.63 Safari/537.36")

    @classmethod
    def get_scrapers(cls, path, timeout=None):
        with open(path) as f:
            return [cls.from_data(data, timeout=timeout) for data in json.load(f)]

    @classmethod
    def from_data(cls, data, timeout=None):
        return cls(
            data["name"], data["base_url"], ResultsParser(**data["results_parser"]),
            additional_parsers=[Parser(**d) for d in data.get("additional_parsers", [])],
            keywords=data.get("keywords"), attributes=data.get("attributes"), timeout=timeout)

    def __init__(self, name, base_url, results_parser, additional_parsers=None, keywords=None, attributes=None,
                 timeout=None):
        # type: (str, str, ResultsParser, List[Parser], Dict[str, str], dict, int) -> None
        self._name = name
        self._base_url = base_url
        self._results_parser = results_parser
        self._additional_parsers = additional_parsers or []
        self._keywords = keywords or {}
        self._attributes = attributes or {}
        self._session = requests.Session()
        self._timeout = timeout
        self._session.headers = {
            "User-Agent": self._user_agent,
            "Accept-Encoding": "gzip",
        }

    @property
    def name(self):
        return self._name

    @property
    def id(self):
        return self._spaces_re.sub(".", self._name.lower())

    def get_attribute(self, key, **kwargs):
        try:
            return self._attributes[key]
        except KeyError as e:
            if "default" in kwargs:
                return kwargs["default"]
            else:
                raise e

    def _get_url(self, value):
        return urljoin(self._base_url, value)

    def _parse_results(self, query):
        url = self._get_url(_formatter.format(self._results_parser.url, query=query))
        logging.debug("Getting results for url %s", url)
        r = self._session.get(url, timeout=self._timeout)
        r.raise_for_status()
        return self._results_parser.parse_results(r.content)

    def _parse_additional(self, data):
        parser, result = data
        url = self._get_url(_formatter.format(parser.url, **result))
        logging.debug("Getting additional results for url %s", url)
        r = self._session.get(url, timeout=self._timeout)
        r.raise_for_status()
        parser.update_result(result, r.content)

    def _format_query(self, keyword, formats):
        query = _formatter.format(self._keywords[keyword], **formats)
        return self._spaces_re.sub(" ", query.strip())

    def parse(self, keyword, formats, pool=None):
        return self.parse_query(self._format_query(keyword, formats), pool=pool)

    def parse_query(self, query, pool=None):
        results = self._parse_results(query)
        for parser in self._additional_parsers:
            _run(pool, self._parse_additional, [(parser, result) for result in results])
        return results


class ScraperRunner(object):
    def __init__(self, scrapers, num_threads=10):
        self._scrapers = scrapers
        self._pool = ThreadPoolExecutor(num_threads)

    def parse(self, *args, **kwargs):
        return self._run_scrapers(Scraper.parse, *args, **kwargs)

    def parse_query(self, *args, **kwargs):
        return self._run_scrapers(Scraper.parse_query, *args, **kwargs)

    def _run_scrapers(self, method, *args, **kwargs):
        results = [(scraper, self._pool.submit(method, scraper, *args, pool=self._pool, **kwargs))
                   for scraper in self._scrapers]
        for scraper, scraper_results in results:
            try:
                self.before_result(scraper)
                yield scraper, scraper_results.result()
            except Exception as e:
                logging.error("Failed running scraper %s: %s", scraper.name, e)

    def before_result(self, scraper):
        pass

    def close(self):
        self._pool.shutdown()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
