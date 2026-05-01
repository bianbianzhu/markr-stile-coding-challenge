# T2.1 defusedxml output

Command:
`uv run python spikes/sig_defusedxml.py && uv run python spikes/spike_defusedxml.py`

Output:
```text
signature: (text, forbid_dtd=False, forbid_entities=True, forbid_external=True)
module: defusedxml.common
doc:
type: <class 'xml.etree.ElementTree.Element'>
isinstance Element: True
tag: root
child tag: child
attr: 1
entity rejected: EntitiesForbidden
```
