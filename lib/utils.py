import re

try:
    from urllib.parse import unquote, unquote_plus
except ImportError:
    # noinspection PyUnresolvedReferences
    from urllib import unquote, unquote_plus

text = u"".__class__


class Title(text):
    def __new__(cls, title, titles=None):
        self = super(Title, cls).__new__(cls, title)
        self._titles = titles or dict()
        return self

    def __getattr__(self, item):
        return self._titles.get(item, self)


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


def colored_text(s, color):
    return "[COLOR {}]{}[/COLOR]".format(color, s)


def bold(s):
    return "[B]{}[/B]".format(s)
