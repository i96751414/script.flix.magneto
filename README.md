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
-   Uses xpath for getting items (even for json APIs)
-   Allows to mutate parsed data, using a custom formatter
-  Possible to test the providers using `provider_test.py` script

## How to add a magnet provider

Adding a provider (scraper) requires 3 simple steps:

-   Add the provider definition in `resources/providers.json` (
    see [provider.schema.json](resources/providers.schema.json))

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

## Custom formatter

This section describes the supported conversions/formats.

|Conversion|Description|
|----------|-----------|
|`{<field>!u}`|Converts the specified `<field>` to upper case|
|`{<field>!l}`|Converts the specified `<field>` to lower case|
|`{<field>!A}`|Strips all accents from the specified `<field>`|
|`{<field>!b}`|Converts the specified `<field>` to a human readable size|

|Format|Description|
|------|-----------|
|`{<field>:q}`|Quotes the specified `<field>`|
|`{<field>:q<letter>}`|Quotes the specified `<field>`, replacing all spaces with the specified letter (i.e. `{url:q+}`)|

### Accessing alternative titles

By default, one can access the movie/show title by using `{title}`. However, alternative titles can also be used by
accessing the ISO 3166-1 lowercase country code (e.g: `{title.us}`). If such title does not exist, the original title
is used. One can also access the current country code with `{title.auto}`.

## Examples

### using an additional parser

Additional parsers are optional parsers which are run after the main parser (`results_parser`) has run. These don't have
the `rows` definition as it can only be defined once.

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
size by `results_parser.mutate` (note `{size!b}`).

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

## Testing the provider

The `provider_test.py` tool was created so developers can test their providers without having to run Kodi. In order to
run the tool, install the required dependencies:

```shell
pip3 install requests jsonschema htmlement defusedxml
```

Then, you can either verify the providers file or test the xpath expression.

### verify

The `verify` command performs some preliminary checks against the providers file:

-   Validates the providers' schema;
-   Validates the settings.xml file against the providers.json file;
-   Analyses the set attributes (icon and color).

```shell
python3 provider_test.py verify
```

### xpath

The `xpath` command evaluates the provided xpath against the provided URL contents. It supports JSON, XML and HTML (
default) content types, and it can be run as a single xpath or as a list of xpaths (by using `--row` option).

```shell
python3 provider_test.py xpath --rows ".//tbody/tr" "./td[2]/a[1]/@title" "https://www.foobar.com/?q=baz"
```