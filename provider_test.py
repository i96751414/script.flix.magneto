#!/usr/bin/env python3

import argparse
import json
import logging
import os
import re
import sys

import jsonschema
import requests
from defusedxml import ElementTree, minidom

from lib.filters import Resolution, ReleaseType
from lib.parsers import XMLParser, JSONParser, HTMLParser, create_xml_tree
from lib.scraper import Scraper, ScraperRunner

ROOT_PATH = os.path.dirname(os.path.realpath(__file__))
RESOURCES_PATH = os.path.join(ROOT_PATH, "resources")
PROVIDERS_PATH = os.path.join(RESOURCES_PATH, "providers.json")
SETTINGS_PATH = os.path.join(RESOURCES_PATH, "settings.xml")
PROVIDERS_SCHEMA_PATH = os.path.join(RESOURCES_PATH, "providers.schema.json")

COLOR_REGEX = re.compile(r"^[0-9A-Fa-f]{8}$")


class ValidationError(Exception):
    pass


# noinspection PyProtectedMember
def get_data_keys(scraper):
    parsers = scraper._results_parser, *scraper._additional_parsers
    for parser in parsers:
        for key in parser._data:
            yield key
        for key, _ in parser._mutate:
            yield key


def verify(providers_path, schema_path, settings_path):
    if not os.path.exists(providers_path):
        raise ValidationError("providers.json file ({}) does not exist!".format(providers_path))

    with open(providers_path) as f:
        data = json.load(f)
    with open(schema_path) as f:
        schema = json.load(f)

    jsonschema.validate(data, schema)

    settings = ElementTree.parse(settings_path)
    providers_root = os.path.dirname(providers_path)

    for provider in data:
        scraper = Scraper.from_data(provider)
        scraper_data = set(get_data_keys(scraper))

        for key, level in (("title", logging.ERROR), ("magnet", logging.ERROR),
                           ("seeds", logging.WARN), ("leeches", logging.WARN), ("size", logging.WARN)):
            if key not in scraper_data:
                logging.log(level, "data.%s not defined for provider %s", key, scraper.name)

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
        for result in parser.parse_results(args.rows, dict(data=args.xpath), full_elements=True):
            logging.info(result["data"])
    else:
        logging.info(parser.get_element(args.xpath, full_element=True))


def get_scrapers(args):
    return [s for s in Scraper.get_scrapers(args.providers_path) if not args.provider_id or args.provider_id == s.id]


def print_results(scraper_name, results):
    print("- Found a total of {} results".format(len(results)))
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


def generate_settings(path, enabled_count=-1):
    providers = "".join(
        '\n{}<setting id="{}" type="bool" label="{}" default="{}"/>'
        .format(" " * 4 * 2, scraper.id, scraper.name, "false" if 0 <= enabled_count <= i else "true")
        for i, scraper in enumerate(Scraper.get_scrapers(path)))

    resolutions = "".join(
        '\n{}<setting id="include_resolution_{}" type="bool" label="{}" default="true" enable="eq(-{},true)"/>'
        .format(" " * 4 * 2, resolution.name.lower(), resolution.name, i)
        for i, resolution in enumerate(reversed(Resolution.values), 1))

    release_types = "".join(
        '\n{}<setting id="include_release_{}" type="bool" label="{}" default="true" enable="eq(-{},true)"/>'
        .format(" " * 4 * 2, release.name.lower(), release.name, i)
        for i, release in enumerate(reversed(ReleaseType.values), 1))

    return """\
<?xml version="1.0" encoding="utf-8" standalone="yes"?>
<settings>
    <!-- General -->
    <category label="30000">
        <setting id="scraper_timeout" type="slider" label="30002" option="int" range="10,1,60" default="30"/>
        <setting id="thread_number" type="slider" label="30004" option="int" range="1,1,50" default="10"/>
        <setting id="enable_bg_dialog" type="bool" label="30003" default="true"/>
    </category>
    <!-- Providers -->
    <category label="30001">{}
    </category>
    <!-- Filters -->
    <category label="30020">
        <setting id="require_resolution" type="bool" label="30021" default="false"/>
        <setting id="require_release_type" type="bool" label="30022" default="false"/>
        <setting id="require_size" type="bool" label="30023" default="false"/>
        <setting id="require_seeds" type="bool" label="30024" default="false"/>
    </category>
    <!-- Resolutions -->
    <category label="30030">
        <setting id="require_resolution" type="bool" visible="false"/>{}
    </category>
    <!-- Release Types -->
    <category label="30040">
        <setting id="require_release_type" type="bool" visible="false"/>{}
    </category>
</settings>""".format(providers, resolutions, release_types)


def generate_settings_and_save(args):
    with open(args.settings_path, "w") as f:
        f.write(generate_settings(args.providers_path, enabled_count=args.enabled_count))


def parse_query(args):
    with ScraperRunner(get_scrapers(args)) as runner:
        for scraper, results in runner.parse_query(args.search):
            print_results(scraper.name, results)


def parse_media(args):
    with ScraperRunner(get_scrapers(args)) as runner:
        for scraper, results in runner.parse(args.parser, {f: getattr(args, f) or "" for f in args.fields}):
            print_results(scraper.name, results)


def convert_json_to_xml(args):
    if re.match("https?://", args.path):
        data = requests.get(args.path).content
    else:
        with open(args.path, "rb") as f:
            data = f.read()

    print(minidom.parseString(ElementTree.tostring(create_xml_tree(json.loads(data)))).toprettyxml(indent=" " * 4))


def main():
    parser = argparse.ArgumentParser(description="Tool to test and verify script.flix.magneto providers")
    subparsers = parser.add_subparsers(title="command", dest="command", required=True, help="Command to execute")

    parser_verify = subparsers.add_parser("verify", help="Verifies the providers.json file")
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

    parser_generate_settings = subparsers.add_parser("generate-settings", help="Generates the settings.xml file")
    parser_generate_settings.add_argument("-e", "--enabled-count", type=int, default=-1,
                                          help="The number of enabled providers by default")
    parser_generate_settings.set_defaults(func=generate_settings_and_save)

    parser_parse = subparsers.add_parser("parse", help="Runs the specified parser and lists the results")
    parsers = parser_parse.add_subparsers(title="parser", dest="parser", description="The parser to execute",
                                          required=True)
    query_parser = parsers.add_parser("query", help="Parses the results for the provided query")
    query_parser.add_argument("search", help="The search query")
    query_parser.set_defaults(func=parse_query)
    movie_parser = parsers.add_parser("movie", help="Parses the results for the provided movie")
    movie_parser.set_defaults(func=parse_media, fields=("tmdb_id", "title", "year"))
    show_parser = parsers.add_parser("show", help="Parses the results for the provided show")
    show_parser.set_defaults(func=parse_media, fields=("tmdb_id", "title", "year"))
    season_parser = parsers.add_parser("season", help="Parses the results for the provided season")
    season_parser.set_defaults(func=parse_media, fields=("tmdb_id", "title", "season"))
    episode_parser = parsers.add_parser("episode", help="Parses the results for the provided episode")
    episode_parser.set_defaults(func=parse_media, fields=("tmdb_id", "title", "season", "episode"))

    parser_json2xml = subparsers.add_parser("json2xml", help="Converts a json to XML")
    parser_json2xml.add_argument("path", help="The JSON file path/url")
    parser_json2xml.set_defaults(func=convert_json_to_xml)

    for p in (movie_parser, show_parser, season_parser, episode_parser):
        p.add_argument("--tmdb-id", type=str, help="The TMDB identifier")
        p.add_argument("--title", type=str, required=True, help="The media title")

    for p in (movie_parser, show_parser):
        p.add_argument("--year", type=int, help="The year of the release")

    for p in (season_parser, episode_parser):
        p.add_argument("--season", type=int, required=True, help="The season number")

    episode_parser.add_argument("--episode", type=int, required=True, help="The episode number")

    for p in (parser_verify, parser_generate_settings):
        p.add_argument("-s", "--settings-path", type=str, default=SETTINGS_PATH,
                       help="The addon settings.xml path (default: {})".format(SETTINGS_PATH))

    for p in (parser_verify, parser_generate_settings, query_parser,
              movie_parser, show_parser, season_parser, episode_parser):
        p.add_argument("-p", "--providers-path", type=str, default=PROVIDERS_PATH,
                       help="The providers.json path (default: {})".format(PROVIDERS_PATH))

    for p in (query_parser, movie_parser, show_parser, season_parser, episode_parser):
        p.add_argument("-i", "--provider-id", type=str, help="The provider identifier")

    for p in (parser_verify, parser_xpath, parser_generate_settings, query_parser,
              movie_parser, show_parser, season_parser, episode_parser, parser_json2xml):
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
