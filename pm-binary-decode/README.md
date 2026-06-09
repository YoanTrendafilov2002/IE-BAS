# PM Binary Decode

Diagnostic utility for reverse-engineering binary particulate-matter exports.
It extracts strings, block spacing, hex dumps, plausible numeric values, and
candidate time-series columns.

```powershell
python promo_dump.py path\to\instrument-file.promo
```

The tool uses only the Python standard library and writes a sibling
`*_decoded_attempt` directory.
