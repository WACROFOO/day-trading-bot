# src/

The probe's modules.

| Module | What |
|---|---|
| `forecast.py` | Kronos inference that KEEPS the sample axis, and the barrier reduction. The shipped `predict()` averages sampled OHLC paths in price space, which destroys the only quantity measured here |
| `truth.py` | the realised barrier outcome from the forward tape, graded by the same rule the model's paths are |
| `bars.py` | session-aware slicing of the cached minute bars; drops rather than pads |
| `anchors.py` | both populations — variant-A decision points, and the random-entry arm rebuilt from the parent study's own `SessionState` |
