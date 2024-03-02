# Testing the provider

The `provider_test.py` tool was created so developers can test their providers without having to run Kodi. In order to
run the tool, install the required dependencies:

```shell
pip3 install requests jsonschema htmlement defusedxml
```

or

```shell
pip3 install -r requirements.txt
```

Then, you can either verify the providers file, test the xpath expression, generate the `settings.xml` file for Kodi or
run the providers (parse) against the provided query/search parameters.

## Supported commands

This section describes all the supported commands of the `provider_test.py` tool and for each of them provides an
example.

### verify

The `verify` command performs some preliminary checks against the providers file:

-   Validates the providers' schema;
-   Validates the settings.xml file against the providers.json file;
-   Verifies if all the necessary data items are defined in the providers.json file;
-   Verifies if the defined attributes are correct (icon and color).

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

The `query` search type is the simplest one. It is a raw search, and thus it does not require any additional arguments.

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
