# MODIS / HDF Reader

Reads HDF4, HDF5, or netCDF scientific files, writes dataset statistics, and
exports raw values as tab-separated text.

```powershell
python -m pip install -r requirements.txt
Copy-Item input.example.txt input.txt
# Edit input.txt so its first line is the source file path.
python HDFreader.py
```

Results are written to `output/`. Raw exports can be very large.
