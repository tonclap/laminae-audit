"""How many runs of surface prediction lie between two consecutive labelled sheets?

This is the mechanism question, and by now it is the only one left standing.

Counting laminae outward from the umbilicus outruns the fit's winding numbering by
10-20% in the outer half of the scroll. Three explanations were possible; two are
already dead:

- the reference is wrong — no: every segment mesh spans exactly `high - low + 1` turns
  of accumulated angle (28 segments, three heights, within 0.2%);
- the ray is wrong, meeting some sheets twice because the scroll is not round — no:
  intersecting the ray with the published meshes gives 120 crossings for the 120
  windings it spans, with a median excess of -0.4% and at most one non-monotone
  crossing per ray (`ray_vs_mesh.py`).

What is left is the surface prediction itself: along a ray, between two consecutive
labelled sheets there should be exactly one run of mask. This measures how often that
is true, and where it stops being true.

The two are read on the same ray, at the same height, so nothing is being compared
across frames: mesh crossings give the winding ladder, `count_runs`' rising edges give
the prediction's, and the question is simply how many of the latter fall between
neighbouring rungs of the former.

The scroll is a parameter (`--scroll`, see `scrolls.py`). Nothing in the question above
is about PHerc. Paris 4, and a measurement that only ever ran on the scroll it was
invented on is a measurement no one has reason to trust.

Usage:
    python runs_per_winding.py --scroll PHerc0139 --cache ../../output/cache0139 \\
        --grid-cache ../../output/figgrids --z 5000 --rays 24

For the pre-registered run over five heights and both scrolls, drive `measure()` from
`protocol_run.py` rather than calling this by hand five times.
"""
import argparse
import os
import sys

import numpy as np

# `absolute_winding_calibration.py` sits beside this file in the published repository
# and one directory over in the working one. Add the second location only if it exists,
# so the published copies are byte-identical to the ones that produced the numbers.
_STANDALONE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'standalone')
if os.path.isdir(_STANDALONE):
    sys.path.insert(0, _STANDALONE)
import ray_vs_mesh                                                    # noqa: E402
import scrolls                                                        # noqa: E402


def prediction_profile(pred, origin, unit, max_radius, threshold, step):
    """Rising-edge radii and the above-threshold profile along the ray.

    Both are wanted, because "no run between two labelled sheets" has two very
    different causes: the prediction may have missed a sheet entirely, or it may have
    merged it with its neighbour into one long run. The rising edges alone cannot tell
    those apart; asking whether the mask is on *at* a labelled sheet can.
    """
    ts = np.arange(0.0, max_radius + step, step)
    direction = np.array([unit[0], unit[1], 0.0])
    above = (pred.sample(origin[None, :] + ts[:, None] * direction[None, :])
             >= threshold).astype(np.int8)
    return ts[np.flatnonzero(np.diff(above, prepend=np.int8(0)) == 1)], ts, above


def detected(ts, above, radii, tolerances):
    """Is the mask on within each tolerance of each labelled sheet crossing?"""
    out = [dict() for _ in radii]
    for index, radius in enumerate(radii):
        for tolerance in tolerances:
            window = (ts >= radius - tolerance) & (ts <= radius + tolerance)
            out[index][tolerance] = bool(above[window].any())
    return out


def measure(scroll, z, cache, grid_cache, rays=24, threshold=None, step=0.5,
            null_draws=200, tolerance=(1.0, 2.0, 3.0, 5.0, 8.0, 11.0), segments=None,
            direction=None, verbose=True):
    """One slice of the measurement, as plain data.

    Separated from the printing so the pre-registered protocol run can drive it over
    five heights and two scrolls (`protocol_run.py`) and keep every slice on disk. The
    return value is JSON-serialisable on purpose: a run that dies halfway through the
    network should cost the slice it was on, not the ones already paid for.

    `direction` is passed in by a whole run, which settles it once over every height —
    it is a property of the scroll, and settling it slice by slice makes a run hostage
    to its worst slice. Left out, it is settled here from this height alone.
    """
    segments = segments or scrolls.labelled_segments(scroll)
    threshold = scroll.threshold if threshold is None else threshold
    tolerance = list(tolerance)

    centre = scrolls.Centre(scroll, cache, grid_cache)
    if verbose:
        print(centre.describe(z), flush=True)
    if direction is None:
        direction = scrolls.traversal_direction(scroll, centre, grid_cache, z, segments)
    ux, uy = centre.at(z)
    origin2 = np.array([ux, uy])
    origin3 = np.array([ux, uy, z])
    pred = scrolls.open_prediction(scroll, cache)

    curves = scrolls.ladder_curves(scroll, centre, direction, grid_cache, z, segments,
                                   verbose=verbose)
    reach = scrolls.ray_reach(curves, origin2)
    # Bands to report by, 20 windings wide, counted from the innermost labelled winding
    # of whichever scroll this is — 10 on Paris 4, 23 on PHerc0139. Anchoring on the
    # data rather than on multiples of 20 keeps the Paris 4 bands the ones the earlier
    # write-up used (10-30, 30-50, …), so its numbers stay comparable.
    lo_w = int(np.floor(min(float(np.min(w)) for _, w in curves)))
    hi_w = int(np.ceil(max(float(np.max(w)) for _, w in curves)))
    bands = [(lo, min(lo + 20, hi_w)) for lo in range(lo_w, hi_w, 20)]

    # The rays are laid out first, with no network involved, so the whole slice's chunk
    # demand is known before a single byte is fetched — and can be fetched as one pool
    # instead of 24 ray-sized ones. The link saturates at four parallel requests, so
    # this buys nothing in bandwidth; what it removes is the tail of each ray's batch,
    # where a handful of stragglers hold up a pool of eight. On a Paris 4 slice that is
    # 24 tails out of ~230 chunks.
    layout = []
    for step_index in range(rays):
        angle = 2 * np.pi * step_index / rays
        unit = np.array([np.cos(angle), np.sin(angle)])
        hits = []
        for polyline, winding in curves:
            hits += ray_vs_mesh.ray_crossings(polyline, winding, origin2, unit, reach)
        if len(hits) < max(5, len(curves) // 2):
            continue
        hits.sort()
        layout.append((step_index, angle, unit,
                       np.array([h[0] for h in hits]),
                       np.array([h[1] for h in hits])))
    if layout:
        wanted = set()
        for _, _, unit, radii, _ in layout:
            ts = np.arange(0.0, float(radii[-1]) + step, step)
            points = origin3[None, :] + ts[:, None] * np.array([unit[0], unit[1], 0.0])
            index = np.rint(points[:, ::-1]).astype(np.int64)
            block = np.unique(index // np.array(pred.chunks, np.int64), axis=0)
            for cz, cy, cx in block:
                if all(0 <= v < s for v, s in zip((cz, cy, cx),
                                                  [-(-pred.shape[a] // pred.chunks[a])
                                                   for a in range(3)])):
                    wanted.add(f'{cz}/{cy}/{cx}')
        if verbose:
            print(f'  prefetching {len(wanted)} prediction chunks for the slice',
                  flush=True)
        pred.prefetch(sorted(wanted))

    gaps = []                        # (winding at the inner rung, runs inside the gap)
    sheets = []                      # (winding of a labelled sheet, mask on within tol)
    splits = []                      # (edge separation, gap width, winding)
    null_gaps = [[] for _ in range(null_draws)]
    fake_sheets = []                 # the same detection question at random radii
    rays_used = 0
    for step_index, angle, unit, radii, windings in layout:
        rays_used += 1
        edges, ts, above = prediction_profile(pred, origin3, unit, float(radii[-1]),
                                              threshold, step)
        sheets += list(zip(windings, detected(ts, above, radii, tolerance)))
        # Detection needs its own baseline, and an obvious one: the mask occupies a
        # sizeable share of the ray, so a window of +-11 voxels around *any* radius has
        # a fair chance of touching it by luck. Same question, asked at random radii.
        fake_radii = np.sort(np.random.default_rng(1000 + step_index).uniform(
            radii[0], radii[-1], len(radii)))
        fake_sheets += detected(ts, above, fake_radii, tolerance)
        # One gap per pair of neighbouring labelled sheets; count the rising edges
        # falling strictly inside it.
        # Same statistic with the run positions destroyed and everything else kept:
        # same count of runs, same stretch of ray, same gap boundaries.
        rng = np.random.default_rng(step_index)
        for draw in range(null_draws):
            fake = np.sort(rng.uniform(radii[0], radii[-1], len(edges)))
            counts = np.bincount(np.searchsorted(radii, fake) - 1,
                                 minlength=len(radii) - 1)[:len(radii) - 1]
            null_gaps[draw].append(counts)

        inside = np.searchsorted(radii, edges)
        for index in range(len(radii) - 1):
            here = edges[inside == index + 1]
            gaps.append((windings[index], len(here)))
            # When a gap holds exactly two runs, how far apart are they? Two edges a
            # few voxels apart are one sheet the threshold broke in half; two edges
            # near the sheet spacing are two distinct pieces of material. The gap's own
            # width is carried along so the separation can be read as a fraction of it.
            if len(here) == 2:
                splits.append((float(here[1] - here[0]),
                               float(radii[index + 1] - radii[index]),
                               float(windings[index])))
        if verbose:
            print(f'  ray {np.degrees(angle):5.0f}°: {len(radii)} labelled sheets, '
                  f'{len(edges)} prediction runs to r={radii[-1]:.0f}', flush=True)

    nulls = [np.concatenate(draw) for draw in null_gaps if draw]
    return {
        'scroll': scroll.key, 'z': float(z), 'rays': rays, 'rays_used': rays_used,
        'threshold': threshold, 'step': step, 'null_draws': null_draws,
        'tolerance': tolerance, 'centre': [float(ux), float(uy)],
        'direction': float(direction), 'segments': len(segments),
        'curves': len(curves), 'reach': float(reach), 'bands': [list(b) for b in bands],
        'gap_winding': [float(g[0]) for g in gaps],
        'gap_runs': [int(g[1]) for g in gaps],
        'null_one_share': [float(np.mean(draw == 1)) for draw in nulls],
        'sheet_winding': [float(s[0]) for s in sheets],
        'sheet_hits': {str(t): [bool(s[1][t]) for s in sheets] for t in tolerance},
        'fake_hits': {str(t): [bool(f[t]) for f in fake_sheets] for t in tolerance},
        'splits': splits,
    }


def report(result):
    """Print one slice's measurement, in the shape the earlier runs printed it."""
    bands = [tuple(b) for b in result['bands']]
    tolerance = result['tolerance']
    windings = np.array(result['gap_winding'])
    runs = np.array(result['gap_runs'], float)
    print(f"\n{len(runs)} winding gaps over {result['rays']} rays at "
          f"z = {result['z']:.0f}")
    print(f'prediction runs per gap: mean {runs.mean():.3f}  '
          f'median {np.median(runs):.1f}')
    # The mean is nearly a tautology — the same runs spread over the same ray, cut into
    # the same number of gaps — so it is the *share landing one-per-gap* that carries
    # the signal, and that needs a baseline. The baseline re-places the very same number
    # of runs uniformly at random along the same stretch of ray and asks the same
    # question. A prediction indifferent to where the sheets are would match it.
    null = np.array(result['null_one_share'])
    for value in range(4):
        share = np.mean(runs == value) if value < 3 else np.mean(runs >= 3)
        label = f'{value}' if value < 3 else '3+'
        extra = (f'   against {null.mean():6.1%} for the same runs placed at random '
                 f'(p95 {np.percentile(null, 95):.1%})' if value == 1 else '')
        print(f'  {label:>2s} run(s) in the gap: {share:6.1%}{extra}')

    print(f'\n{"windings":>10s}  {"gaps":>5s}  {"mean runs":>9s}  {"0":>6s}  '
          f'{"1":>6s}  {"2+":>6s}')
    for lo, hi in bands:
        take = (windings >= lo) & (windings < hi)
        if take.sum() < 10:
            continue
        band = runs[take]
        print(f'  {lo:4d}-{hi:4d}  {take.sum():5d}  {band.mean():9.3f}  '
              f'{np.mean(band == 0):6.1%}  {np.mean(band == 1):6.1%}  '
              f'{np.mean(band >= 2):6.1%}')
    print('\nA prediction that resolved exactly the labelled sheets would sit at '
          '1.000 everywhere.')

    sheet_winding = np.array(result['sheet_winding'])
    hits = {t: np.array(result['sheet_hits'][str(t)], float) for t in tolerance}
    chance = {t: float(np.mean(result['fake_hits'][str(t)])) for t in tolerance}
    # The tolerance is not a free parameter to be picked after seeing the answer, so
    # the whole curve is printed. It separates the two readings of a missing run: if
    # detection climbs to ~100% by half the sheet spacing (~11 vx), every labelled
    # sheet has mask near it and the trouble is placement or merging; if it plateaus
    # well below, sheets are genuinely absent from the prediction.
    print(f'\nmask on within +-tolerance of a labelled sheet '
          f'({len(sheet_winding)} crossings); neighbouring sheets are ~22 vx apart:')
    header = '  '.join(f'+-{t:<4.0f}' for t in tolerance)
    print(f'{"windings":>10s}  {"sheets":>6s}  {header}')
    row = '  '.join(f'{hits[t].mean():6.1%}' for t in tolerance)
    print(f'{"all":>10s}  {len(sheet_winding):6d}  {row}')
    row = '  '.join(f'{chance[t]:6.1%}' for t in tolerance)
    print(f'{"at random":>10s}  {len(sheet_winding):6d}  {row}')
    for lo, hi in bands:
        take = (sheet_winding >= lo) & (sheet_winding < hi)
        if take.sum() >= 10:
            row = '  '.join(f'{hits[t][take].mean():6.1%}' for t in tolerance)
            print(f'  {lo:4d}-{hi:4d}  {take.sum():6d}  {row}')
    print('\nA gap with no rising edge but a sheet detected on both sides is a merge; '
          'a gap with no edge and no detection is a miss.')

    if result['splits']:
        separation = np.array([s[0] for s in result['splits']])
        width = np.array([s[1] for s in result['splits']])
        print(f'\ngaps holding exactly two runs ({len(separation)}): separation '
              f'between the two rising edges')
        print(f'  median {np.median(separation):.1f} vx  '
              f'p10 {np.percentile(separation, 10):.1f}  '
              f'p90 {np.percentile(separation, 90):.1f}  '
              f'against a median gap width of {np.median(width):.1f} vx')
        for lo, hi in ((0, 4), (4, 8), (8, 14), (14, 10_000)):
            take = (separation >= lo) & (separation < hi)
            label = f'{lo}-{hi} vx' if hi < 10_000 else f'>{lo} vx'
            print(f'  {label:>9s}: {np.mean(take):6.1%}')
        print('  A separation of a few voxels is one sheet the threshold broke in two;\n'
              '  a separation near the sheet spacing is genuinely extra material.')


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    scrolls.add_argument(parser)
    parser.add_argument('--cache', required=True)
    parser.add_argument('--grid-cache', required=True)
    parser.add_argument('--z', type=float, default=None,
                        help='height; default is the middle protocol height')
    parser.add_argument('--rays', type=int, default=24)
    parser.add_argument('--threshold', type=int, default=None,
                        help="mask cut; defaults to the scroll's")
    parser.add_argument('--step', type=float, default=0.5)
    parser.add_argument('--null-draws', type=int, default=200)
    parser.add_argument('--tolerance', type=float, nargs='+',
                        default=[1.0, 2.0, 3.0, 5.0, 8.0, 11.0],
                        help='voxels either side of a labelled sheet that still count '
                             'as the same sheet; sheet spacing here is ~22 vx')
    args = parser.parse_args()

    scroll = scrolls.SCROLLS[args.scroll]
    segments = scrolls.labelled_segments(scroll)
    if args.z is None:
        heights = scrolls.protocol_heights(scroll, args.grid_cache, segments=segments)
        args.z = heights[len(heights) // 2]
    report(measure(scroll, args.z, args.cache, args.grid_cache, rays=args.rays,
                   threshold=args.threshold, step=args.step,
                   null_draws=args.null_draws, tolerance=args.tolerance,
                   segments=segments))


if __name__ == '__main__':
    main()
