# script.flix.magneto

[![Build Status](https://github.com/i96751414/script.flix.magneto/workflows/build/badge.svg)](https://github.com/i96751414/script.flix.magneto/actions?query=workflow%3Abuild)
[![Codacy Badge](https://app.codacy.com/project/badge/Grade/ffe8ff7028674c2db50a2b3d4de1cebc)](https://www.codacy.com/gh/i96751414/script.flix.magneto/dashboard?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=i96751414/script.flix.magneto&amp;utm_campaign=Badge_Grade)

A [Flix](https://github.com/i96751414/plugin.video.flix) provider which
uses [Torrest](https://github.com/i96751414/plugin.video.torrest) as backend for playing magnets. It consists of a very
clean implementation of an abstract scraper which is intended to work against as many sites as possible.

## Features

-   Clean and simple code
-   Very easy to add/update scrapers
-   Very fast
-   Intended to be as generic as possible
-   Uses [xpath](https://docs.python.org/3/library/xml.etree.elementtree.html#xpath-support) for getting items (even for json APIs)
-   Allows to mutate parsed data, using a custom formatter
-   Possible to test the providers using `provider_test.py` script

## How to add a magnet provider

Adding a provider (scraper) requires 3 simple steps:

-   Add the provider definition in `resources/providers.json` 
    (see [provider.schema.json](resources/providers.schema.json)) containing all required fields (see *Provider fields* 
    section)

-   Add the provider icon in `resources/provider_icons`

-   Add the provider to `resources/settings.xml`:
    ```xml
    <setting id="<provider.id>" type="bool" label="<provider.name>" default="<true|false>"/>  
    ```
    where:
    -   `provider.id` is the provider name (as specified in `providers.json`) in lower case with all spaces replaced by
        dots.

    -   `provider.name` is the provider name (as specified in `providers.json`).
  
    -   The default boolean value specifies if the provider is either enabled (true) or disabled (false) by default.

## Provider fields

The below table refers to all fields a provider must/can have.

| Type      | Field name | Required | Description                                                                          |
|-----------|------------|----------|--------------------------------------------------------------------------------------|
| data      | title      | yes      | The result title                                                                     |
| data      | magnet     | yes      | The result magnet link                                                               |
| data      | seeds      | no       | The result seeds number                                                              |
| data      | leeches    | no       | The result leeches number                                                            |
| data      | size       | no       | The result total size                                                                |
| attribute | icon       | no       | The provider icon path (absolute or relative to the addon resources path)            |
| attribute | color      | no       | The color to use on the provider results (hex code, ex: `FF539A02`)                  |
| keyword   | movie      | yes      | The keywords used for searching movies (ex: `"{title} {year}"`)                      |
| keyword   | show       | yes      | The keywords used for searching shows (ex: `"{title}"`)                              |
| keyword   | season     | yes      | The keywords used for searching seasons (ex: `"{title} S{season:02}"`)               |
| keyword   | episode    | yes      | The keywords used for searching episodes (ex: `"{title} S{season:02}E{episode:02}"`) |

## Custom formatter

This section describes the supported conversions/formats.

| Conversion    | Description                                               |
|---------------|-----------------------------------------------------------|
| `{<field>!u}` | Converts the specified `<field>` to upper case            |
| `{<field>!l}` | Converts the specified `<field>` to lower case            |
| `{<field>!A}` | Strips all accents from the specified `<field>`           |
| `{<field>!b}` | Converts the specified `<field>` to a human readable size |

| Format                | Description                                                                                      |
|-----------------------|--------------------------------------------------------------------------------------------------|
| `{<field>:q}`         | Quotes the specified `<field>`                                                                   |
| `{<field>:q<letter>}` | Quotes the specified `<field>`, replacing all spaces with the specified letter (i.e. `{url:q+}`) |

Python default conversions/formats are also supported.
See [custom string formatting](https://docs.python.org/3/library/string.html#custom-string-formatting).

### Functions support

Functions support is **experimental**. Please see the below table for the available functions.

| Function                      | Description                                                         |
|-------------------------------|---------------------------------------------------------------------|
| `{<field>:replace(str, str)}` | Replaces the specified RegEx pattern with the provided string       |
| `{<field>:split(str)}`        | Splits the field (assuming its a string) by the specified delimiter |
| `{<field>:get(int)}`          | Gets the item at the provided index. Useful for split operations    |

Function chaining is also supported. To do so, simply chain functions in the format specification:
`{<field>:split(' ').get(0)}`

### Accessing alternative titles

By default, one can access the movie/show title by using `{title}`. However, alternative titles can also be used by
accessing the ISO 3166-1 lowercase country code (e.g: `{title.us}`). If such title does not exist, the original title
is used. One can also access the current country code with `{title.auto}`.

### Fields available

The following table describes the fields available when building keywords and also the media types where these fields
may be used.

| Field       | Description                                 | Movie | Show | Season | Episode |
|-------------|---------------------------------------------|-------|------|--------|---------|
| `{tmdb_id}` | The TMDB identifier                         | X     | X    | X      | X       |
| `{title}`   | The title as specified in the section above | X     | X    | X      | X       |
| `{year}`    | The release year (optional)                 | X     | X    |        |         |
| `{season}`  | The season number                           |       |      | X      | X       |
| `{episode}` | The episode number                          |       |      |        | X       |

## Examples

### using an additional parser

Additional parsers are optional parsers which are run after the main parser (`results_parser`) has run. These may or may
not have the `rows` definition - if present, the results will be updated to contain the new ones caught by this parser;
if not present, the current results are updated to contain the `data` parameters.

```json
[
  {
    "name": "Example",
    "base_url": "https://example.com",
    "results_parser": {
      "url": "/search/{query:q+}/",
      "rows": ".//tbody/tr",
      "data": {
        "torrent_url": "td[1]/a[2]/@href",
        "title": "td[1]/a[2]/text()",
        "seeds": "td[2]/text()",
        "leeches": "td[3]/text()",
        "size": "td[5]/text()"
      }
    },
    "additional_parsers": [
      {
        "url": "{torrent_url}",
        "data": {
          "magnet": ".//main/div/ul/li/a/@href"
        }
      }
    ],
    "keywords": {
      "movie": "{title} {year}",
      "show": "{title}",
      "season": "{title} S{season:02}",
      "episode": "{title} S{season:02}E{episode:02}"
    },
    "attributes": {
      "color": "FFF14E13",
      "icon": "provider_icons/example.png"
    }
  }
]
```

### using a json parser

One can parse json data by setting `results_parser.type` as `json`.

```json
[
  {
    "name": "Example",
    "base_url": "https://example.com",
    "results_parser": {
      "url": "/api/v2/example.json?q={query:q}",
      "type": "json",
      "rows": "./data/movies//torrents/",
      "data": {
        "title": "./title/text()",
        "size": "./size/text()",
        "seeds": "./seeds/text()",
        "leeches": "./peers/text()",
        "magnet": "./magnet/text()"
      }
    },
    "keywords": {
      "movie": "{title} {year}",
      "show": "{title}",
      "season": "{title} S{season:02}",
      "episode": "{title} S{season:02}E{episode:02}"
    },
    "attributes": {
      "color": "FFF14E13",
      "icon": "provider_icons/example.png"
    }
  }
]
```

### mutating data

In the below example, `size` is first parsed by the `results_parser.data` and then it is converted to a human-readable
size by `results_parser.mutate` (note `{size!b}`). Mutations can be defined either by an object or an array of objects.

```json
[
  {
    "name": "Example",
    "base_url": "https://example.com",
    "results_parser": {
      "url": "/search/{query:q+}/",
      "rows": ".//tbody/tr",
      "data": {
        "magnet": "td[1]/a[2]/@href",
        "title": "td[1]/a[2]/text()",
        "seeds": "td[2]/text()",
        "leeches": "td[3]/text()",
        "size": "td[5]/text()"
      },
      "mutate": {
        "size": "{size!b}"
      }
    },
    "keywords": {
      "movie": "{title} {year}",
      "show": "{title}",
      "season": "{title} S{season:02}",
      "episode": "{title} S{season:02}E{episode:02}"
    },
    "attributes": {
      "color": "FFF14E13",
      "icon": "provider_icons/example.png"
    }
  }
]
```

In this specific case only a single mutate operation was required. However, if multiple are required for the same
parameter, mutate can be defined as an array.

## Testing the provider

The `provider_test.py` tool was created so developers can test their providers without having to run Kodi. In order to
run the tool, install the required dependencies:

```shell
pip3 install requests jsonschema htmlement defusedxml
```

Then, you can either verify the providers file, test the xpath expression, generate the `settings.xml` file for Kodi or
run the providers (parse) against the provided query/search parameters.

### verify

The `verify` command performs some preliminary checks against the providers file:

-   Validates the providers' schema;
-   Validates the settings.xml file against the providers.json file;
-   Analyses the set attributes (icon and color).

```shell
python3 provider_test.py verify
```

### xpath

The `xpath` command evaluates the provided xpath against the provided URL contents. It supports JSON, XML and HTML
(default) content types, and it can be run as a single xpath or as a list of xpaths (by using `--row` option).

```shell
python3 provider_test.py xpath --rows ".//tbody/tr" "./td[2]/a[1]/@title" "https://www.foobar.com/?q=baz"
```

### generate-settings

The `generate-settings` command automatically generates a `settings.xml` file suitable for Kodi. It generates the
providers list from the `providers.json` file. By default, this file
is located under `resources/settings.xml`.

```shell
python3 provider_test.py generate-settings
```

### parse

The `parse` command allows to emulate a real search, using real providers. Depending on the search type, additional
arguments may be required. All parse commands can be executed against a single provider. To do so, use the `-i` or
`--provider-id` argument (e.g. `--provider-id <provider-id>`).

#### query

The `query` search type is the simplest one. It is a raw search and thus it does not require any additional arguments.

```shell
python3 provider_test.py parse query "big buck bunny"
```

#### movie

The `movie` search type gathers information for the provided movie.

```shell
python3 provider_test.py parse movie --tmdb-id 10378 --title "Big Buck Bunny" --year 2008
```

#### show

The `show` search type gathers information for the provided show.

```shell
python3 provider_test.py parse show --tmdb-id 1668 --title "Friends" --year 1994
```

#### season

The `season` search type gathers information for the provided show and season.

```shell
python3 provider_test.py parse season --tmdb-id 1668 --title "Friends" --season 1
```

#### episode

The `episode` search type gathers information for the provided show, season and episode.

```shell
python3 provider_test.py parse episode --tmdb-id 1668 --title "Friends" --season 1 --episode 1
```

### json2xml

The `json2xml` command allows to convert a JSON file to XML. This is useful when using JSON APIs and xpath.

```shell
python3 provider_test.py json2xml resources/providers.schema.json
```
