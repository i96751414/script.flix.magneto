import copy
import itertools
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

    def _get_url_formatted(self, **kwargs):
        return _formatter.format(self._url, **kwargs)

    def _get_full_url(self, url):
        return urljoin(self._base_url, url)

    def _get_content(self, url):
        # type: (str) -> (str, bytes)
        logging.debug("Getting content for url %s", url)
        r = self._session.get(url, timeout=self._timeout)
        r.raise_for_status()
        return r.url, r.content


class AdditionalParser(_BaseParser):
    def __init__(self, *args, rows=None, **kwargs):
        # type: (any, str, any) -> None
        super(AdditionalParser, self).__init__(*args, **kwargs)
        self._rows = rows

    def _update_result(self, result, content):
        self._clazz(content).update_result(self._data, result)
        self._mutate_result(result)
        yield result

    def _get_additional_results_and_update(self, result, content):
        for new_result in self._clazz(content).parse_results(self._rows, self._data):
            updated_result = copy.copy(result)
            updated_result.update(new_result)
            self._mutate_result(updated_result)
            yield updated_result

    def get_and_update_result(self, result):
        _, content = self._get_content(self._get_full_url(self._get_url_formatted(**result)))

        if self._rows is None:
            results = self._update_result(result, content)
        else:
            results = self._get_additional_results_and_update(result, content)

        return list(results)


class ResultsParser(_BaseParser):
    def __init__(self, rows, *args, total_pages=1, next_page_url_type="xpath", next_page_url=None, **kwargs):
        # type: (str, any, int, str, str, any) -> None
        super(ResultsParser, self).__init__(*args, **kwargs)
        self._rows = rows

        if total_pages is None or total_pages <= 1 or next_page_url is None:
            self._total_pages = 1
            self._next_page_cb = lambda parser, **kw: None
        else:
            self._total_pages = total_pages
            if next_page_url_type == "static":
                self._next_page_cb = lambda parser, page=1, **kw: _formatter.format(next_page_url, page=page + 1, **kw)
            elif next_page_url_type == "xpath":
                self._next_page_cb = lambda parser, **kw: parser.try_get_element(next_page_url)
            else:
                raise ValueError("next_page_url_type must be one of static/xpath")

    def _get_and_parse_results(self, url, **kwargs):
        real_url, content = self._get_content(url)
        parser = self._clazz(content)
        results = parser.parse_results(self._rows, self._data)
        for result in results:
            self._mutate_result(result)
        return results, real_url, self._next_page_cb(parser, **kwargs)

    def get_and_parse_results(self, query):
        url = self._get_full_url(self._get_url_formatted(query=query))
        results, base_url, next_page = self._get_and_parse_results(url, query=query)

        # Handle next pages, if any
        if next_page is not None:
            visited_urls = [base_url]

            for page in range(2, self._total_pages + 1):
                new_page_url = urljoin(base_url, next_page)
                # Check for recursive calls
                if new_page_url in visited_urls:
                    logging.warning("Detected an already visited URL: %s", new_page_url)
                    break

                new_results, base_url, next_page = self._get_and_parse_results(new_page_url, page=page, query=query)
                if len(new_results) == 0:
                    break

                results.extend(new_results)
                if next_page is None:
                    break

                visited_urls.append(new_page_url)

        return results


def _run(pool, func, iterable):
    if pool is None:
        return [func(data) for data in iterable]
    return list(pool.map(func, iterable))


def safe_call(on_failure):
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logging.warning("Failed to execute %s: %s", func.__name__, e)
                return on_failure

        return wrapper

    return decorator


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
        sentinel = object()
        attribute = self._attributes.get(key, sentinel)
        if attribute is sentinel:
            attribute = kwargs.get("default", sentinel)
            if attribute is sentinel:
                raise ValueError("No such attribute: {}".format(key))

        return attribute

    def _format_query(self, keyword, formats):
        query = _formatter.format(self._keywords[keyword], **formats)
        return self._spaces_re.sub(" ", query.strip())

    def parse(self, keyword, formats, ignore_failed_updates=True, pool=None):
        return self.parse_query(
            self._format_query(keyword, formats), ignore_failed_updates=ignore_failed_updates, pool=pool)

    def parse_query(self, query, ignore_failed_updates=True, pool=None):
        decorator = safe_call(()) if ignore_failed_updates else lambda x: x
        results = self._results_parser.get_and_parse_results(query)

        for parser in self._additional_parsers:
            results = list(itertools.chain(*_run(pool, decorator(parser.get_and_update_result), results)))

        if len(results) == 0:
            logging.warning("No results found for query: %s", query)

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
