import re
import sys
from base64 import b32decode
from binascii import hexlify

try:
    from urlparse import urlparse, parse_qs
except ImportError:
    from urllib.parse import urlparse, parse_qs

PY3 = sys.version_info.major >= 3
text = u"".__class__


class CachedCall(object):
    def __init__(self, callback):
        self._cache = {}
        self._callback = callback

    def __call__(self, key):
        try:
            value = self._cache[key]
        except KeyError:
            value = self._callback(key)
            self._cache[key] = value
        return value


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
    _info_hash_re = re.compile(r"^(?:urn:btih:(?:([A-Fa-f\d]{40})|([A-Za-z2-7]{32}))|urn:btmh:1220([A-Fa-f\d]{64}))$")

    def __init__(self, info_hash, dn=None, xl=None, tr=(), xs=None, as_=None, ws=(), kt=None, supplements=None):
        self._info_hash = info_hash
        self._dn = dn
        self._xl = xl
        self._tr = tr
        self._xs = xs
        self._as = as_
        self._ws = ws
        self._kt = kt.split() if kt else []
        self._supplements = supplements or {}

    @property
    def info_hash(self):
        return self._info_hash

    @classmethod
    def parse_info_hash(cls, xt):
        match = cls._info_hash_re.match(xt)
        if not match:
            raise InvalidMagnet("Unable to parse info hash from magnet")

        sha1_hash, base32_hash, sha256_hash = match.groups()
        if sha1_hash is not None:
            info_hash = sha1_hash
        elif base32_hash is not None:
            info_hash = hexlify(b32decode(base32_hash)).decode()
        else:
            # TODO: Currently not supporting v2 info hashes
            raise InvalidMagnet("v2 info hashes are not supported")

        return info_hash.lower()

    @classmethod
    def from_string(cls, uri, ignore_unknown=True):
        info = urlparse(uri.strip(), scheme="magnet", allow_fragments=False)
        if not info.scheme == "magnet":
            raise InvalidMagnet("Not a magnet URI")

        query = parse_qs(info.query)
        xt_list = query.pop("xt", None)

        if not xt_list:
            raise InvalidMagnet("Missing exact topic ('xt')")
        elif len(xt_list) > 1:
            # TODO: Currently not supporting v2-hybrid info hashes
            raise InvalidMagnet("Multiple exact topics ('xt')")

        parameters = dict(info_hash=cls.parse_info_hash(xt_list[0]))  # type: dict[str, (str, list)]

        def parse_single_value_param(param, name, internal_param=None):
            param_list = query.pop(param, None)
            if param_list:
                if len(param_list) > 1:
                    raise InvalidMagnet("Multiple {}s ('{}')".format(name, param))
                parameters[internal_param or param] = param_list[0]

        def parse_multi_value_param(param):
            param_list = query.pop(param, None)
            if param_list:
                parameters[param] = param_list

        def parse_supplements(internal_param):
            parameters[internal_param] = {key[2:]: query.pop(key) for key in list(query.keys()) if key.startswith("x.")}

        # Parameters that accept only one value
        parse_single_value_param("dn", "display name")
        parse_single_value_param("xl", "exact length")
        parse_single_value_param("xs", "exact source")
        parse_single_value_param("as", "acceptable source", "as_")
        parse_single_value_param("kt", "keyword topic")

        # Parameters that accept multiple values
        parse_multi_value_param("tr")
        parse_multi_value_param("ws")

        # Parameters in supplement format
        parse_supplements("supplements")

        if not ignore_unknown and len(query) > 0:
            raise InvalidMagnet("Unknown parameters: {}".format(list(query.keys())))

        return cls(**parameters)


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
