from __future__ import annotations

import json
import zipfile
from pathlib import Path
from lxml import etree

NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}

path = Path("work/source.docx")
with zipfile.ZipFile(path) as zf:
    root = etree.fromstring(zf.read("word/document.xml"))

rows = []
for idx, p in enumerate(root.xpath("//w:body/w:p", namespaces=NS), 1):
    chunks = []
    for node in p.xpath(".//w:t | .//w:tab | .//w:br", namespaces=NS):
        tag = etree.QName(node).localname
        chunks.append(node.text or "" if tag == "t" else "\t" if tag == "tab" else "\n")
    num = p.xpath("./w:pPr/w:numPr/w:numId/@w:val", namespaces=NS)
    ilvl = p.xpath("./w:pPr/w:numPr/w:ilvl/@w:val", namespaces=NS)
    rows.append({"i": idx, "num": num[0] if num else None, "level": ilvl[0] if ilvl else None, "text": "".join(chunks)})

print(json.dumps(rows, ensure_ascii=True, indent=2))
