import pytest
from xml.etree.ElementTree import Element

from markr.ingestion.xml_parser import MalformedXMLError, safe_parse


def test_returns_stdlib_element():
    e = safe_parse(b"<a><b>1</b></a>")
    assert isinstance(e, Element)
    assert e.tag == "a"


def test_malformed_raises():
    with pytest.raises(MalformedXMLError):
        safe_parse(b"<a>")


def test_empty_body_raises():
    with pytest.raises(MalformedXMLError):
        safe_parse(b"")


def test_whitespace_only_raises():
    with pytest.raises(MalformedXMLError):
        safe_parse(b"   \n\t  ")
