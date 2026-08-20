"""Counting checked point by point against `abs_winding.json` — the fit's own anchor.

The published calibration is scored against the 28 segment names, which are 2 to 18
windings wide, and reports the offset as a median over many rays. That is the weaker
of the two available tests and it is the one that was published.

This is the sharper one. `abs_winding.json` is the file `fit_spiral.py` reads to learn
where absolute winding zero is: `get_patch_abs_winding_loss` pins the spiral's shifted
radius at each of its points to `winding_annotation * dr_per_winding`, and no other
input to the fit carries an absolute number. It holds 59 hand-placed points, 48 of them
consecutive windings 16-63 on a single z-slice (z = 15694, the slice this project
published its constant on).

So: count laminae from the umbilicus to each of those points and compare with the
number a human wrote there. Exact integers, no intervals, no medians — one prediction
against one label, 59 times.

Every number is printed next to a baseline, as it has to be: the labels shuffled among
the same points, which keeps every marginal and destroys only the association.

Usage:
    python check_abs_winding.py --cache ../../output/figcache [--out results.json]
"""
import argparse
import json
import os
import sys
import urllib.request

import numpy as np

# `absolute_winding_calibration.py` sits beside this file in the published repository
# and one directory over in the working one. Add the second location only if it exists,
# so the published copies are byte-identical to the ones that produced the numbers.
_STANDALONE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'standalone')
if os.path.isdir(_STANDALONE):
    sys.path.insert(0, _STANDALONE)
import absolute_winding_calibration as awc                            # noqa: E402

ABS_WINDING = awc.DATA_SERVER + 'abs_winding.json'


def load_labels(cache):
    """The hand-placed absolute winding points, flagged as absolute by the file itself."""
    path = os.path.join(cache, 'abs_winding.json')
    if not os.path.exists(path):
        os.makedirs(cache, exist_ok=True)
        data = urllib.request.urlopen(ABS_WINDING, timeout=120).read()
        tmp = f'{path}.{os.getpid()}.part'
        with open(tmp, 'wb') as handle:
            handle.write(data)
        os.replace(tmp, path)
    with open(path, encoding='utf-8-sig') as handle:
        doc = json.load(handle)
    rows = []
    for name, collection in doc['collections'].items():
        # `fit_spiral.py` only treats a collection as absolute when this flag is set
        # (fit_spiral.py:718-726), so this reader applies the same filter rather than
        # assuming every collection in the file is absolute.
        if not collection.get('metadata', {}).get('winding_is_absolute', False):
            continue
        for point in (collection.get('points') or {}).values():
            if point.get('wind_a') is None:
                continue
            rows.append(dict(collection=collection.get('name', name),
                             winding=float(point['wind_a']),
                             point=np.array(point['p'], float)))
    rows.sort(key=lambda row: (row['point'][2], row['winding']))
    return rows


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--cache', required=True)
    parser.add_argument('--threshold', type=int, default=115)
    parser.add_argument('--step', type=float, default=0.5)
    parser.add_argument('--out')
    args = parser.parse_args()

    rows = load_labels(args.cache)
    prediction = awc.Prediction(args.cache)
    control = awc.load_umbilicus(None, args.cache)
    print(f'{len(rows)} hand-placed absolute winding points in {ABS_WINDING}')

    for row in rows:
        point = row['point']
        ux, uy = awc.umbilicus_at(control, point[2])
        origin = np.array([ux, uy, point[2]])
        row['radius'] = float(np.hypot(point[0] - ux, point[1] - uy))
        row['counted'] = awc.count_to_point(prediction, origin, point,
                                            args.threshold, args.step)
        print(f"  z {point[2]:8.1f}  r {row['radius']:6.0f}  labelled "
              f"{row['winding']:5.0f}  counted {row['counted']:4d}  "
              f"implied C {row['winding'] - row['counted']:+5.0f}", flush=True)

    labelled = np.array([row['winding'] for row in rows], float)
    counted = np.array([row['counted'] for row in rows], float)
    implied = labelled - counted
    slope, intercept = np.polyfit(counted, labelled, 1)
    print(f'\nslope {slope:.3f}  intercept {intercept:+.1f}  '
          f'r {np.corrcoef(counted, labelled)[0, 1]:.4f}')
    print(f'implied constant: median {np.median(implied):+.1f}  '
          f'mean {implied.mean():+.2f}  '
          f'iqr {np.subtract(*np.percentile(implied, [75, 25])):.1f}  '
          f'range {implied.min():+.0f}..{implied.max():+.0f}')

    rng = np.random.default_rng(0)
    print('\n            exact   ±1     ±2      | shuffled-label baseline (200 draws)')
    for constant in (5, 6, 7, 8):
        error = np.abs(implied - constant)
        null = []
        for _ in range(200):
            shuffled = rng.permutation(labelled) - counted
            null.append(float(np.mean(np.abs(shuffled - constant) <= 1)))
        print(f'  C = +{constant}:  {np.mean(error < 0.5):.3f}  '
              f'{np.mean(error <= 1):.3f}  {np.mean(error <= 2):.3f}   |  '
              f'±1 null mean {np.mean(null):.3f}  p95 {np.percentile(null, 95):.3f}')

    if args.out:
        with open(args.out, 'w', encoding='utf-8') as handle:
            json.dump([dict(collection=row['collection'], winding=row['winding'],
                            counted=row['counted'], radius=row['radius'],
                            point=row['point'].tolist()) for row in rows],
                      handle, indent=1)
        print(f'\nwrote {args.out}')


if __name__ == '__main__':
    main()
