# script.flix.magneto

A [Flix](https://github.com/i96751414/plugin.video.flix) provider which uses [Torrest](https://github.com/i96751414/plugin.video.torrest) as backend for playing magnets.

## How to add a magnet provider?

Adding a provider requires 3 simple steps:
- Add the provider definition in `resources/providers.json` (see [provider-schema.json](resources/providers-schema.json))
- Add the provider icon in `resources/provider_icons`
- Add the provider to `resources/settings.xml`:
  ```xml
  <setting id="<provider.id>" type="bool" label="<provider.name>" default="<true|false>"/>  
  ```

### providers.json html example with additional parser

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

### providers.json json example

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