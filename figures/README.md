# Figures

Drawn by `make_figures.py`, which imports `absolute_winding_calibration.py` as a
library rather than reimplementing it: the number of ticks each figure draws is
asserted against `count_to_point`, so a figure cannot quietly disagree with the
tool.

| file | what it shows |
|---|---|
| `fig1_slice.png` | the slice the ray is taken from, with published segment mesh points overlaid — including the fan of points sitting past the edge of the scroll that `CORRECTION.md` item 1 is about |
| `fig2_ray.png` | the whole ray at z = 15694, with the winding interval of every published segment it crosses drawn as a bar |
| `fig3_zoom.png` | 300 voxels of that ray at 1:1 — raw CT on top, the `th0.45` recto prediction underneath, one tick per lamina entered and the number it implies; open circles are the hand-placed points of villa's `abs_winding.json` |
| `fig5_labels.png` | counted vs annotated winding for the 59 points of `abs_winding.json`, against the same statistic with the labels shuffled |
| `fig6_gate_slice.png` | z = 18000, where about half of the published mesh points fall outside the scan mask (`check_mesh_outside.py`) |

`fig3_zoom.png` is the one to look at first.
