import ast
import re
import unicodedata
from string import Formatter
import operator

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


class ExtendedFormatter(Formatter):
    _safe_calls = dict(replace=regex_replace, split=str.split, get=operator.getitem)

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
            value = self.evaluate_calls(value, format_spec)
            if not isinstance(value, str):
                value = str(value)
            return value
        return super(ExtendedFormatter, self).format_field(value, format_spec)

    def evaluate_calls(self, value, string):
        return self._evaluate_calls(value, ast.parse(string, mode="eval").body)

    def _evaluate_calls(self, value, node):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                return self._execute_call(node.func.id, value, node)
            if isinstance(node.func, ast.Attribute):
                return self._execute_call(node.func.attr, self._evaluate_calls(value, node.func.value), node)
            raise ValueError("Unexpected function call")
        raise ValueError("Unsupported syntax")

    def _execute_call(self, name, value, node):
        call = self._safe_calls.get(name)
        if call is not None:
            args = tuple(self._get_arg(arg) for arg in node.args)
            kwargs = {kw.arg: self._get_arg(kw.value) for kw in node.keywords}
            return call(value, *args, **kwargs)
        raise ValueError("Unsupported function call: {}".format(name))

    @staticmethod
    def _get_arg(node):
        if isinstance(node, Constant):
            return node.value
        if isinstance(node, ast.Str):
            return node.s
        if isinstance(node, ast.Num):
            return node.n

        raise ValueError("Unsupported argument: {}".format(node))


f = ExtendedFormatter()
print(f.format("{a:replace('a','b').replace('b','B')}", a="1a2a3"))
