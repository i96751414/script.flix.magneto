# Provider definition examples

Below one can find examples of different definitions for `providers.json`.
This is not an extensive list of examples nor intends to demonstrate all features of a provider, however it server as a
good starting point for creating the providers' definition.

## using an additional parser

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

## using a json parser

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

## mutating data

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
