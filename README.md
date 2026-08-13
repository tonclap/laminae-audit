# laminae-audit — how well does a surface prediction resolve single laminae?

> This repository was published on 12 August 2026 as **absolute-winding**, and most of
> what it claimed then has since been withdrawn by measurement. The record is in
> [CORRECTION.md](CORRECTION.md), and the history is intact rather than rewritten. What
> follows is what survived: not the calibration, but the measurement that showed the
> calibration was weak.

A surface prediction is a mask over the scan volume. Everything downstream — tracing,
`fit_spiral.py`, the winding fields — assumes it separates neighbouring sheets of
papyrus, and that assumption is usually reported as a segmentation score against
annotated surfaces. That score answers "is the predicted surface in the right place".
It does not answer the question the spiral machinery actually depends on:

**between two annotated sheets, does the prediction show exactly one sheet?**

This measures that, on both scrolls that publish absolute winding labels, with a
baseline beside every number.

```
resolving power = share of gaps between neighbouring labelled sheets
                  that contain exactly one run of predicted surface
```

## The result

| scroll | prediction | gaps | one run | same runs at random | ratio |
|---|---|---|---|---|---|
| PHerc0139 | `m7-L0-th0.2` | 3 734 | **51.1%** | 26.8% | **1.90×** |
| PHerc. Paris 4 | `recto-2um-ps256-L0-th0.45` | 14 310 | **52.3%** | 32.2% | **1.63×** |

A prediction that resolved exactly the annotated sheets would put 100% in the "one run"
column. A prediction indifferent to where the sheets are would match the random column,
which takes the same number of runs found on that ray and scatters them along the same
stretch of it.

So: **about half the gaps are resolved correctly, at 1.6–1.9× chance.** Of the rest, a
gap holds no run at all in 26.7% of cases on Paris 4 and 32.8% on PHerc0139 — a merge
or a miss — and two or more in 20.9% and 16.1%.

The two scrolls agree while sharing almost nothing: different model, different
threshold, different scan, different voxel grid, and on PHerc0139 there is no published
umbilicus, so the centre of counting is fitted to the innermost annotated turn instead.

### It depends strongly on how far out you are

Rows below are copied from the generated tables, not recomputed by hand — see
[OFFMASK_CHECK.md](OFFMASK_CHECK.md) for the same numbers with the dropped-gap counts.

| windings | Paris 4, all gaps | on-scan only | vs random |
|---|---|---|---|
| 10–20 | 57.7% | 57.7% | 1.79× |
| 20–30 | 67.3% | 67.3% | 2.09× |
| 30–40 | 67.1% | 67.1% | 2.08× |
| 40–50 | 61.2% | 61.2% | 1.90× |
| 50–60 | 59.2% | 59.2% | 1.84× |
| 60–70 | 57.8% | 57.8% | 1.80× |
| 70–80 | 52.9% | 52.9% | 1.64× |
| 80–90 | 54.4% | 54.8% | 1.70× |
| 90–100 | 49.3% | 51.7% | 1.61× |
| 100–110 | 40.7% | 46.2% | 1.44× |
| 110–120 | 36.9% | 44.2% | 1.37× |
| 120–130 | 21.1% | 26.4% | **0.82×** |

Resolving power roughly halves between the inner and outer half of the scroll, and in
the outermost band it drops **below chance** — the prediction there does not merely
miss sheets, it places runs where the annotated sheets are not.

The "on-scan only" column exists because part of that decline is not the prediction's
fault: the published segment meshes run past the edge of the scanned volume in the
outer windings (0.0% of gaps out to winding 80, 23.9% on 120–130), and a rung of the
ladder in unscanned volume is not a sheet anyone could have predicted. Dropping every
gap that touches unscanned volume recovers about a third of the outer decline and
leaves the rest standing. Full tables: [OFFMASK_CHECK.md](OFFMASK_CHECK.md).

PHerc0139's annotations cover windings 23–59 only, which is inside Paris 4's healthy
region, and there it behaves the same (1.64–2.11×). **The outer collapse is therefore a
Paris 4 statement**; the second scroll has no labels out there to test it with.

## The protocol, fixed before the run

The failure mode this design is built against is picking the slice that makes the point.
The protocol was written down and committed before any of it ran, and
[`protocol_run.py`](protocol_run.py) *is* that protocol:

1. **heights** — five equidistant quantiles of the z-range the labelled meshes actually
   cover, read off the data, endpoints excluded. Not chosen, not adjustable;
2. **rays** — 24 at equal angles, a fixed set;
3. **every** height and **both** scrolls are published, whatever comes out. A slice that
   fails to run appears in the table as a failed row rather than disappearing;
4. **a baseline beside every number**, from the same run;
5. **every published number comes out of the shipped code.** `protocol_run.py` writes
   one JSON per slice; `protocol_summary.py` reads those into the tables. Nothing is
   typed by hand — which is exactly what went wrong in the first version of this
   repository (see [CORRECTION.md](CORRECTION.md), item 5).

Slice-by-slice results: [PROTOCOL_RESULTS.md](PROTOCOL_RESULTS.md).

## How it works

At one height, for one ray from the centre outward:

- **the ladder.** Each published segment mesh is a curve at that height; intersecting
  the ray with it gives a crossing, and each crossing carries its winding number,
  interpolated along the mesh. Neighbouring crossings bound one gap.
- **the prediction.** Sample the mask along the same ray at 0.5 voxel steps and count
  rising edges. Each maximal run of mask is one predicted lamina.
- **the question.** How many rising edges fall strictly inside each gap.
- **the baseline.** Take the same number of runs, scatter them uniformly along the same
  stretch of ray, ask the same question, repeat 200 times.

Two prior questions had to be settled first, and both are checks the code runs every
time rather than assumptions:

- **is the reference sound?** Each mesh must span exactly the turns its name claims.
  Paris 4's do, to within 0.2%. PHerc0139's single-winding meshes overrun a full turn
  by a median 4–8% — neighbouring annotations deliberately overlap — so the gate is
  one-sided: a mesh must cover at least 0.95 of its named turns and may cover more.
  Two PHerc0139 meshes (w035, w050) cover 0.76 and 0.44 and are excluded by name in
  every run.
- **can a ray count windings at all?** If the scroll is out of round, a ray could cross
  the same sheet twice and no counter would return the winding number. Tested without
  the prediction, by intersecting rays with the meshes alone: on Paris 4, 120 crossings
  for the 120 windings spanned, median excess −0.4%. On PHerc0139 the overlap above
  shows up here as a median excess of −5.1% and about two non-monotone crossings per
  ray. [`ray_vs_mesh.py`](ray_vs_mesh.py).

## Run it

```bash
pip install -r requirements.txt

# the whole pre-registered run: 10 slices, resumable, ~1.6 GB over the network
python protocol_run.py --cache-root ./cache --grid-cache ./cache/grids

# tables out of the slices it wrote
python protocol_summary.py --slices ./cache/protocol --out PROTOCOL_RESULTS.md
python offmask_check.py --slices ./cache/protocol --cache-root ./cache \
    --grid-cache ./cache/grids --out OFFMASK_CHECK.md

# one slice on its own, with the full per-ray printout
python runs_per_winding.py --scroll PHerc0139 --cache ./cache/cache0139 \
    --grid-cache ./cache/grids --z 5026 --rays 24

# what a scroll's layout looks like, and the checks that license the reference
python scrolls.py --scroll PHerc0139 --cache ./cache/cache0139 --grid-cache ./cache/grids
python mesh_winding.py --scroll PHerc0139 --cache ./cache/cache0139 --grid-cache ./cache/grids
```

CPU and network only, no credentials, public data throughout. Each slice is cached as
JSON and reused, so an interrupted run costs the slice it was on and nothing else — one
of the ten slices died on a dropped connection during the published run and was
recovered by re-running the same command.

Adding a third scroll is a `Scroll(...)` entry in [`scrolls.py`](scrolls.py): the
prediction and CT paths, the pyramid level whose voxel grid the meshes are written in,
the segment naming pattern, and where the centre of counting comes from. Every field is
a fact that can be checked against the data server, and getting one wrong produces an
error rather than a plausible number — the level in particular, which on Paris 4 is 2
and on PHerc0139 is 0.

## What this is not

- **Not a segmentation score.** It says nothing about whether the predicted surface is
  in the right place; it asks only whether neighbouring annotated sheets are separated.
  A prediction can score well here and be misplaced, or score badly here and be
  perfectly placed but merged.
- **Not a claim about ink or about downstream quality.** Whether 1.63× is good enough
  for `fit_spiral.py` is a question for the people who run it; this supplies the number,
  not the verdict.
- **Not a calibration.** The absolute-winding constant that this repository originally
  claimed is withdrawn to a narrow range and domain — see
  [CORRECTION.md](CORRECTION.md).
- **Not a large sample of scrolls.** Two, because two are all that publish absolute
  winding labels. PHercMANBp has winding-named segments but no confirmed mesh in the
  prediction's frame; PHerc0172 and PHerc1667 have the names but no prediction zarr.

## What was tried and did not survive

Kept because a negative result measured properly is worth more than a positive one
asserted:

- **"the method knows where it is invalid"** (a slope gate) — no instance of it firing
  survived the mask fix;
- **"the error is an offset, not a drift"** — true only over windings 10–70;
- **"the radial ray is the problem"** — refuted by geometry with no prediction in it;
- **"the prediction shows a sheet within a few voxels of 86–95% of annotated sheets"** —
  killed by its own baseline: a random radius on the same ray scores 84–92%. That test
  has almost no resolving power, and it is reported here only next to its baseline
  (88.4% against 85.2% on Paris 4; 90.9% against 85.0% on PHerc0139).

## Licence and disclosure

MIT, see [LICENSE](LICENSE). Written with AI assistance under human direction and
review; see [AI_DISCLOSURE.md](AI_DISCLOSURE.md).
