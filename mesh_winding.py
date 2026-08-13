"""Exact per-point winding from the segment meshes, instead of an interval midpoint.

The published calibration scores every point of a segment against the interval in its
name — 2 windings wide for `w116-117`, 18 for `w010-027` — and regresses the segment's
median count against the interval's midpoint. That makes the reference coarse and, if
mesh point density is not uniform across a segment's windings, biased: the regression
slope then measures the reference's parameterisation as much as the counting.

There is a better reference hiding in the same files. A tifxyz mesh is a regular grid:
axis 0 is height, axis 1 runs along the spiral. Walking axis 1 at fixed height and
accumulating the turn around the umbilicus gives the winding advance **in radians of
actual geometry** — no naming convention involved. That number can then be checked
against the name, which is the first thing this script does.

First result, and it fixes a convention this project had wrong: `w010-027` spans
18.0 turns, not 17. The name is inclusive of both ends — `w010-027` is windings 10
through 27, eighteen of them — so the midpoint used as truth was off by half a winding
and the per-point truth was never used at all.

The identity checked here is what licenses the whole reference, so it is the first
thing to run on a scroll that has not been measured before. On PHerc0139 every segment
is named for a single winding, so the expected span is 1.000 turn — a weaker test than
Paris 4's 18-turn segment, but the same test.

Usage:
    python mesh_winding.py --scroll PHerc0139 --grid-cache ../../output/figgrids \\
        --cache ../../output/cache0139
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
import scrolls                                                        # noqa: E402


def segment_grid(name, cache, scroll=None):
    """The tifxyz grid with its shape kept: (rows, cols, 3), -1 where invalid."""
    return scrolls.segment_grid(name, scroll or scrolls.PARIS4, cache)


def iso_z_row(grid, z, max_dz=None):
    """The grid row whose points sit nearest this height, and its valid mask.

    Rows are ~19 voxels apart in z for these meshes, so a row is used as-is rather
    than interpolated between rows: the winding advance along a row is what is being
    measured, and interpolation across rows would mix two different heights into one
    accumulated angle for no gain. A row further than `max_dz` from the height asked
    for is refused rather than returned — see `scrolls.iso_z_row`.
    """
    return scrolls.iso_z_row(grid, z, max_dz)


def turn_profile(grid, row, mask, control):
    """Cumulative turn around the umbilicus along the row, in windings."""
    centre = (control if hasattr(control, 'at')
              else scrolls.centre_from_control(control))
    return scrolls.turn_profile(grid, row, mask, centre)


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    scrolls.add_argument(parser)
    parser.add_argument('--cache', required=True)
    parser.add_argument('--grid-cache', required=True)
    parser.add_argument('--z', type=float, nargs='+', default=None,
                        help='heights to check; default is the pre-registered '
                             'protocol heights for this scroll')
    args = parser.parse_args()

    os.makedirs(args.grid_cache, exist_ok=True)
    scroll = scrolls.SCROLLS[args.scroll]
    segments = scrolls.labelled_segments(scroll)
    control = scrolls.Centre(scroll, args.cache, args.grid_cache)
    args.z = args.z or scrolls.protocol_heights(scroll, args.grid_cache,
                                                segments=segments)

    print('turn = angle accumulated around the centre along the mesh grid;')
    print(f'centre = {control.source}')
    print('named  = high - low + 1 if the name is inclusive of both ends\n')
    header = '  '.join(f'z={z:.0f}'.rjust(14) for z in args.z)
    print(f'{"segment":11s} {"named":>6s}  {header}')
    totals = {z: [] for z in args.z}
    for name, low, high in segments:
        grid = segment_grid(name, args.grid_cache, scroll)
        cells = []
        for z in args.z:
            row, mask = iso_z_row(grid, z)
            if row is None or mask.sum() < 10:
                cells.append('—'.rjust(14))
                continue
            points, turns, _ = turn_profile(grid, row, mask, control)
            span = float(turns[-1] - turns[0])
            named = high - low + 1
            totals[z].append(span / named)
            cells.append(f'{span:+7.3f} ({span / named:5.3f})'.rjust(14))
        print(f'w{low:03d}-{high:03d}  {high - low + 1:6d}  ' + '  '.join(cells),
              flush=True)

    print()
    for z in args.z:
        ratios = np.array(totals[z])
        if len(ratios):
            print(f'z={z:.0f}: turns / (high-low+1) over {len(ratios)} segments — '
                  f'median {np.median(ratios):.4f}  '
                  f'mean {ratios.mean():.4f}  min {ratios.min():.4f}  '
                  f'max {ratios.max():.4f}')


if __name__ == '__main__':
    main()
