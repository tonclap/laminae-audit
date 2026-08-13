"""The pre-registered run: five heights, two scrolls, every one published.

The protocol was written down before any of it ran, and this file is that protocol as
code so it cannot quietly drift:

1. **heights** — five equidistant quantiles of the z-extent the labelled meshes
   actually cover, read off the data, endpoints excluded. Not chosen, not adjustable,
   and not re-chosen after seeing a slice;
2. **rays** — 24 at equal angles, a fixed set;
3. **every** height and **both** scrolls are published, whatever comes out. A slice
   that fails to run at all is printed as a failure in the table rather than dropped;
4. **a baseline beside every number**: the same count of runs placed at random along
   the same stretch of ray, and the same detection question asked at random radii;
5. every number comes out of the shipped code path — `runs_per_winding.measure` — which
   is precisely what the previous write-up got wrong when three published rows turned
   out to come from a different script.

Slices are cached as JSON, one file each, and a re-run reuses them. That is not just
convenience: a cold PHerc0139 slice pulls hundreds of prediction chunks over the
network, and an interrupted run must cost the slice it was on rather than the ones
already paid for. Delete a slice's JSON to re-measure it.

Usage:
    python protocol_run.py --cache-root ../../output --grid-cache ../../output/figgrids
"""
import argparse
import json
import os
import sys
import traceback

import numpy as np

# `absolute_winding_calibration.py` sits beside this file in the published repository
# and one directory over in the working one. Add the second location only if it exists,
# so the published copies are byte-identical to the ones that produced the numbers.
_STANDALONE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'standalone')
if os.path.isdir(_STANDALONE):
    sys.path.insert(0, _STANDALONE)
import runs_per_winding                                               # noqa: E402
import scrolls                                                        # noqa: E402

RAYS = 24
HEIGHTS = 5


def slice_path(out_dir, scroll, z):
    return os.path.join(out_dir, f'{scroll.key}_z{round(z):05d}.json')


def run_slice(scroll, z, cache, grid_cache, out_dir, segments, rays, direction):
    """One slice, from cache if it is there, else measured and then cached."""
    path = slice_path(out_dir, scroll, z)
    if os.path.exists(path):
        with open(path, encoding='utf-8') as handle:
            result = json.load(handle)
        print(f'{scroll.key} z={z:.0f}: reusing {os.path.basename(path)}', flush=True)
        return result
    result = runs_per_winding.measure(scroll, z, cache, grid_cache, rays=rays,
                                      segments=segments, direction=direction)
    tmp = f'{path}.{os.getpid()}.part'
    with open(tmp, 'w', encoding='utf-8') as handle:
        json.dump(result, handle)
    os.replace(tmp, path)
    return result


def summarise(result):
    """The one line of a slice that the protocol asks for, baseline included."""
    runs = np.array(result['gap_runs'], float)
    null = np.array(result['null_one_share'])
    return {
        'scroll': result['scroll'], 'z': result['z'], 'gaps': len(runs),
        'curves': result['curves'], 'segments': result['segments'],
        'rays_used': result['rays_used'],
        'mean': float(runs.mean()),
        'zero': float(np.mean(runs == 0)), 'one': float(np.mean(runs == 1)),
        'two': float(np.mean(runs == 2)), 'three_plus': float(np.mean(runs >= 3)),
        'null_one': float(null.mean()),
        'null_one_p95': float(np.percentile(null, 95)),
    }


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--cache-root', required=True,
                        help='directory holding one chunk cache per scroll; those must '
                             'not be shared, they collide on level and coordinates')
    parser.add_argument('--grid-cache', required=True,
                        help='mesh grid cache; may be shared between scrolls')
    parser.add_argument('--out', default=None,
                        help='where slice JSON and the results table go '
                             '(default: <cache-root>/protocol)')
    parser.add_argument('--rays', type=int, default=RAYS)
    parser.add_argument('--heights', type=int, default=HEIGHTS)
    parser.add_argument('--scroll', action='append', default=None,
                        help='repeatable; default is both scrolls')
    args = parser.parse_args()

    out_dir = args.out or os.path.join(args.cache_root, 'protocol')
    os.makedirs(out_dir, exist_ok=True)
    keys = args.scroll or sorted(scrolls.SCROLLS)
    if args.rays != RAYS or args.heights != HEIGHTS:
        print(f'WARNING: running {args.heights} heights and {args.rays} rays, not the '
              f'pre-registered {HEIGHTS} and {RAYS}. Anything published from this run '
              f'has to say so.', flush=True)

    rows, failures = [], []
    for key in keys:
        scroll = scrolls.SCROLLS[key]
        cache = os.path.join(args.cache_root, scroll.cache_name)
        segments = scrolls.labelled_segments(scroll)
        heights = scrolls.protocol_heights(scroll, args.grid_cache, args.heights,
                                           segments)
        low, high = scrolls.labelled_z_extent(scroll, args.grid_cache, segments)
        print(f'\n=== {scroll.key}: {len(segments)} labelled segments, labelled '
              f'z-extent {low:.0f}..{high:.0f}', flush=True)
        print('    heights: ' + ', '.join(f'{z:.0f}' for z in heights), flush=True)
        # Settled once, from every height at once: the traversal direction is a
        # property of the scroll, and settling it per slice would make the whole run
        # hostage to the worst slice in it (PHerc0139's lowest height answers 58% on
        # its own, and cleanly when pooled).
        centre = scrolls.Centre(scroll, cache, args.grid_cache)
        direction = scrolls.traversal_direction(scroll, centre, args.grid_cache,
                                                heights, segments)
        for index, z in enumerate(heights, 1):
            print(f'\n--- {scroll.key} z={z:.0f} '
                  f'({index} of {len(heights)}) ---', flush=True)
            try:
                result = run_slice(scroll, z, cache, args.grid_cache, out_dir,
                                   segments, args.rays, direction)
            except Exception as error:                              # noqa: BLE001
                # A slice that cannot be measured is published as a slice that could
                # not be measured. Swallowing it would turn "all five heights" into
                # "the heights that worked", which is the selection the protocol exists
                # to prevent.
                failures.append((scroll.key, z, f'{type(error).__name__}: {error}'))
                print(f'FAILED: {type(error).__name__}: {error}', flush=True)
                traceback.print_exc()
                continue
            runs_per_winding.report(result)
            rows.append(summarise(result))

    table = ['# Pre-registered protocol run', '',
             f'{args.heights} heights per scroll, {args.rays} rays each, every height '
             f'published. Slice data: `{out_dir}`.', '',
             '| scroll | z | segments | gaps | 0 | **1** | 2 | 3+ | random "1" (p95) |',
             '|---|---|---|---|---|---|---|---|---|']
    for row in rows:
        table.append(
            f"| {row['scroll']} | {row['z']:.0f} | {row['curves']}/{row['segments']} | "
            f"{row['gaps']} | {row['zero']:.1%} | **{row['one']:.1%}** | "
            f"{row['two']:.1%} | {row['three_plus']:.1%} | "
            f"{row['null_one']:.1%} (p95 {row['null_one_p95']:.1%}) |")
    for scroll_key, z, error in failures:
        table.append(f'| {scroll_key} | {z:.0f} | — | — | — | **failed** | — | — | '
                     f'{error} |')
    table += ['', 'A prediction that resolved exactly the labelled sheets would put '
                  '100% in the **1** column. The random column is the same number of '
                  'runs scattered along the same stretch of ray.']

    path = os.path.join(out_dir, 'RESULTS.md')
    with open(path, 'w', encoding='utf-8', newline='\n') as handle:
        handle.write('\n'.join(table) + '\n')
    print('\n' + '\n'.join(table))
    print(f'\nwritten to {path}')
    if failures:
        print(f'{len(failures)} slice(s) failed and are in the table as failures.')


if __name__ == '__main__':
    main()
