"""Does the outer collapse survive throwing away everything off the scan?

The pre-registered run says the prediction resolves single sheets at 1.6-2.1x the
random baseline out to winding ~90 on PHerc. Paris 4, and then falls to 0.66x by
winding 120-130 — worse than scattering the same runs at random. Before that is read
as a statement about the prediction, it has to survive the failure that spoiled the
previous artifact: **published segment meshes run past the edge of the scanned volume**
at high z (0.0% of mesh points off-mask at z = 9000, 21.0% at z = 15694, 51.0% at
z = 18000). A rung of the ladder that sits where nothing was scanned is not a sheet the
prediction missed; it is a rung that should never have been there.

This is deliberately **not** part of the protocol. The protocol was declared without a
mask filter and is published as declared; this is a separate question asked afterwards
of the same slices, and it is declared here before it is run:

- a crossing is *on-scan* if the CT reads non-zero there. The volume is published as
  `…-masked.zarr`, so exactly-zero means outside the scan mask; air inside the mask
  reads around 50, so no tunable threshold is involved;
- a gap is on-scan if **both** of its bounding crossings are;
- the comparison is the one-run share over on-scan gaps against the same share over all
  gaps, per winding band, with the count of dropped gaps beside it;
- every band is reported, including the ones where nothing changes.

The ladder is geometry — meshes, centre, rays — so it is rebuilt here from the cached
grids without touching the prediction, and checked against the slices the run wrote:
the rebuilt gap labels must equal the stored ones element for element, or this is
measuring something else and says so.

Usage:
    python offmask_check.py --slices ../../output/protocol \\
        --cache-root ../../output --grid-cache ../../output/figgrids \\
        --out OFFMASK_CHECK.md
"""
import argparse
import glob
import json
import os
import sys

import numpy as np

# `absolute_winding_calibration.py` sits beside this file in the published repository
# and one directory over in the working one. Add the second location only if it exists,
# so the published copies are byte-identical to the ones that produced the numbers.
_STANDALONE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'standalone')
if os.path.isdir(_STANDALONE):
    sys.path.insert(0, _STANDALONE)
import scrolls                                                        # noqa: E402

BAND = 10


def rebuild(scroll, z, cache, grid_cache, segments, centre, direction, rays):
    """The ladder of this slice again, as (gap winding, both-ends-on-scan)."""
    origin = np.array(centre.at(z))
    curves = scrolls.ladder_curves(scroll, centre, direction, grid_cache, z, segments,
                                   verbose=False)
    reach = scrolls.ray_reach(curves, origin)
    mask = scrolls.open_scan_mask(scroll, cache)

    labels, on_scan = [], []
    for step in range(rays):
        angle = 2 * np.pi * step / rays
        unit = np.array([np.cos(angle), np.sin(angle)])
        hits = []
        for points, winding in curves:
            hits += scrolls.ray_crossings(points, winding, origin, unit, reach)
        if len(hits) < max(5, len(curves) // 2):
            continue
        hits.sort()
        radii = np.array([h[0] for h in hits])
        windings = np.array([h[1] for h in hits])
        points = np.stack([origin[0] + radii * unit[0],
                           origin[1] + radii * unit[1],
                           np.full_like(radii, z)], axis=1)
        inside = mask.inside(points)
        labels.append(windings[:-1])
        on_scan.append(inside[:-1] & inside[1:])
    return np.concatenate(labels), np.concatenate(on_scan)


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--slices', required=True)
    parser.add_argument('--cache-root', required=True)
    parser.add_argument('--grid-cache', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()

    by_scroll = {}
    for path in sorted(glob.glob(os.path.join(args.slices, '*.json'))):
        with open(path, encoding='utf-8') as handle:
            result = json.load(handle)
        by_scroll.setdefault(result['scroll'], []).append(result)

    out = ['# Off-mask check on the protocol slices', '',
           'Asked after the run, of the same slices, and not part of the protocol: '
           'what happens to the numbers when every gap with an endpoint outside the '
           'scanned volume is dropped. Criterion declared in `offmask_check.py` before '
           'running.', '']

    for key in sorted(by_scroll):
        scroll = scrolls.SCROLLS[key]
        cache = os.path.join(args.cache_root, scroll.cache_name)
        segments = scrolls.labelled_segments(scroll)
        results = sorted(by_scroll[key], key=lambda r: r['z'])
        centre = scrolls.Centre(scroll, cache, args.grid_cache)
        direction = scrolls.traversal_direction(
            scroll, centre, args.grid_cache, [r['z'] for r in results], segments)

        windings, runs, on_scan = [], [], []
        rows = []
        for result in results:
            labels, keep = rebuild(scroll, result['z'], cache, args.grid_cache,
                                   segments, centre, direction, result['rays'])
            stored = np.array(result['gap_winding'])
            if len(labels) != len(stored) or not np.allclose(labels, stored, atol=1e-6):
                raise RuntimeError(
                    f'{key} z={result["z"]:.0f}: the rebuilt ladder does not match the '
                    f'slice ({len(labels)} gaps against {len(stored)}); this would be '
                    f'measuring a different thing from the run')
            here = np.array(result['gap_runs'], float)
            windings.append(stored)
            runs.append(here)
            on_scan.append(keep)
            rows.append(f'| {key} | {result["z"]:.0f} | {len(stored)} | '
                        f'{1 - keep.mean():.1%} | {np.mean(here == 1):.1%} | '
                        f'**{np.mean(here[keep] == 1) if keep.any() else float("nan"):.1%}** |')
            print(f'{key} z={result["z"]:.0f}: {1 - keep.mean():.1%} of gaps have an '
                  f'endpoint off-scan', flush=True)

        windings = np.concatenate(windings)
        runs = np.concatenate(runs)
        on_scan = np.concatenate(on_scan)
        null = float(np.mean([n for r in results for n in r['null_one_share']]))

        out += [f'## {key}', '',
                '| scroll | z | gaps | dropped | one run, all | one run, on-scan |',
                '|---|---|---|---|---|---|'] + rows + ['']
        out += [f'Pooled: {len(runs)} gaps, {1 - on_scan.mean():.1%} dropped. One run '
                f'in {np.mean(runs == 1):.1%} over all gaps and '
                f'**{np.mean(runs[on_scan] == 1):.1%}** over on-scan gaps, against the '
                f'run\'s random baseline of {null:.1%}.', '',
                '| windings | gaps | off-scan | one run, all | one run, on-scan | '
                'on-scan vs random |', '|---|---|---|---|---|---|']
        low = int(np.floor(windings.min()))
        for start in range(low - low % BAND, int(np.ceil(windings.max())), BAND):
            take = (windings >= start) & (windings < start + BAND)
            if take.sum() < 50:
                continue
            kept = take & on_scan
            clean = (f'**{np.mean(runs[kept] == 1):.1%}**' if kept.sum() >= 50
                     else f'({kept.sum()} gaps)')
            ratio = (f'{np.mean(runs[kept] == 1) / null:.2f}×' if kept.sum() >= 50
                     else '—')
            out.append(f'| {start}–{start + BAND} | {take.sum()} | '
                       f'{1 - on_scan[take].mean():.1%} | '
                       f'{np.mean(runs[take] == 1):.1%} | {clean} | {ratio} |')
        out.append('')

    with open(args.out, 'w', encoding='utf-8', newline='\n') as handle:
        handle.write('\n'.join(out) + '\n')
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(errors='replace')
    print('\n'.join(out))
    print(f'\nwritten to {args.out}')


if __name__ == '__main__':
    main()
