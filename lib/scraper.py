import json
import logging
import re
import unicodedata
from multiprocessing.pool import ThreadPool
from string import Formatter
from xml.etree import ElementTree

import htmlement
import requests

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

_invalid_xml_tag_re = re.compile(r"[^a-zA-Z0-9-_.]")


def create_xml_tree(obj, root_name="root", attribute_type=False):
    root = ElementTree.Element(root_name)
    _create_xml_tree(root, obj, attribute_type=attribute_type)
    return root


def _check_tag(tag, invalid_xml_tag_re=re.compile(r"[^a-zA-Z0-9-_.]")):
    tag = invalid_xml_tag_re.sub("", tag)
    if len(tag) == 0 or tag[0].isdigit():
        tag = "_" + tag
    return tag


def _create_xml_tree(root, obj, **kwargs):
    attribute_type = kwargs.get("attribute_type", False)
    tag_str = kwargs.get("tag_str", str)

    if isinstance(obj, (tuple, list)):
        for v in obj:
            _create_xml_tree(ElementTree.SubElement(root, "item"), v, **kwargs)
    elif isinstance(obj, dict):
        for k, v in obj.items():
            if attribute_type:
                _kwargs, tag = {"key_type": k.__class__.__name__, "key": tag_str(k)}, "item"
            else:
                _kwargs, tag = {}, _check_tag(tag_str(k))
            _create_xml_tree(ElementTree.SubElement(root, tag, **_kwargs), v, **kwargs)
    else:
        root.text = tag_str(obj)
    if attribute_type:
        root.attrib["type"] = obj.__class__.__name__


def strip_accents(s):
    return "".join([c for c in unicodedata.normalize("NFD", s) if not unicodedata.combining(c)])


class ExtendedFormatter(Formatter):
    def convert_field(self, value, conversion):
        if conversion == "u":
            return value.upper()
        elif conversion == "l":
            return value.lower()
        elif conversion == "A":
            return strip_accents(value)
        return super(ExtendedFormatter, self).convert_field(value, conversion)

    def format_field(self, value, format_spec):
        if format_spec == "q":
            return quote(value, "")
        elif format_spec.startswith("q") and len(format_spec) == 2:
            return quote(value, " ").replace(" ", format_spec[1])
        return super(ExtendedFormatter, self).format_field(value, format_spec)


_formatter = ExtendedFormatter()


class Parser(object):
    # noinspection PyShadowingBuiltins
    def __init__(self, url, data, type="html", mutate=None):
        self.url = url
        self.data = data
        self.type = type
        self.mutate = mutate or {}


class ResultsParser(Parser):
    def __init__(self, rows, *args, **kwargs):
        super(ResultsParser, self).__init__(*args, **kwargs)
        self.rows = rows


def _run(pool, func, iterable):
    if pool is None:
        return [func(data) for data in iterable]
    return pool.map(func, iterable)


class Scraper(object):
    _spaces_re = re.compile(r"\s+")
    _attr_re = re.compile(r"^(.+)/@([a-zA-Z0-9_ ]+)$")
    _text_re = re.compile(r"^(.+)/text\(\)$")
    _user_agent = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/81.0.4044.113 Safari/537.36")

    @staticmethod
    def get_scrapers(path):
        with open(path) as f:
            return [Scraper.from_data(data) for data in json.load(f)]

    @staticmethod
    def from_data(data):
        return Scraper(
            data["name"], data["base_url"], ResultsParser(**data["results_parser"]),
            additional_parsers=[Parser(**d) for d in data.get("additional_parsers", [])],
            keywords=data.get("keywords"), attributes=data.get("attributes"))

    def __init__(self, name, base_url, results_parser, additional_parsers=None, keywords=None, attributes=None):
        # type:(str,str,ResultsParser,List[Parser], Dict[str, str], dict) ->None
        self._name = name
        self._base_url = base_url
        self._results_parser = results_parser
        self._additional_parsers = additional_parsers or []
        self._keywords = keywords or {}
        self._attributes = attributes or {}
        self._session = requests.Session()
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
        r = self._session.get(url)
        r.raise_for_status()
        if self._results_parser.type == "json":
            root = create_xml_tree(json.loads(r.content))
        else:
            root = htmlement.fromstring(r.content)
        results = [{key: self._xpath_element(element, xpath) for key, xpath in self._results_parser.data.items()}
                   for element in root.findall(self._results_parser.rows)]
        for key, value in self._results_parser.mutate.items():
            for result in results:
                result[key] = _formatter.format(value, **result)
        return results

    def _parse_additional(self, data):
        parser, result = data
        url = self._get_url(_formatter.format(parser.url, **result))
        logging.debug("Getting additional results for url %s", url)
        r = self._session.get(url)
        r.raise_for_status()
        if parser.type == "json":
            root = create_xml_tree(json.loads(r.content))
        else:
            root = htmlement.fromstring(r.content)
        for key, xpath in parser.data.items():
            result[key] = self._xpath_element(root, xpath)
        for key, value in parser.mutate.items():
            result[key] = _formatter.format(value, **result)

    def _xpath_element(self, element, path):
        logging.debug("Getting %s path from element %s", path, element.tag)
        attr_match = self._attr_re.match(path)
        if attr_match:
            return element.find(attr_match.group(1)).attrib[attr_match.group(2)]
        text_match = self._text_re.match(path)
        if text_match:
            return element.find(text_match.group(1)).text
        raise ValueError("Only .../@attr and .../text() paths are supported")

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
        self._pool = ThreadPool(num_threads)

    def __getattr__(self, item):
        if item not in ("parse", "parse_query"):
            raise ValueError("item must be one of parse/parse_query")

        def wrapper(*args, **kwargs):
            kwargs["pool"] = self._pool
            results = [(scraper, self._pool.apply_async(getattr(scraper, item), args, kwargs))
                       for scraper in self._scrapers]
            for scraper, scraper_results in results:
                yield scraper, scraper_results.get()

        return wrapper

    def close(self):
        self._pool.close()
        self._pool.join()

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
