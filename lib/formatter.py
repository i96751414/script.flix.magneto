import ast
import re
import unicodedata
from string import Formatter

try:
    from ast import Constant
except ImportError:
    class Constant(object):
        value = None

try:
    from urllib.parse import quote
except ImportError:
    # noinspection PyUnresolvedReferences
    from urllib import quote


def strip_accents(s):
    return "".join([c for c in unicodedata.normalize("NFD", s) if not unicodedata.combining(c)])


def sizeof_fmt(num, suffix="B", divisor=1000.0):
    for unit in ("", "k", "M", "G", "T", "P", "E", "Z"):
        if abs(num) < divisor:
            return "{:.2f} {}{}".format(num, unit, suffix)
        num /= divisor
    return "{:.2f} {}{}".format(num, "Y", suffix)


def regex_replace(value, pattern, repl):
    return re.sub(pattern, repl, value)


def get_at_index(value, index):
    return value[index]


class ExtendedFormatter(Formatter):
    _safe_calls = dict(replace=regex_replace, split=str.split, get=get_at_index)

    def convert_field(self, value, conversion):
        if conversion == "u":
            return value.upper()
        elif conversion == "l":
            return value.lower()
        elif conversion == "A":
            return strip_accents(value)
        elif conversion == "b":
            return sizeof_fmt(int(value))
        return super(ExtendedFormatter, self).convert_field(value, conversion)

    def format_field(self, value, format_spec):
        if format_spec == "q":
            return quote(value.encode("utf-8"), "")
        elif format_spec.startswith("q") and len(format_spec) == 2:
            return quote(value.encode("utf-8"), " ").replace(" ", format_spec[1])
        elif format_spec.endswith(")") and "(" in format_spec:
            # Experimental
            # Poor check for function format on purpose
            for function, args in self.parse_functions(format_spec):
                value = function(value, *args)
            if not isinstance(value, str):
                value = str(value)
            return value
        return super(ExtendedFormatter, self).format_field(value, format_spec)

    def parse_functions(self, string):
        return self._parse_functions(ast.parse(string, mode="eval").body)

    def _parse_functions(self, node):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                yield self._get_call_and_args(node.func.id, node.args)
            elif isinstance(node.func, ast.Attribute):
                for ret in self._parse_functions(node.func.value):
                    yield ret
                yield self._get_call_and_args(node.func.attr, node.args)
            else:
                raise ValueError("Unexpected function call")
        else:
            raise ValueError("Not a function call")

    def _get_call_and_args(self, node_name, node_args):
        call = self._safe_calls.get(node_name)
        if call is not None:
            return call, tuple(self._get_args(node_args))
        raise ValueError("Unsupported function call: {}".format(node_name))

    @staticmethod
    def _get_args(node_args):
        for a in node_args:
            if isinstance(a, Constant):
                yield a.value
            elif isinstance(a, ast.Str):
                yield a.s
            elif isinstance(a, ast.Num):
                yield a.n
            else:
                raise ValueError("Unsupported argument: {}".format(a))
