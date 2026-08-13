"""Read the protocol run's slices and write the table the write-up quotes.

Separate from `protocol_run.py` on purpose. The run is expensive and its slices are on
disk; the summary is cheap and will be rewritten as the write-up asks different
questions of the same measurement. Keeping them apart means no question ever costs a
re-measurement, and — the point the previous artifact failed on — every number in the
write-up comes from the shipped code reading the shipped slices, not from a script that
was never published.

Usage:
    python protocol_summary.py --slices ../../output/protocol \\
        --out PROTOCOL_RESULTS.md
"""
import argparse
import glob
import json
import os
import sys

import numpy as np

BAND = 10


def load(directory):
    slices = {}
    for path in sorted(glob.glob(os.path.join(directory, '*.json'))):
        with open(path, encoding='utf-8') as handle:
            result = json.load(handle)
        slices.setdefault(result['scroll'], []).append(result)
    for results in slices.values():
        results.sort(key=lambda r: r['z'])
    return slices


def per_slice_rows(results):
    rows = []
    for result in results:
        runs = np.array(result['gap_runs'], float)
        null = np.array(result['null_one_share'])
        rows.append(
            f"| {result['scroll']} | {result['z']:.0f} | {result['curves']}/"
            f"{result['segments']} | {len(runs)} | {np.mean(runs == 0):.1%} | "
            f"**{np.mean(runs == 1):.1%}** | {np.mean(runs == 2):.1%} | "
            f"{np.mean(runs >= 3):.1%} | {null.mean():.1%} "
            f"(p95 {np.percentile(null, 95):.1%}) |")
    return rows


def band_rows(results):
    windings = np.concatenate([r['gap_winding'] for r in results])
    runs = np.concatenate([np.array(r['gap_runs'], float) for r in results])
    null = np.concatenate([r['null_one_share'] for r in results]).mean()
    low = int(np.floor(windings.min()))
    rows = []
    for start in range(low - low % BAND, int(np.ceil(windings.max())), BAND):
        take = (windings >= start) & (windings < start + BAND)
        if take.sum() < 50:                     # too few gaps to read a share off
            continue
        band = runs[take]
        rows.append(f'| {start}–{start + BAND} | {take.sum()} | '
                    f'{np.mean(band == 0):.1%} | **{np.mean(band == 1):.1%}** | '
                    f'{np.mean(band == 2):.1%} | {np.mean(band >= 3):.1%} | '
                    f'{np.mean(band == 1) / null:.2f}× |')
    return rows, float(np.mean(runs == 1)), float(null), len(runs)


def detection_rows(results):
    tolerances = results[0]['tolerance']
    hit = {t: np.concatenate([np.array(r['sheet_hits'][str(t)], float)
                              for r in results]) for t in tolerances}
    random = {t: np.concatenate([np.array(r['fake_hits'][str(t)], float)
                                 for r in results]) for t in tolerances}
    header = '| | ' + ' | '.join(f'±{t:.0f}' for t in tolerances) + ' |'
    rule = '|---|' + '---|' * len(tolerances)
    return [header, rule,
            '| mask on near a labelled sheet | '
            + ' | '.join(f'{hit[t].mean():.1%}' for t in tolerances) + ' |',
            '| same question at random radii | '
            + ' | '.join(f'{random[t].mean():.1%}' for t in tolerances) + ' |']


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--slices', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()

    slices = load(args.slices)
    if not slices:
        raise SystemExit(f'no slice JSON in {args.slices}')

    out = ['# Pre-registered protocol run — results', '',
           'Five equidistant quantiles of each scroll\'s labelled z-extent, 24 rays '
           'each, every height published, a baseline beside every number. Protocol '
           'fixed before the run: `protocol_run.py`. Numbers below are read off the '
           'slices it wrote, by `protocol_summary.py`.', '',
           '## Every slice', '',
           '| scroll | z | segments | gaps | 0 | **1** | 2 | 3+ | random "1" (p95) |',
           '|---|---|---|---|---|---|---|---|---|']
    for scroll in sorted(slices):
        out += per_slice_rows(slices[scroll])
    out += ['',
            'The **1** column is the measurement: the share of gaps between two '
            'neighbouring labelled sheets holding exactly one run of prediction. A '
            'prediction that resolved exactly the labelled sheets would put 100% '
            'there. The random column places the same number of runs along the same '
            'stretch of ray.', '']

    for scroll in sorted(slices):
        rows, overall, null, gaps = band_rows(slices[scroll])
        out += [f'## {scroll} by winding, pooled over the five heights', '',
                f'{gaps} gaps; one run in **{overall:.1%}** against a random '
                f'{null:.1%} — **{overall / null:.2f}×**.', '',
                '| windings | gaps | 0 | **1** | 2 | 3+ | vs random |',
                '|---|---|---|---|---|---|---|'] + rows + ['']
        out += ['Detection, pooled, in voxels either side of a labelled sheet '
                '(neighbouring sheets are ~22–26 vx apart):', ''] \
            + detection_rows(slices[scroll]) + ['']

    with open(args.out, 'w', encoding='utf-8', newline='\n') as handle:
        handle.write('\n'.join(out) + '\n')
    # The document is UTF-8 whatever the console is; a Windows console on a legacy
    # code page must not be able to fail the run *after* the file is written.
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(errors='replace')
    print('\n'.join(out))
    print(f'\nwritten to {args.out}')


if __name__ == '__main__':
    main()
