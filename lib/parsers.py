import json
import logging
import re
from xml.etree.ElementTree import Element, SubElement  # nosec

import htmlement
from defusedxml import ElementTree

from lib.utils import text


class ETParser(object):
    _attr_re = re.compile(r"^(.+)/@([a-zA-Z0-9_ ]+)$")
    _text_re = re.compile(r"^(.+)/text\(\)$")
    _tail_re = re.compile(r"^(.+)/tail\(\)$")
    _parents_re = re.compile(r"\.{2,3}")

    def __init__(self, root):
        self._root = root
        self._parents = None

    @property
    def parents(self):
        if self._parents is None:
            self._parents = dict((c, p) for p in self._root.iter() for c in p)
        return self._parents

    def parse_results(self, rows, data):
        return [{key: self._xpath_element(element, xpath) for key, xpath in data.items()}
                for element in self._root.iterfind(rows)]

    def update_result(self, data, result):
        for key, xpath in data.items():
            result[key] = self._xpath_element(self._root, xpath)

    def _xpath_find(self, element, path):
        paths = self._parents_re.split(path)
        if len(paths) > 1:
            for i, p in enumerate(paths[:-1]):
                if i > 0 and p.startswith("/"):
                    p = p[1:]
                if p.endswith("/"):
                    p = p[:-1]
                element = self.parents[element.find(p) if p else element]
            element = element.find("." + paths[-1])
        else:
            element = element.find(paths[0])
        return element

    def _xpath_element(self, element, path):
        logging.debug("Getting %s path from element %s", path, element.tag)
        attr_match = self._attr_re.match(path)
        if attr_match:
            return self._xpath_find(element, attr_match.group(1)).attrib[attr_match.group(2)]
        text_match = self._text_re.match(path)
        if text_match:
            return self._xpath_find(element, text_match.group(1)).text
        tail_match = self._tail_re.match(path)
        if tail_match:
            return self._xpath_find(element, tail_match.group(1)).tail
        raise ValueError("Only .../@attr, .../text() and .../tail() paths are supported")


class XMLParser(ETParser):
    def __init__(self, content):
        super(XMLParser, self).__init__(ElementTree.fromstring(content))


class HTMLParser(ETParser):
    def __init__(self, content):
        super(HTMLParser, self).__init__(htmlement.fromstring(content))


def create_xml_tree(obj, root_name="root", attribute_type=False):
    root = Element(root_name)
    _create_xml_tree(root, obj, attribute_type=attribute_type)
    return root


def _check_tag(tag, invalid_xml_tag_re=re.compile(r"[^a-zA-Z0-9-_.]")):
    tag = invalid_xml_tag_re.sub("", tag)
    if len(tag) == 0 or tag[0].isdigit():
        tag = "_" + tag
    return tag


def _create_xml_tree(root, obj, **kwargs):
    attribute_type = kwargs.get("attribute_type", False)
    tag_str = kwargs.get("tag_str", text)

    if isinstance(obj, (tuple, list)):
        for v in obj:
            _create_xml_tree(SubElement(root, "item"), v, **kwargs)
    elif isinstance(obj, dict):
        for k, v in obj.items():
            if attribute_type:
                _kwargs, tag = {"key_type": k.__class__.__name__, "key": tag_str(k)}, "item"
            else:
                _kwargs, tag = {}, _check_tag(tag_str(k))
            _create_xml_tree(SubElement(root, tag, **_kwargs), v, **kwargs)
    else:
        root.text = tag_str(obj)
    if attribute_type:
        root.attrib["type"] = obj.__class__.__name__


class JSONParser(ETParser):
    def __init__(self, content, **kwargs):
        super(JSONParser, self).__init__(create_xml_tree(json.loads(content), **kwargs))
