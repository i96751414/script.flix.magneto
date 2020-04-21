import json
import logging
import re

import htmlement
import requests

try:
    # noinspection PyUnresolvedReferences
    from typing import List, Dict
except ImportError:
    pass

try:
    from urllib.parse import quote_plus
except ImportError:
    # noinspection PyUnresolvedReferences
    from urllib import quote_plus


class Parser(object):
    def __init__(self, url, data, mutate=None):
        self.url = url
        self.data = data
        self.mutate = mutate or {}


class ResultsParser(Parser):
    def __init__(self, rows, *args, **kwargs):
        super(ResultsParser, self).__init__(*args, **kwargs)
        self.rows = rows


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
        self._session.headers["User-Agent"] = self._user_agent

    @property
    def name(self):
        return self._name

    @property
    def id(self):
        return self._spaces_re.sub(".", self._name.lower())

    def get_attribute(self, key):
        return self._attributes[key]

    def _get_url(self, value):
        if not value.startswith("http"):
            value = self._base_url + value
        return value

    def _parse_results(self, query):
        url = self._get_url(self._results_parser.url.format(query=quote_plus(query)))
        logging.debug("Getting results for url %s", url)
        r = self._session.get(url)
        r.raise_for_status()
        root = htmlement.fromstring(r.content)
        results = [{key: self._xpath_element(element, xpath) for key, xpath in self._results_parser.data.items()}
                   for element in root.findall(self._results_parser.rows)]
        for key, value in self._results_parser.mutate.items():
            for result in results:
                result[key] = value.format(**result)
        return results

    def _parse_additional(self, parser, result):
        url = self._get_url(parser.url.format(**result))
        logging.debug("Getting additional results for url %s", url)
        r = self._session.get(url)
        r.raise_for_status()
        root = htmlement.fromstring(r.content)
        for key, xpath in parser.data.items():
            result[key] = self._xpath_element(root, xpath)
        for key, value in parser.mutate.items():
            result[key] = value.format(**result)

    def _xpath_element(self, element, path):
        attr_match = self._attr_re.match(path)
        if attr_match:
            return element.find(attr_match.group(1)).attrib[attr_match.group(2)]
        text_match = self._text_re.match(path)
        if text_match:
            return element.find(text_match.group(1)).text
        raise ValueError("Only .../@attr and .../text() paths are supported")

    def _format_query(self, keyword, formats):
        query = self._keywords[keyword].format(**formats)
        return self._spaces_re.sub(" ", query.strip())

    def parse(self, keyword, **formats):
        results = self._parse_results(self._format_query(keyword, formats))
        for parser in self._additional_parsers:
            for result in results:
                self._parse_additional(parser, result)
        return results


def generate_settings(path, enabled_count=-1):
    scrapers = Scraper.get_scrapers(path)
    for i, scraper in enumerate(scrapers):
        default = "false" if 0 <= enabled_count <= i else "true"
        print('<setting id="{}" type="bool" label="{}" default="{}"/>'.format(scraper.id, scraper.name, default))
