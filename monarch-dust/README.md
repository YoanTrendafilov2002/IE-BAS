# MONARCH Dust

`BarcelonaData.py` downloads AEMET MONARCH dust forecasts through OPeNDAP and
interpolates model fields to a configured point. `BarcelonaGrapher.cpp` renders
the resulting dust series with gnuplot.

```powershell
python -m pip install -r requirements.txt
Copy-Item user_config.example.json user_config.json
# Add your BDSR credentials to user_config.json.
python BarcelonaData.py
```

The private `user_config.json` is ignored by Git. The C++ grapher requires a
C++17 compiler and `gnuplot` in `PATH`.
