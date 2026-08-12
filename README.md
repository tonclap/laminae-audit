# Absolute winding calibration for PHerc. Paris 4

Winding fields recovered from CT are relative: they get the *differences* between
windings right and leave the origin unknown. Both sides of the current toolchain say
so — winding-sync's README calls absolute counts "not yet calibrated", and its entry
in villa's community-projects page repeats that verbatim; constraint-gauge, the
external benchmark that scores winding-constraint generators, writes the complementary
rule into its submission criteria: *winding may be relative, only differences are
scored*. So the offset is measured by nobody and rewarded by nobody.

This measures it.

```
absolute winding = laminae counted outward from the umbilicus + 6      (+1 / −2)
```

valid over z ≈ 3100–15700 — and, the part that makes it usable, **the method tells you
where it is valid**. The regression slope is computed from the same rays with no
absolute labels involved; where counting is sound it sits near 1, and at the top of
the fitted mesh domain it collapses to 0.465 on its own. Read the constant only off
slices that pass that gate; the tool prints `SLOPE GATE FAILED` when they do not.

## Run it

```bash
pip install -r requirements.txt
python absolute_winding_calibration.py --cache ./chunks --mesh-cache ./meshes
```

No credentials, no GPU, no bulk download, no arguments beyond two scratch directories.
Expect this:

```
segments 28  slope 0.978  intercept -3.5  r 0.983
per-point (448 points): best constant C = +6  inside 0.277  +-1 0.364  +-2 0.435
  C=0 baseline: inside 0.210
  second estimator (slope fixed at 1, median offset): +5.5  against the grid search's +6
  windings  18- 55: n= 80  median offset -5.5  iqr 5.0
  windings  61-102: n=192  median offset -5.0  iqr 8.0
  windings 105-128: n=176  median offset -5.0  iqr 20.0
shuffled-label null: mean 0.064  p95 0.094  max 0.118
```

`--z 18000` shows the gate refusing a slice. `--out results.json` writes the same
figures plus every per-point count.

**Inputs come from two different hosts**, which is not guessable and cost this project
an afternoon: the surface prediction and the segment meshes stream from the S3 bucket
`vesuvius-challenge-open-data`, while the umbilicus is fetched from the data server
`dl.ash2txt.org` as part of the spiral-input dataset. That bucket has no `datasets/`
prefix at all, so the annotation corpus is not there.

## Ground truth: one source, propagated

The truth is the 28 PHerc. Paris 4 segments whose names *are* absolute winding
intervals — `…-w010-027` through `…-w128-129`, covering windings 10 to 129
continuously. The naming is documented rather than inferred: villa's spiral tutorial
shows `meshes/mesh/w010/ # one tifxyz mesh per winding` and describes `render_ink.py`
grouping them into ranges named `w010-027`. Median offset **−5.5**.

`abs_winding.json` — 59 hand-placed absolute winding numbers — gives **−7**.

**These are not two independent measurements, and the direction matters.** The spiral
fit takes absolute winding annotations as an *input*, and no other input it consumes
(patches, fibers, relative annotations, predicted normals, tracks, the umbilicus, the
outer shell) carries an absolute number. So the fit's absolute numbering can only have
come from those 59 labels, and the segment names are those labels propagated across
windings 10–129. There is **one** absolute ground truth; the −7 / −5.5 pair is the raw
labels against the fit's spread of them. What is independent is the counting side: it
uses neither.

## Method

On a z-slice, cast a ray from the umbilicus to a mesh point of a labelled segment and
count runs of the binary surface prediction (`…-recto-2um-ps256-L0-th0.45.zarr`,
pyramid level 2 — the frame the annotations live in). Regress counted against the
segment's own winding interval. Segment geometry comes from
`mesh/intermediate/tifxyz_original/`, which is in the prediction's frame.

The local step is the part known to be accurate: on short rays, threshold crossings
match human clicks to sub-voxel median error (0.28–0.63 vx).

**Counting conventions**, since the whole result is one integer:

- a lamina is a maximal run at or above `--threshold`; a run already in progress at
  the first sample counts (rays start at the umbilicus, which is not inside a lamina,
  so this does not fire here — but it would for a different origin);
- the ray runs from the umbilicus control point, not from the first lamina, and the
  lamina containing the target is counted;
- winding numbers follow the segment names, which are 1-based: `w010` is the tenth
  winding.

## Results

Six slices spanning 15,000 voxels of scroll height. Two are the edges of the fitted
mesh domain, picked adversarially before the run by a stated criterion —
labelled-segment point density, flat at ~12,000 points per slice everywhere and
halving at exactly one place, z = 18000.

| z | slope | r | best C | inside interval | shuffled-label null |
|---|---|---|---|---|---|
| 3100 (lower edge) | 1.010 | 0.978 | +4 | 0.172 | 0.052 |
| 6000 | 1.061 | 0.983 | +6 | 0.205 | 0.061 |
| 9000 | 1.070 | 0.990 | +7 | 0.259 | 0.061 |
| 12000 | 1.014 | 0.995 | +5 | 0.321 | 0.068 |
| 15694 | 0.978 | 0.983 | +6 | 0.277 | 0.064 |
| 18000 (upper edge) | **0.465** | **0.574** | +4 | 0.147 | 0.053 |

On the five that pass, counting tracks truth close to 1:1 across 120 windings, so the
error is an offset rather than accumulating drift. Read `+1/−2` as **the spread of
observations, not a confidence interval**: across the five passing slices C came out
+4, +6, +7, +5, +6. The sixth is excluded by its own gate, so its C is not part of the
range. Four of the six z were round numbers picked by hand; two were picked
adversarially.

On the sixth it fails, and **the failure is visible without ground truth**: slope
0.465, r 0.574, band-wise shortfall running away to −50.5 counts with IQR 82. The
second estimator diverges too (+16.8 against the grid search's +4). This is the top
row of the `z3000_18000` fit domain, where the segment meshes themselves thin to half
density.

## Null control

Every hit rate is reported against the same statistic with the labels destroyed — each
segment's winding interval reassigned to another segment, 200 permutations, all
marginals preserved, and the best constant re-selected *inside* each permutation so
the grid search is charged for. The null lands at **0.064** (p95 0.094, max 0.118)
against a measured 0.277. Leaving the offset out entirely scores 0.210.

This control exists because an earlier version of this work produced a beautiful peak
at exactly the expected value that turned out to be nothing: fitting a scale factor
for the cheap `…-45.532um.tifxyz` mesh peaked at the nominal 4.75, at 0.244 on-mask
against a random-cloud baseline of 0.241. That mesh is defined on scan
20260310170716, a different scan from the prediction's 20260411134726. Worth naming
publicly — it looks like the obvious mesh to use.

## What this is not

- **Not per-point winding identification.** Dispersion grows outward: the per-point
  offset IQR runs 5 → 8 → 20 counts across windings 10–60, 60–105 and 105–129. And
  "gets it right" is weaker than it sounds — a point is scored against its segment's
  *interval*, 2 windings wide for `w116-117` but 18 wide for `w010-027`. On that
  generous test a point lands inside 20–32% of the time. The per-point absolute number
  is not recovered at all; the offset of the field is.
- **Not two independent ground truths.** See above: one source and its propagation.
- **Not free of shared ancestry.** The fit also consumes machine-derived inputs —
  lasagna normals, skeletonised surface-prediction tracks — so the geometry the
  segments sit on is not wholly independent of the prediction this counts laminae in.
  The absolute origin is unaffected, but per-point agreement is flattered to an
  unknown degree. The shuffled-label null does not address this: it breaks the
  segment-to-interval association, not common ancestry.
- **Not a pre-registered gate.** The slope bounds 0.8–1.2 were set after seeing that
  good slices sit near 1.0 and the broken one at 0.465.
- **Not a relative-winding method.** Global wrap identity from this prediction was
  attempted three ways and all three failed; connected components are refuted rather
  than merely unsuccessful, since the median geodesic detour within a component is 41×
  the direct distance — the papyrus is one physically continuous spiral. Relative
  winding is winding-sync's job, and constraint-gauge measures it.
- **One scroll.** PHerc. Paris 4 is the only scroll with published absolute labels, so
  C is a Paris 4 number. The method should transfer; the constant is not claimed to.

## Licence and disclosure

MIT, see `LICENSE`. AI assistance is disclosed in `AI_DISCLOSURE.md` as villa's
submission policy requires.
