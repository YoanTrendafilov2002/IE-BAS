# EarthCARE Tracking

Finds the next interval when the EarthCARE satellite ground track passes within
the configured distance of Sofia.

```powershell
python -m pip install -r requirements.txt
python SatTrack.py
```

The script downloads the current TLE from CelesTrak, so an internet connection
is required.
