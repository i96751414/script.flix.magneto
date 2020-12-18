import json
import logging
import re
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from string import Formatter

import requests

from lib.parsers import HTMLParser, JSONParser, XMLParser

try:
    # noinspection PyUnresolvedReferences
    from typing import List, Dict
except ImportError:
    pass

try:
    from urllib.parse import quote
except ImportError:
    # noinspection PyUnresolvedReferences
    from urllib import quote


def strip_accents(s):
    return "".join([c for c in unicodedata.normalize("NFD", s) if not unicodedata.combining(c)])


def sizeof_fmt(num, suffix="B", divisor=1000.0):
    for unit in ("", "k", "M", "G", "T", "P", "E", "Z"):
        if abs(num) < divisor:
            return "{:.2f} {}{}".format(num, unit, suffix)
        num /= divisor
    return "{:.2f} {}{}".format(num, "Y", suffix)


class ExtendedFormatter(Formatter):
    def convert_field(self, value, conversion):
        if conversion == "u":
            return value.upper()
        elif conversion == "l":
            return value.lower()
        elif conversion == "A":
            return strip_accents(value)
        elif conversion == "b":
            return sizeof_fmt(int(value))
        return super(ExtendedFormatter, self).convert_field(value, conversion)

    def format_field(self, value, format_spec):
        if format_spec == "q":
            return quote(value.encode("utf-8"), "")
        elif format_spec.startswith("q") and len(format_spec) == 2:
            return quote(value.encode("utf-8"), " ").replace(" ", format_spec[1])
        return super(ExtendedFormatter, self).format_field(value, format_spec)


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
            result[key] = _formatter.format(value, **result)


class ResultsParser(Parser):
    def __init__(self, rows, *args, **kwargs):
        super(ResultsParser, self).__init__(*args, **kwargs)
        self.rows = rows

    def parse_results(self, content):
        results = self.clazz(content).parse_results(self.rows, self.data)
        for key, value in self.mutate.items():
            for result in results:
                result[key] = _formatter.format(value, **result)
        return results


def _run(pool, func, iterable):
    if pool is None:
        return [func(data) for data in iterable]
    return list(pool.map(func, iterable))


class Scraper(object):
    _spaces_re = re.compile(r"\s+")
    _user_agent = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/81.0.4044.113 Safari/537.36")

    @staticmethod
    def get_scrapers(path, timeout=None):
        with open(path) as f:
            return [Scraper.from_data(data, timeout=timeout) for data in json.load(f)]

    @staticmethod
    def from_data(data, timeout=None):
        return Scraper(
            data["name"], data["base_url"], ResultsParser(**data["results_parser"]),
            additional_parsers=[Parser(**d) for d in data.get("additional_parsers", [])],
            keywords=data.get("keywords"), attributes=data.get("attributes"), timeout=timeout)

    def __init__(self, name, base_url, results_parser, additional_parsers=None, keywords=None, attributes=None,
                 timeout=None):
        # type:(str,str,ResultsParser,List[Parser], Dict[str, str], dict, int) -> None
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
        if not value.startswith("http"):
            value = self._base_url + value
        return value

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

    def __getattr__(self, item):
        if item not in ("parse", "parse_query"):
            raise ValueError("item must be one of parse/parse_query")

        def wrapper(*args, **kwargs):
            kwargs["pool"] = self._pool
            results = [(scraper, self._pool.submit(getattr(scraper, item), *args, **kwargs))
                       for scraper in self._scrapers]
            for scraper, scraper_results in results:
                try:
                    yield scraper, scraper_results.result()
                except Exception as e:
                    logging.error("Failed running scraper %s: %s", scraper.name, e)

        return wrapper

    def close(self):
        self._pool.shutdown()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False


def generate_settings(path, enabled_count=-1):
    scrapers = Scraper.get_scrapers(path)
    for i, scraper in enumerate(scrapers):
        default = "false" if 0 <= enabled_count <= i else "true"
        print('<setting id="{}" type="bool" label="{}" default="{}"/>'.format(scraper.id, scraper.name, default))


def main():
    import os
    path = os.path.join(os.path.dirname(__file__), "..", "resources", "providers.json")
    generate_settings(path, enabled_count=5)
