import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor

import requests

from lib.formatter import ExtendedFormatter
from lib.parsers import HTMLParser, JSONParser, XMLParser

try:
    from urllib.parse import urljoin
except ImportError:
    # noinspection PyUnresolvedReferences
    from urlparse import urljoin

_formatter = ExtendedFormatter()


class _BaseParser(object):
    # noinspection PyShadowingBuiltins
    def __init__(self, url, data, base_url=None, type="html", mutate=(), session=None, timeout=None):
        # type: (str, str, str, str, list[dict[str, str]] | dict[str, str], requests.Session, int) -> None
        self._url = url
        self._data = data
        self._base_url = base_url
        self._mutate = list(mutate.items()) if isinstance(mutate, dict) else [i for m in mutate for i in m.items()]
        self._session = session or requests
        self._timeout = timeout

        if type == "html":
            self._clazz = HTMLParser
        elif type == "json":
            self._clazz = JSONParser
        elif type == "xml":
            self._clazz = XMLParser
        else:
            raise ValueError("type must be one of html/json/xml")

    def _mutate_result(self, result):
        for key, value in self._mutate:
            result[key] = _formatter.format(value, **result)

    def _get_content(self, **kwargs):
        url_formatted = _formatter.format(self._url, **kwargs)
        full_url = url_formatted if self._base_url is None else urljoin(self._base_url, url_formatted)
        logging.debug("Getting content for url %s", full_url)
        r = self._session.get(full_url, timeout=self._timeout)
        r.raise_for_status()
        return r.content


class AdditionalParser(_BaseParser):
    def update_result(self, result, content):
        self._clazz(content).update_result(self._data, result)
        self._mutate_result(result)

    def get_and_update_result(self, result):
        self.update_result(result, self._get_content(**result))


class ResultsParser(_BaseParser):
    def __init__(self, rows, *args, **kwargs):
        # type: (str, any, any) -> None
        super(ResultsParser, self).__init__(*args, **kwargs)
        self._rows = rows

    def parse_results(self, content):
        results = self._clazz(content).parse_results(self._rows, self._data)
        for result in results:
            self._mutate_result(result)
        return results

    def get_and_parse_results(self, query):
        return self.parse_results(self._get_content(query=query))


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
        base_url = data["base_url"]
        session = requests.Session()
        session.headers = {"User-Agent": cls._user_agent, "Accept-Encoding": "gzip"}
        return cls(
            data["name"], ResultsParser(base_url=base_url, session=session, timeout=timeout, **data["results_parser"]),
            additional_parsers=[AdditionalParser(base_url=base_url, session=session, timeout=timeout, **d)
                                for d in data.get("additional_parsers", [])],
            keywords=data.get("keywords"), attributes=data.get("attributes"))

    def __init__(self, name, results_parser, additional_parsers=None, keywords=None, attributes=None):
        # type: (str, ResultsParser, list[AdditionalParser], dict[str, str], dict) -> None
        self._name = name
        self._results_parser = results_parser
        self._additional_parsers = additional_parsers or []
        self._keywords = keywords or {}
        self._attributes = attributes or {}

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

    def _format_query(self, keyword, formats):
        query = _formatter.format(self._keywords[keyword], **formats)
        return self._spaces_re.sub(" ", query.strip())

    def parse(self, keyword, formats, pool=None):
        return self.parse_query(self._format_query(keyword, formats), pool=pool)

    def parse_query(self, query, pool=None):
        results = self._results_parser.get_and_parse_results(query)
        for parser in self._additional_parsers:
            _run(pool, parser.get_and_update_result, results)
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
