import re

try:
    from urllib.parse import unquote, unquote_plus
except ImportError:
    # noinspection PyUnresolvedReferences
    from urllib import unquote, unquote_plus


class Title(object):
    def __init__(self, title, titles=None):
        # type:(str, dict)->None
        self._title = title
        self._titles = titles or dict()

    @property
    def title(self):
        return self._title

    def __getattr__(self, item):
        return self._titles.get(item, self._title)

    def __format__(self, format_spec):
        return self._title


class InvalidMagnet(Exception):
    pass


class Magnet(object):
    _info_hash_re = re.compile(r"\burn:btih:([A-Fa-f\d]{40})\b")
    _tracker_re = re.compile(r"\btr=([^&]+)")
    _name_re = re.compile(r"\bdn=([^&]+)")

    def __init__(self, magnet):
        self._magnet = magnet

    @property
    def magnet(self):
        return self._magnet

    def parse_info_hash(self):
        match = self._info_hash_re.search(self._magnet)
        if match is None:
            raise InvalidMagnet("Unable to parse info hash from magnet")
        return match.group(1)

    def parse_trackers(self):
        return [unquote(t) for t in self._tracker_re.findall(self._magnet)]

    def parse_name(self):
        match = self._name_re.search(self._magnet)
        return unquote_plus(match.group(1)) if match else None


resolution_colors = {
    "240p": "FF996600",
    "480p": "FFA56F01",
    "720p": "FF539A02",
    "1080p": "FF0166FC",
    "2K": "FFF15052",
    "4K": "FF6BB9EC",
}


def colored_text(text, color):
    return "[COLOR {}]{}[/COLOR]".format(color, text)


def bold(text):
    return "[B]{}[/B]".format(text)
