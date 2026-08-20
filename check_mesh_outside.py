"""How much of each published segment mesh lies outside the scan mask, by z.

The sampling defect this project found in its own calibration (a third of scored
points not on the scroll at z = 15694) has a second reading that is not about us: it
is a property of the published segment meshes. Above some height the fitted surfaces
leave the scanned volume.

This measures that directly and over **every** mesh point in the z-band, not over the
16-per-segment sample the calibration draws, so the number is about villa's data
rather than about our sampling.

Criterion, fixed before the run: the CT volume is `…-masked.zarr`, so `CT == 0` is
outside the scan mask. No tunable threshold.

Usage:
    python check_mesh_outside.py --cache ../../output/figcache \\
        --mesh-cache ../../output/figmeshes
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
import absolute_winding_calibration as awc                            # noqa: E402
import planes                                                         # noqa: E402


def outside_fraction(ct, meshes, z, z_band):
    """(points in band, fraction outside the mask, fraction outside per segment)."""
    bands, per_segment = [], []
    for name, low, high in awc.labelled_segments():
        mesh = meshes[name]
        band = mesh[np.abs(mesh[:, 2] - z) <= z_band]
        if len(band):
            bands.append((name, low, high, band))
    points = np.concatenate([b[3] for b in bands])
    x0, y0 = int(points[:, 0].min()) - 4, int(points[:, 1].min()) - 4
    image = ct.window(z, max(0, y0), int(points[:, 1].max()) + 5,
                      max(0, x0), int(points[:, 0].max()) + 5)

    def sample(pts):
        rows = np.clip(np.rint(pts[:, 1]).astype(int) - max(0, y0),
                       0, image.shape[0] - 1)
        cols = np.clip(np.rint(pts[:, 0]).astype(int) - max(0, x0),
                       0, image.shape[1] - 1)
        return image[rows, cols]

    for name, low, high, band in bands:
        per_segment.append((low, high, float(np.mean(sample(band) == 0)), len(band)))
    return len(points), float(np.mean(sample(points) == 0)), per_segment


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--cache', required=True)
    parser.add_argument('--mesh-cache', required=True)
    parser.add_argument('--z', type=float, nargs='+',
                        default=[3100, 3500, 4000, 6000, 9000, 12000, 15694, 18000])
    parser.add_argument('--z-band', type=float, default=3.0)
    parser.add_argument('--detail', type=float,
                        help='print the per-segment breakdown for this z')
    args = parser.parse_args()

    ct = planes.CTPlane(args.cache)
    meshes = {name: awc.segment_points(name, args.mesh_cache)
              for name, _, _ in awc.labelled_segments()}

    print('every mesh point of the 28 labelled segments within ±3 voxels of z,')
    print('against the scan mask of 20260411134726-2.400um-…-masked.zarr\n')
    print(f'{"z":>7}  {"points":>8}  {"outside the scan mask":>22}')
    detail = None
    for z in args.z:
        total, fraction, per_segment = outside_fraction(ct, meshes, z, args.z_band)
        print(f'{z:7.0f}  {total:8d}  {fraction:21.1%}', flush=True)
        if args.detail is not None and abs(z - args.detail) < 0.5:
            detail = per_segment

    if detail:
        print(f'\nper segment at z = {args.detail:.0f}:')
        for low, high, fraction, count in detail:
            print(f'  w{low:03d}-{high:03d}  {fraction:6.1%}  of {count:6d} points')


if __name__ == '__main__':
    main()
