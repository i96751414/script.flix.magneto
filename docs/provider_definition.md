# Defining a Provider


## How to add a magnet provider

Adding a provider (scraper) requires 3 simple steps:

-   Add the provider definition in `resources/providers.json` 
    (see [provider.schema.json](../resources/providers.schema.json)) containing all required fields (see *Provider fields* 
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
