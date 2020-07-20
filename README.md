# script.flix.magneto

A [Flix](https://github.com/i96751414/plugin.video.flix) provider which uses [Torrest](https://github.com/i96751414/plugin.video.torrest) as backend for playing magnets.
It consists of a very clean implementation of an abstract scraper which is intended to work against many sites as possible.

## Features

- Clean code
- Very easy to add/update scrapers
- Very fast
- Intended to be as generic as possible
- Uses xpath for getting items (even for json APIs)
- Allows to mutate parsed data, using a custom formatter

## How to add a magnet provider?

Adding a provider (scraper) requires 3 simple steps:
- Add the provider definition in `resources/providers.json` (see [provider-schema.json](resources/providers-schema.json))
- Add the provider icon in `resources/provider_icons`
- Add the provider to `resources/settings.xml`:
  ```xml
  <setting id="<provider.id>" type="bool" label="<provider.name>" default="<true|false>"/>  
  ```
  where:
  - `provider.id` - The provider name (as specified in `providers.json`) in lower case with all spaces replaced by dots.
  - `provider.name` - The provider name (as specified in `providers.json`).
  - The default boolean value specifies if the provider is either enabled (true) or disabled (false) by default.

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

## Examples

### using an additional parser

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

In the below example, `size` is first parsed by the `results_parser` and then it is converted to a human readable size (note `"{size!b}`)

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