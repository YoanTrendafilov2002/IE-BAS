# StringMeteo Scraper

Downloads daily station observations from StringMeteo into JSON.

```powershell
python -m pip install -r requirements.txt
python scrape_stringmeteo.py
```

Edit the date range and station constants near the top of the script. Output is
written to `output/`. Set `STRINGMETEO_OUTPUT` to use another directory.
Selenium Manager locates Edge automatically; set `EDGE_DRIVER_PATH` only when a
specific `msedgedriver.exe` is required.
