#!/usr/bin/env python3

import argparse
import json
import logging
import os
import re
import sys
from xml.etree import ElementTree  # nosec

import jsonschema
import requests

from lib.parsers import XMLParser, JSONParser, HTMLParser
from lib.scraper import Scraper, ScraperRunner

ROOT_PATH = os.path.dirname(os.path.realpath(__file__))
RESOURCES_PATH = os.path.join(ROOT_PATH, "resources")
PROVIDERS_PATH = os.path.join(RESOURCES_PATH, "providers.json")
SETTINGS_PATH = os.path.join(RESOURCES_PATH, "settings.xml")
PROVIDERS_SCHEMA_PATH = os.path.join(RESOURCES_PATH, "providers.schema.json")

COLOR_REGEX = re.compile(r"^[0-9A-Fa-f]{8}$")


class ValidationError(Exception):
    pass


def verify(providers_path, schema_path, settings_path):
    if not os.path.exists(providers_path):
        raise ValidationError("providers.json file ({}) does not exist!".format(providers_path))

    with open(providers_path) as f:
        data = json.load(f)
    with open(schema_path) as f:
        schema = json.load(f)

    jsonschema.validate(data, schema)

    settings = ElementTree.parse(settings_path)  # nosec
    providers_root = os.path.dirname(providers_path)

    for provider in data:
        scraper = Scraper.from_data(provider)

        icon = scraper.get_attribute("icon", default=None)
        if icon:
            if not os.path.exists(os.path.join(providers_root, icon)):
                logging.warning("attributes.icon for provider '%s' is defined (%s) but is not a valid file",
                                scraper.name, icon)
        else:
            logging.debug("No icon attributes.icon defined for provider '%s'", scraper.name)

        color = scraper.get_attribute("color", default=None)
        if color:
            if not COLOR_REGEX.match(color):
                logging.warning("attributes.color for provider '%s' is defined (%s) but is not a valid color (%s)",
                                scraper.name, color, COLOR_REGEX.pattern)
        else:
            logging.debug("No icon attributes.color defined for provider '%s'", scraper.name)

        setting = settings.find(".//setting[@id='{}']".format(scraper.id))
        if setting is not None:
            if setting.attrib.get("type") != "bool":
                logging.warning("settings.xml setting with id '%s' must have type 'bool'", scraper.id)
            if setting.attrib.get("label") is None:
                logging.warning("settings.xml setting with id '%s' must have label attribute defined", scraper.id)
        else:
            logging.warning("settings.xml setting with id '%s' is not defined", scraper.id)


def verify_and_print(args):
    try:
        verify(args.providers_path, args.schema_path, args.settings_path)
    except ValidationError as e:
        logging.error(e)
    except jsonschema.ValidationError as e:
        logging.error(e.message)
    except json.JSONDecodeError:
        logging.error("providers.json file must contain valid JSON data")
    else:
        logging.info("The providers.json contents are valid")


# noinspection PyProtectedMember
def xpath(args):
    session = requests.Session()
    session.headers = {"User-Agent": Scraper._user_agent, "Accept-Encoding": "gzip"}
    r = session.get(args.url)
    r.raise_for_status()

    logging.debug("Url content:\n%s", r.content)
    parser = args.parser(r.content)

    if args.rows:
        for element in parser._root.iterfind(args.rows):
            logging.info(parser._xpath_element(element, args.xpath))
    else:
        logging.info(parser._xpath_element(parser._root, args.xpath))


def get_scrapers(args):
    return [s for s in Scraper.get_scrapers(args.providers_path) if not args.provider_id or args.provider_id == s.id]


def print_results(scraper_name, results):
    for result in results:
        title = result["title"]
        seeds = result.get("seeds")
        leeches = result.get("leeches")
        size = result.get("size")

        if seeds and leeches:
            title += " | S:{}/L:{}".format(seeds, leeches)
        if size:
            title += " | {}".format(size)
        title += " | {}".format(scraper_name)

        print("+ {}\n{}\n".format(title, result["magnet"]))


def parse_query(args):
    with ScraperRunner(get_scrapers(args)) as runner:
        for scraper, results in runner.parse_query(args.search):
            print_results(scraper.name, results)


def main():
    parser = argparse.ArgumentParser(description="Tool to test and verify script.flix.magneto providers")
    subparsers = parser.add_subparsers(title="command", dest="command", required=True, help="Command to execute")

    parser_verify = subparsers.add_parser("verify", help="Verifies the providers.json file")
    parser_verify.add_argument("-p", "--providers-path", type=str, default=PROVIDERS_PATH,
                               help="The providers.json path (default: {})".format(PROVIDERS_PATH))
    parser_verify.add_argument("-s", "--settings-path", type=str, default=SETTINGS_PATH,
                               help="The addon settings.xml path (default: {})".format(SETTINGS_PATH))
    parser_verify.add_argument("-S", "--schema-path", type=str, default=PROVIDERS_SCHEMA_PATH,
                               help="The json schema path (default: {})".format(PROVIDERS_SCHEMA_PATH))
    parser_verify.set_defaults(func=verify_and_print)

    parser_xpath = subparsers.add_parser("xpath", help="Gets the result of the xpath expression")
    parser_xpath_type = parser_xpath.add_mutually_exclusive_group()
    parser_xpath_type.add_argument("--xml", action="store_const", const=XMLParser, dest="parser",
                                   help="Use the XML parser")
    parser_xpath_type.add_argument("--json", action="store_const", const=JSONParser, dest="parser",
                                   help="Use the JSON parser")
    parser_xpath_type.add_argument("--html", action="store_const", const=HTMLParser, dest="parser",
                                   help="Use the HTML parser (default)")
    parser_xpath.add_argument("-r", "--rows", type=str, help="Rows xpath (for multiple evaluation)")
    parser_xpath.add_argument("xpath", type=str, help="The xpath expression")
    parser_xpath.add_argument("url", type=str, help="The url where to perform the xpath")
    parser_xpath.set_defaults(func=xpath, parser=HTMLParser)

    parser_parse = subparsers.add_parser("parse", help="Runs the specified parser and lists the results")
    parsers = parser_parse.add_subparsers(title="parser", dest="parser", description="The parser to execute",
                                          required=True)
    query_parser = parsers.add_parser("query", help="Parses the results for the provided query")
    query_parser.add_argument("search", help="The search query")
    query_parser.set_defaults(func=parse_query)

    for p in (query_parser,):
        p.add_argument("-i", "--provider-id", type=str, help="The provider identifier")
        p.add_argument("-p", "--providers-path", type=str, default=PROVIDERS_PATH,
                       help="The providers.json path (default: {})".format(PROVIDERS_PATH))

    for p in (parser_verify, parser_xpath, query_parser):
        p.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG if args.verbose else logging.INFO)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(logging.Formatter("%(levelname)s - %(message)s"))
    logger.handlers = [sh]

    args.func(args)


if __name__ == "__main__":
    main()
