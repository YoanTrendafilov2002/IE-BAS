# Lufft and Vaisala Parsers

Windows-oriented C/C++ utilities that convert station logs to JSON/JSONL.

```powershell
cmake -S . -B build
cmake --build build --config Release
```

`VaisalaParser.cpp` uses the Win32 file picker and is built only on Windows.
`sample_luft.txt` and `2024-02-02.json` provide small input/output fixtures.
