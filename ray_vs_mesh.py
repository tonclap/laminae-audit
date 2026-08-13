"""Can a radial ray count windings at all? A test with no prediction in it.

The exact-winding runs show counting outrunning the fit's numbering by 10-20% in the
outer half of the scroll. Three explanations were on the table:

a. the surface prediction invents laminae out there (fragments, delamination, cracks);
b. the reference meshes are wrong out there;
c. **the instrument is wrong**: a ray cast from the umbilicus can cross the same sheet
   more than once, because the scroll is not round and an outer winding can run
   tangentially to the ray for a while. Then no counter, however perfect, would return
   the winding number.

(c) is testable without the prediction, and that is what this does. The published
segment meshes are themselves curves at a fixed height; intersecting the ray with those
curves counts how many times the ray meets *labelled sheet*, and every intersection
carries its exact winding (interpolated along the mesh, as in `calibrate_exact.py`).

If a ray meets 130 sheet crossings while the outermost winding it reaches is 110, the
overcount is geometry and belongs to the method, not to the prediction.

On a scroll with no published umbilicus this script has a second job. The centre there
is fitted to the innermost labelled turn, and the turn-span identity cannot check it —
accumulated turn over a closed loop is 1.0 for any centre inside the loop. The ladder
can: with a good centre a ray meets each single-winding mesh exactly once, in order, so
"0% excess and 0 revisits" reads as a statement about the centre as much as about the
geometry.

Usage:
    python ray_vs_mesh.py --scroll PHerc0139 --cache ../../output/cache0139 \\
        --grid-cache ../../output/figgrids --z 5000 --rays 24
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


# The intersection itself lives in `scrolls.py`: settling the traversal direction needs
# it too, and one copy of the geometry is one place for it to be wrong.
ray_crossings = scrolls.ray_crossings


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    scrolls.add_argument(parser)
    parser.add_argument('--cache', required=True)
    parser.add_argument('--grid-cache', required=True)
    parser.add_argument('--z', type=float, default=None,
                        help='height; default is the middle protocol height')
    parser.add_argument('--rays', type=int, default=24)
    args = parser.parse_args()

    scroll = scrolls.SCROLLS[args.scroll]
    segments = scrolls.labelled_segments(scroll)
    if args.z is None:
        heights = scrolls.protocol_heights(scroll, args.grid_cache, segments=segments)
        args.z = heights[len(heights) // 2]
    centre = scrolls.Centre(scroll, args.cache, args.grid_cache)
    print(centre.describe(args.z), flush=True)
    direction = scrolls.traversal_direction(scroll, centre, args.grid_cache, args.z,
                                            segments)
    origin = np.array(centre.at(args.z))

    curves = scrolls.ladder_curves(scroll, centre, direction, args.grid_cache, args.z,
                                   segments)
    # The innermost labelled winding is where the ladder starts, and it is not 10 on
    # every scroll — PHerc0139 starts at 23. Read it off the curves actually usable
    # here, so a segment excluded above does not silently inflate the expectation.
    innermost = min(float(np.min(winding)) for _, winding in curves)
    reach = scrolls.ray_reach(curves, origin)
    print(f'{len(curves)} segment curves at z = {args.z:.0f}; innermost labelled '
          f'winding {innermost:.0f}, tracing rays to r = {reach:.0f} vx')

    print(f'\n{"angle":>6s}  {"crossings":>9s}  {"max winding":>11s}  '
          f'{"expected":>12s}  {"excess":>7s}  {"revisits":>8s}')
    excesses, revisit_counts = [], []
    for step in range(args.rays):
        angle = 2 * np.pi * step / args.rays
        unit = np.array([np.cos(angle), np.sin(angle)])
        hits = []
        for polyline, winding in curves:
            hits += ray_crossings(polyline, winding, origin, unit, reach)
        if len(hits) < 10:
            continue
        hits.sort()
        windings = np.array([h[1] for h in hits])
        highest = windings.max()
        # How many labelled windings *should* a ray reaching this far cross? One per
        # winding from the innermost labelled one to the outermost it reaches.
        expected = highest - innermost + 1.0
        excess = len(hits) - expected
        # A revisit is a crossing whose winding is not monotonically increasing along
        # the ray: the ray came back to sheet it had already passed.
        revisits = int(np.count_nonzero(np.diff(windings) < -0.25))
        excesses.append(excess / expected)
        revisit_counts.append(revisits)
        print(f'{np.degrees(angle):6.0f}  {len(hits):9d}  {highest:11.1f}  '
              f'{expected:12.1f}  {excess:+7.1f}  {revisits:8d}')

    if excesses:
        print(f'\nexcess crossings over windings spanned: median '
              f'{np.median(excesses):+.1%}  '
              f'(min {np.min(excesses):+.1%}, max {np.max(excesses):+.1%}) '
              f'over {len(excesses)} rays')
        print(f'non-monotone crossings per ray: median {np.median(revisit_counts):.0f}, '
              f'max {np.max(revisit_counts)}')
        print('\nA ray that met each labelled winding exactly once would show 0% excess '
              'and 0 revisits.')


if __name__ == '__main__':
    main()
