![](resources/images/magneto_banner.png)

[![Build Status](https://github.com/i96751414/script.flix.magneto/workflows/build/badge.svg)](https://github.com/i96751414/script.flix.magneto/actions?query=workflow%3Abuild)
[![Codacy Badge](https://app.codacy.com/project/badge/Grade/ffe8ff7028674c2db50a2b3d4de1cebc)](https://app.codacy.com/gh/i96751414/script.flix.magneto/dashboard?utm_source=gh&utm_medium=referral&utm_content=&utm_campaign=Badge_grade)

## What it is

A [Flix](https://github.com/i96751414/plugin.video.flix) provider which
uses [Torrest](https://github.com/i96751414/plugin.video.torrest) as backend for playing magnets. It consists of a very
clean implementation of an abstract scraper which is intended to work against as many sites as possible.

## Features

-   Very fast
-   Clean and simple code, easy to maintain
-   Very easy to add/update scrapers
-   Intended to be as generic as possible
-   Supports different parsers: HTML, XML and JSON
-   Uses [xpath](https://docs.python.org/3/library/xml.etree.elementtree.html#xpath-support) for getting items (even for JSON APIs)
-   Can parse sub-pages as well as multi-pages results
-   Allows to mutate parsed data, using a custom formatter
-   Possible to test the providers using `provider_test.py` script
-   Well documented:
    -   Documentation on [how to define and add a provider](docs/provider_definition.md)
    -   Documentation on [how to use the provider_test tool, with examples](docs/provider_test.md)
    -   With [examples of providers' definitions](docs/examples.md)
