from __future__ import annotations

from typing import cast
from xml.etree.ElementTree import Element

from defusedxml.ElementTree import fromstring as _safe_fromstring


class MalformedXMLError(ValueError):
    pass


def safe_parse(body: bytes) -> Element:
    if not body or not body.strip():
        raise MalformedXMLError("empty or whitespace-only body")
    try:
        parsed = cast(Element, _safe_fromstring(body))
    except Exception as exc:
        raise MalformedXMLError(str(exc)) from exc
    return parsed
