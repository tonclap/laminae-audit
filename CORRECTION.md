# Correction record

This repository was published on 12 August 2026 as **absolute-winding**, claiming a
calibration that turns a relative winding field into an absolute one. Measurement over
the following two days withdrew most of that claim. The repository was renamed to
**laminae-audit** on 14 August and rewritten around what survived — the measurement
underneath it — rather than deleted: the commit history, including the original
README and its numbers, stays public. Nothing below has been quietly edited out of the
old text; it was corrected in place, dated, and is now collected here.

There is one thing to note before the list. Every correction below was found by the
same discipline, and it is the only method claim this repository makes: **print a
baseline next to every number.** Four of the five withdrawals are cases where a figure
looked convincing until the same question was asked of randomised data and gave nearly
the same answer.

## 1. The applicability gate is withdrawn

The original headline feature was that the method refuses slices where counting is
unsound: the regression slope collapsed to 0.465 at z = 18000 and the tool printed
`SLOPE GATE FAILED`.

That collapse was an artefact of the sampler. It scored mesh points lying **outside the
scan mask** — 51% of them at z = 18000, 21% at z = 15694, 0% below z = 9000. With those
points excluded the slope at z = 18000 is 1.134 and the slice passes. Across eight
slices the gate then fires nowhere, so there is no demonstrated case of it working.

The tool was fixed (`ScanMask` in `absolute_winding_calibration.py`;
`--no-mask-filter` reproduces the old runs exactly). The *claim* is withdrawn.

## 2. "The error is an offset, not a drift" is withdrawn

Against exact per-point winding — recovered from the meshes themselves rather than from
interval midpoints, see `mesh_winding.py` — the regression slope is 1.00 ± 0.05 only
over windings 10–70. Beyond winding 70 it runs to 1.1–1.5 and the offset falls away. A
single additive constant describes the inner half of the scroll, not the whole of it.

## 3. The constant survives, narrowed to a range and a domain

`+7` over windings 10–70, where two independent references agree: the segment meshes
(+7.32) and the 59 hand-placed labels of `abs_winding.json` (+7.0). Per-point spread is
3–10 windings, so a single ray does not determine a winding — the constant is a
population statement, not a measurement you can make once.

## 4. Why it worked at all — and this is what the repository is about now

Between two consecutive labelled sheets, a ray should cross exactly one run of
predicted surface. Measured over both published scrolls, five heights each, 24 rays
each: exactly one run in **51–52%** of gaps, against 27–32% for the same number of runs
scattered at random along the same ray. A third of gaps hold none and an eighth hold
two or more.

Undercount and overcount are close to equal and opposite, so the total lands near the
winding number by cancellation rather than by measurement. That is the whole mechanism
of the original claim, and it is why the constant is real but weak. The measurement
that shows it is now the subject of this repository: see `README.md`.

## 5. Three published rows came from a different script

Three rows of the original results table (z = 6000, 9000, 12000) were produced by an
earlier script sampling 8 points per segment rather than 16, and the shipped tool does
not reproduce them. Running that earlier script reproduces them exactly, which is the
proof of provenance. The other five rows reproduce.

The rule this repository now follows without exception: **every published number comes
out of the code shipped beside it.** `protocol_run.py` writes the slices,
`protocol_summary.py` reads them into the tables, and no number is typed by hand.

## 6. The naming convention was wrong

`w010-027` covers windings 10 through 27 inclusive — eighteen of them — and the mesh
spans exactly 18.0 turns of accumulated angle (28 segments, three heights, within
0.2%). The truth used in the original calibration, `(low+high)/2`, therefore sits half
a winding low. This moves the constant by a whole number and leaves every slope
untouched.

## 7. Added 14 August: the scan edge, measured against winding

The off-mask contamination of item 1 was first measured against height. Measured
against *winding* it is sharper, and it matters for reading the results in `README.md`:
on PHerc. Paris 4 the share of ladder gaps with an endpoint outside the scanned volume
is 0.0% out to winding 80, then 1.7%, 7.6%, 14.3%, 17.3%, and **23.9% on windings
120–130**. On PHerc0139 it is 0.3% overall.

This is a property of the published segment meshes — they run past the edge of the
scanned volume in the outer windings — not of the prediction. `offmask_check.py`
measures it and `OFFMASK_CHECK.md` reports it band by band.
