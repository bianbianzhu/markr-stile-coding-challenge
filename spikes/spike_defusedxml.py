from defusedxml.ElementTree import fromstring as safe_fromstring
from xml.etree.ElementTree import Element

xml = b"<root><child a='1'>hi</child></root>"
parsed = safe_fromstring(xml)
print("type:", type(parsed))
print("isinstance Element:", isinstance(parsed, Element))
print("tag:", parsed.tag)
print("child tag:", parsed.find("child").tag)
print("attr:", parsed.find("child").get("a"))

# Confirm it rejects entity expansion
try:
    safe_fromstring(b'<!DOCTYPE x [<!ENTITY a "boom">]><x>&a;</x>')
    print("entity: ACCEPTED (unexpected)")
except Exception as exc:
    print("entity rejected:", type(exc).__name__)
