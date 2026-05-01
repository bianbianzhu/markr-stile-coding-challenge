import inspect
from defusedxml.ElementTree import fromstring
print("signature:", inspect.signature(fromstring))
print("module:", fromstring.__module__)
print("doc:", (fromstring.__doc__ or "")[:200])
