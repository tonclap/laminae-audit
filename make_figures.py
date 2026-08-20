"""Pictures of what the absolute-winding calibration actually does, on real data.

Asked for directly by the villa maintainer on PR #1421: "any accompanying images or
demonstrations of accuracy … send a picture of what some of these look like".

Nothing here re-derives the result. The counting is `absolute_winding_calibration.py`
called as a library — same slice, same threshold, same step, same convention; this
file only draws what that code walks over. The two are kept honest by an assertion:
the number of tick marks drawn must equal what `count_to_point` returns.

Figures, in the order they answer a sceptic:

    fig1_slice.png   where the ray is: the CT slice, the umbilicus counting starts
                     from, the rays, the published segment meshes and the hand-placed
                     absolute winding labels.
    fig2_ray.png     the demonstration. One ray, straightened: raw CT on top, the
                     binary surface prediction the counting runs on below it, and
                     under both the running count + C against two independent-of-us
                     ground truths — the winding intervals of the segments the ray
                     passes through, and the individual hand-placed labels of
                     `abs_winding.json`.
    fig3_zoom.png    the same ray at 1:1, a few hundred voxels of it, so the laminae
                     and the ticks can be counted by eye.
    fig4_gate.png    the same picture on z = 18000, where the tool's own slope gate
                     refuses the slice. The failure is meant to be visible too.
    fig5_labels.png  accuracy against `abs_winding.json` point by point: the file
                     `fit_spiral.py` reads to learn where absolute winding zero is.

Usage:
    python make_figures.py --cache ../../output/figcache \\
        --mesh-cache ../../output/figmeshes --out ./out
"""
import argparse
import functools
import json
import os
import sys

import matplotlib
import numpy as np

matplotlib.use('Agg')
import matplotlib.pyplot as plt                                       # noqa: E402
from matplotlib.patches import Rectangle                              # noqa: E402

# `absolute_winding_calibration.py` sits beside this file in the published repository
# and one directory over in the working one. Add the second location only if it exists,
# so the published copies are byte-identical to the ones that produced the numbers.
_STANDALONE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'standalone')
if os.path.isdir(_STANDALONE):
    sys.path.insert(0, _STANDALONE)
import absolute_winding_calibration as awc                            # noqa: E402
import check_abs_winding                                              # noqa: E402
import planes                                                         # noqa: E402

ORANGE = '#e0632c'
BLUE = '#33648f'
INK = '#141414'

# The listing is one HTTP request and is asked for from four places below.
labelled_segments = functools.lru_cache(1)(awc.labelled_segments)


def _resample(window, ys, xs, bilinear):
    """Sample `window` at float (y, x). Bilinear for the CT, nearest for the mask.

    Written out rather than taken from `scipy.ndimage`: scipy in this environment is
    built against numpy 1 and fails to import under numpy 2, and a figure script is
    not worth an environment fight.
    """
    height, width = window.shape
    if not bilinear:
        yi = np.clip(np.rint(ys).astype(int), 0, height - 1)
        xi = np.clip(np.rint(xs).astype(int), 0, width - 1)
        return window[yi, xi].astype(np.float32)
    y0 = np.clip(np.floor(ys).astype(int), 0, height - 2)
    x0 = np.clip(np.floor(xs).astype(int), 0, width - 2)
    fy, fx = ys - y0, xs - x0
    top = window[y0, x0] * (1 - fx) + window[y0, x0 + 1] * fx
    bottom = window[y0 + 1, x0] * (1 - fx) + window[y0 + 1, x0 + 1] * fx
    return (top * (1 - fy) + bottom * fy).astype(np.float32)


def ray_band(reader, z, origin, angle, radius, half, bilinear):
    """Straightened strip along a ray: rows = perpendicular offset, cols = radius."""
    unit = np.array([np.cos(angle), np.sin(angle)])
    perp = np.array([-unit[1], unit[0]])
    rs = np.arange(0.0, radius + 1.0)
    ss = np.arange(-half, half + 1.0)
    xs = origin[0] + rs[None, :] * unit[0] + ss[:, None] * perp[0]
    ys = origin[1] + rs[None, :] * unit[1] + ss[:, None] * perp[1]
    x0, x1 = int(np.floor(xs.min())) - 2, int(np.ceil(xs.max())) + 3
    y0, y1 = int(np.floor(ys.min())) - 2, int(np.ceil(ys.max())) + 3
    x0, y0 = max(0, x0), max(0, y0)
    window = reader.window(z, y0, y1, x0, x1).astype(np.float32)
    # Bilinear for the CT (it is a real image), nearest for the binary prediction —
    # interpolating a mask would smear the very edges the counting keys on.
    return _resample(window, ys - y0, xs - x0, bilinear)


def crossings(pred, origin, angle, radius, threshold, step):
    """Radii at which the ray enters a lamina — the positions behind the count.

    The same rising-edge rule as `awc.count_runs`; the caller asserts the two agree.
    """
    ts = np.arange(0.0, radius + step, step)
    unit = np.array([np.cos(angle), np.sin(angle), 0.0])
    above = (pred.sample(origin[None, :] + ts[:, None] * unit[None, :])
             >= threshold).astype(np.int8)
    return ts[np.flatnonzero(np.diff(above, prepend=np.int8(0)) == 1)]


def segment_ladder(meshes, z, z_band, origin, angle, half_angle_deg):
    """Published segments crossing this ray: (radius, low, high) per mesh point."""
    out = []
    for name, low, high in labelled_segments():
        band = meshes[name][np.abs(meshes[name][:, 2] - z) <= z_band]
        if not len(band):
            continue
        dx, dy = band[:, 0] - origin[0], band[:, 1] - origin[1]
        delta = np.arctan2(dy, dx) - angle
        close = np.abs(np.arctan2(np.sin(delta), np.cos(delta))) \
            <= np.deg2rad(half_angle_deg)
        out += [(float(r), low, high) for r in np.hypot(dx, dy)[close]]
    return sorted(out)


def label_ladder(labels, z, origin, angle, half, radius):
    """Hand-placed absolute labels lying inside the drawn strip: (radius, perp, w)."""
    unit = np.array([np.cos(angle), np.sin(angle)])
    out = []
    for row in labels:
        point = row['point']
        if abs(point[2] - z) > 2.0:
            continue
        vector = np.array([point[0] - origin[0], point[1] - origin[1]])
        along = float(vector @ unit)
        across = float(vector @ np.array([-unit[1], unit[0]]))
        if 0 <= along <= radius and abs(across) <= half:
            out.append((along, across, row['winding'], row['counted']))
    return sorted(out)


def draw_ray(axes, bands, cross, ladder, labels, constant, r0, r1, numbers=False):
    """The three stacked panels: CT strip, prediction strip, count vs. windings."""
    ct_band, pred_band, half = bands
    extent = (0, ct_band.shape[1], -half, half)
    axes[0].imshow(ct_band, cmap='gray', aspect='auto', extent=extent,
                   vmin=0, vmax=200, interpolation='nearest')
    axes[0].set_ylabel('raw CT\n2.4 µm scan', fontsize=8)
    axes[1].imshow(pred_band, cmap='gray', aspect='auto', extent=extent,
                   vmin=0, vmax=255, interpolation='nearest')
    axes[1].set_ylabel('surface\nprediction', fontsize=8)
    for axis in axes[:2]:
        axis.axhline(0, color=ORANGE, lw=0.5, alpha=0.7)
        axis.set_yticks([])
        axis.plot(cross, np.full(len(cross), -half + 2), marker='^', ms=3.0, lw=0,
                  color=ORANGE, clip_on=True)
        if labels:
            axis.plot([l[0] for l in labels], [l[1] for l in labels], marker='o',
                      ms=3.2, lw=0, mfc='none', mec='#111111', mew=0.9, clip_on=True)

    for radius, low, high in ladder:
        axes[2].add_patch(Rectangle((radius - 2.5, low), 5, high - low + 0.02,
                                    facecolor=BLUE, edgecolor='none', alpha=0.7))
    axes[2].plot([], [], color=BLUE, lw=6, alpha=0.7,
                 label='published segment mesh: the winding interval in its name')
    staircase_x = np.concatenate(([0.0], np.repeat(cross, 2), [r1]))
    staircase_y = np.repeat(np.arange(len(cross) + 1) + constant, 2)
    axes[2].plot(staircase_x, staircase_y, color=ORANGE, lw=1.3,
                 label=f'laminae counted from the umbilicus {constant:+.0f}')
    if labels:
        axes[2].plot([l[0] for l in labels], [l[2] for l in labels], marker='o',
                     ms=3.4, lw=0, mfc='none', mec='#111111', mew=0.9,
                     label='hand-placed label in abs_winding.json')
    axes[2].set_ylabel('absolute winding number', fontsize=9)
    axes[2].set_xlabel('radius from the umbilicus, voxels at level 2 (9.6 µm)',
                       fontsize=9)
    axes[2].legend(loc='upper left', fontsize=8, framealpha=0.92)
    axes[2].grid(alpha=0.22, lw=0.4)
    if numbers:
        for index, radius in enumerate(cross, 1):
            if r0 <= radius <= r1:
                # Below the step, so the numbers do not sit on top of the hand-placed
                # label markers, which are what a reader is comparing them against.
                axes[2].annotate(f'{index + int(constant)}', (radius, index + constant),
                                 textcoords='offset points', xytext=(3, -11),
                                 ha='left', fontsize=7, color=ORANGE)
    for axis in axes:
        axis.set_xlim(r0, r1)


class Slice:
    """Everything one z-slice contributes to the figures."""

    def __init__(self, args, z, meshes, labels, control):
        self.args, self.z, self.meshes, self.labels = args, z, meshes, labels
        ux, uy = awc.umbilicus_at(control, z)
        self.origin = np.array([ux, uy, float(z)])
        self.ct = planes.CTPlane(args.cache)
        self.pred_plane = planes.PredictionPlane(args.cache)
        self.pred = awc.Prediction(args.cache)
        here = [meshes[name][np.abs(meshes[name][:, 2] - z) <= args.z_band]
                for name, _, _ in labelled_segments()]
        self.points = np.concatenate([p for p in here if len(p)])
        self.radius = float(np.hypot(self.points[:, 0] - ux,
                                     self.points[:, 1] - uy).max()) + 60

    def sampled(self):
        """The 16-per-segment points the calibration actually scores, with a flag for
        whether each one is inside the scan mask. Same rng seeding as the published
        run, so these are the same points."""
        chosen = []
        for name, _, _ in labelled_segments():
            band = self.meshes[name][
                np.abs(self.meshes[name][:, 2] - self.z) <= self.args.z_band]
            if not len(band):
                continue
            index = np.random.default_rng(0).choice(
                len(band), min(16, len(band)), replace=False)
            chosen.append(band[index])
        chosen = np.concatenate(chosen)
        x0, y0 = int(chosen[:, 0].min()) - 4, int(chosen[:, 1].min()) - 4
        image = self.ct.window(self.z, max(0, y0), int(chosen[:, 1].max()) + 5,
                               max(0, x0), int(chosen[:, 0].max()) + 5)
        rows = np.clip(np.rint(chosen[:, 1]).astype(int) - max(0, y0),
                       0, image.shape[0] - 1)
        cols = np.clip(np.rint(chosen[:, 0]).astype(int) - max(0, x0),
                       0, image.shape[1] - 1)
        return chosen, image[rows, cols] > 0

    def ray(self, angle, radius=None, half=None):
        radius = self.radius if radius is None else radius
        half = self.args.band_half if half is None else half
        cross = crossings(self.pred, self.origin, angle, radius,
                          self.args.threshold, self.args.step)
        # The picture must be of the published method, not of a lookalike: same count,
        # same function, same ray.
        target = self.origin + np.array([np.cos(angle), np.sin(angle), 0.0]) * radius
        counted = awc.count_to_point(self.pred, self.origin, target,
                                     self.args.threshold, self.args.step)
        assert len(cross) == counted, (len(cross), counted)
        bands = (ray_band(self.ct, self.z, self.origin, angle, radius, half, True),
                 ray_band(self.pred_plane, self.z, self.origin, angle, radius, half, False),
                 half)
        ladder = segment_ladder(self.meshes, self.z, self.args.z_band, self.origin,
                                angle, self.args.half_angle)
        marks = label_ladder(self.labels, self.z, self.origin, angle, half, radius)
        print(f'  z={self.z:.0f} ray {np.degrees(angle) % 360:6.1f}°: {len(cross)} laminae '
              f'to r={radius:.0f}, {len(ladder)} segment points, {len(marks)} labels',
              flush=True)
        return dict(cross=cross, bands=bands, ladder=ladder, labels=marks,
                    radius=radius, angle=angle)


def figure_ray(ray, constant, path, title, zoom=None, numbers=False):
    ratios = [1, 1, 2.2] if zoom else [1, 1, 3]
    fig, axes = plt.subplots(3, 1, figsize=(13, 7.4), height_ratios=ratios,
                             sharex=True, constrained_layout=True)
    r0, r1 = zoom if zoom else (0.0, ray['radius'])
    draw_ray(axes, ray['bands'], ray['cross'], ray['ladder'], ray['labels'],
             constant, r0, r1, numbers=numbers)
    if zoom:
        inside = [item for item in ray['ladder'] if r0 <= item[0] <= r1]
        marks = [item for item in ray['labels'] if r0 <= item[0] <= r1]
        low = min([i[1] for i in inside] + [i[2] for i in marks] or [0]) - 4
        high = max([i[2] for i in inside] + [i[2] for i in marks] or [1]) + 4
        axes[2].set_ylim(low, high)
    axes[0].set_title(title, fontsize=10.5, loc='left')
    fig.savefig(path, dpi=190)
    plt.close(fig)
    print('wrote', path, flush=True)


def figure_slice(state, rays, path, title, downsample=5):
    ux, uy = state.origin[0], state.origin[1]
    half = int(state.radius) + 80
    x0, y0 = max(0, int(ux) - half), max(0, int(uy) - half)
    image = state.ct.window(state.z, y0, int(uy) + half, x0, int(ux) + half)
    image = image[::downsample, ::downsample]
    fig, axis = plt.subplots(figsize=(9.5, 9.5), constrained_layout=True)
    axis.imshow(image, cmap='gray', vmin=0, vmax=200,
                extent=(x0, x0 + image.shape[1] * downsample,
                        y0 + image.shape[0] * downsample, y0))
    axis.scatter(state.points[:, 0], state.points[:, 1], s=0.2, c=BLUE, alpha=0.35,
                 label='published segment meshes, windings 10–129')
    chosen, on_mask = state.sampled()
    axis.scatter(chosen[on_mask, 0], chosen[on_mask, 1], s=7, c=BLUE,
                 edgecolors='none', label='scored point, inside the scan mask')
    axis.scatter(chosen[~on_mask, 0], chosen[~on_mask, 1], s=13, c='#d11a1a',
                 marker='x', linewidths=0.8,
                 label=f'scored point, outside it ({(~on_mask).mean():.0%})')
    here = [row['point'] for row in state.labels if abs(row['point'][2] - state.z) <= 2]
    if here:
        here = np.array(here)
        axis.scatter(here[:, 0], here[:, 1], s=5, facecolors='none', edgecolors='k',
                     linewidths=0.5, label='hand-placed abs_winding.json labels')
    for ray in rays:
        angle, radius = ray['angle'], ray['radius']
        axis.plot([ux, ux + np.cos(angle) * radius], [uy, uy + np.sin(angle) * radius],
                  color=ORANGE, lw=1.0)
    axis.plot([ux], [uy], marker='+', ms=15, mew=2, color=ORANGE, lw=0,
              label='umbilicus — counting starts here')
    axis.legend(loc='lower right', fontsize=8, framealpha=0.92)
    axis.set_title(title, fontsize=10.5, loc='left')
    axis.set_xlabel('x, voxels at level 2', fontsize=9)
    axis.set_ylabel('y, voxels at level 2', fontsize=9)
    fig.savefig(path, dpi=190)
    plt.close(fig)
    print('wrote', path, flush=True)


def figure_labels(labels, constant, path):
    """Counted + C against every hand-placed absolute label, and the residuals."""
    labelled = np.array([row['winding'] for row in labels], float)
    counted = np.array([row['counted'] for row in labels], float)
    zs = np.array([row['point'][2] for row in labels], float)
    residual = counted + constant - labelled
    slope = np.polyfit(counted, labelled, 1)[0]

    fig, axes = plt.subplots(1, 2, figsize=(12, 5.2), width_ratios=[1.25, 1],
                             constrained_layout=True)
    main = np.abs(zs - 15694) < 2
    axes[0].plot([0, 70], [0, 70], color='#999999', lw=0.9, ls='--',
                 label='perfect agreement')
    axes[0].scatter(labelled[main], (counted + constant)[main], s=26, c=ORANGE,
                    edgecolors='none', label=f'z = 15694 ({main.sum()} labels)')
    axes[0].scatter(labelled[~main], (counted + constant)[~main], s=30, c=BLUE,
                    marker='s', edgecolors='none',
                    label=f'four other slices ({(~main).sum()} labels)')
    axes[0].set_xlabel('absolute winding a human wrote in abs_winding.json', fontsize=9)
    axes[0].set_ylabel(f'laminae counted from the umbilicus {constant:+.0f}', fontsize=9)
    axes[0].set_title(f'{len(labels)} hand-placed labels, slope {slope:.3f}, '
                      f'r {np.corrcoef(counted, labelled)[0, 1]:.4f}',
                      fontsize=10.5, loc='left')
    axes[0].legend(loc='upper left', fontsize=8)
    axes[0].grid(alpha=0.22, lw=0.4)
    axes[0].set_xlim(5, 70)
    axes[0].set_ylim(5, 70)

    bins = np.arange(residual.min() - 0.5, residual.max() + 1.5)
    axes[1].hist(residual, bins=bins, color=ORANGE, edgecolor='white')
    axes[1].axvline(0, color='#999999', lw=0.9, ls='--')
    # The baseline belongs next to the number, and computed rather than quoted: the
    # labels shuffled among the same points, which keeps every marginal and destroys
    # only the association.
    rng = np.random.default_rng(0)
    null = np.mean([np.mean(np.abs(counted + constant - rng.permutation(labelled)) <= 1)
                    for _ in range(200)])
    axes[1].set_xlabel(f'error in windings (counted {constant:+.0f} − label)',
                       fontsize=9)
    axes[1].set_ylabel('labels', fontsize=9)
    axes[1].set_title(f'exact {np.mean(residual == 0):.0%}, within ±1 '
                      f'{np.mean(np.abs(residual) <= 1):.0%}, against a shuffled-label '
                      f'baseline of {null:.0%}', fontsize=10.5, loc='left')
    axes[1].grid(alpha=0.22, lw=0.4, axis='y')
    fig.savefig(path, dpi=190)
    plt.close(fig)
    print('wrote', path, flush=True)


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--cache', required=True)
    parser.add_argument('--mesh-cache', required=True)
    parser.add_argument('--out', default='./out')
    parser.add_argument('--z', type=float, default=15694.0)
    parser.add_argument('--gate-z', type=float, default=18000.0)
    parser.add_argument('--constant', type=float, default=6.0)
    parser.add_argument('--z-band', type=float, default=3.0)
    parser.add_argument('--half-angle', type=float, default=1.5)
    parser.add_argument('--band-half', type=float, default=60.0)
    parser.add_argument('--threshold', type=int, default=115)
    parser.add_argument('--step', type=float, default=0.5)
    parser.add_argument('--zoom', type=float, nargs=2, default=(700.0, 1000.0))
    parser.add_argument('--labels-json',
                        help='output of check_abs_winding.py --out; recomputed if absent')
    args = parser.parse_args()

    os.makedirs(args.out, exist_ok=True)
    plt.rcParams.update({'font.size': 9, 'axes.edgecolor': INK, 'axes.labelcolor': INK,
                         'text.color': INK, 'xtick.color': INK, 'ytick.color': INK,
                         'figure.facecolor': 'white'})

    control = awc.load_umbilicus(None, args.cache)
    meshes = {name: awc.segment_points(name, args.mesh_cache)
              for name, _, _ in labelled_segments()}
    labels = check_abs_winding.load_labels(args.cache)
    if args.labels_json and os.path.exists(args.labels_json):
        with open(args.labels_json, encoding='utf-8') as handle:
            counted = {(row['winding'], round(row['point'][2], 1)): row['counted']
                       for row in json.load(handle)}
        for row in labels:
            row['counted'] = counted[(row['winding'], round(row['point'][2], 1))]
    else:
        prediction = awc.Prediction(args.cache)
        for row in labels:
            point = row['point']
            ux, uy = awc.umbilicus_at(control, point[2])
            row['counted'] = awc.count_to_point(
                prediction, np.array([ux, uy, point[2]]), point,
                args.threshold, args.step)

    figure_labels(labels, args.constant, os.path.join(args.out, 'fig5_labels.png'))

    main_slice = Slice(args, args.z, meshes, labels, control)
    # The 48 consecutive labels on this slice sit along one direction; taking the ray
    # through their median angle is what puts them inside the drawn strip.
    here = np.array([row['point'] for row in labels
                     if abs(row['point'][2] - args.z) <= 2])
    angle = float(np.median(np.arctan2(here[:, 1] - main_slice.origin[1],
                                       here[:, 0] - main_slice.origin[0]))) \
        if len(here) else 0.0
    ray = main_slice.ray(angle)
    others = [main_slice.ray(angle + offset)
              for offset in (np.pi / 2, np.pi, 3 * np.pi / 2)]

    figure_slice(main_slice, [ray] + others, os.path.join(args.out, 'fig1_slice.png'),
                 f'PHerc. Paris 4, z = {args.z:.0f}: the CT slice, the umbilicus '
                 f'counting starts from, four rays, and both ground truths')
    figure_ray(ray, args.constant, os.path.join(args.out, 'fig2_ray.png'),
               f'z = {args.z:.0f}, ray at {np.degrees(angle) % 360:.0f}°: laminae counted '
               f'outward from the umbilicus, {args.constant:+.0f},\nagainst the '
               f'published segment intervals and the hand-placed absolute labels')
    figure_ray(ray, args.constant, os.path.join(args.out, 'fig3_zoom.png'),
               f'z = {args.z:.0f}, radius {args.zoom[0]:.0f}–{args.zoom[1]:.0f} at '
               f'1:1 — every tick is one lamina entered,\nevery number the absolute '
               f'winding it implies', zoom=tuple(args.zoom), numbers=True)
    for index, other in enumerate(others, 1):
        figure_ray(other, args.constant,
                   os.path.join(args.out, f'fig2_ray_{index}.png'),
                   f'z = {args.z:.0f}, ray at {np.degrees(other["angle"]) % 360:.0f}° — the '
                   f'same slice, another direction')

    gate = Slice(args, args.gate_z, meshes, labels, control)
    gate_ray = gate.ray(angle)
    figure_ray(gate_ray, args.constant, os.path.join(args.out, 'fig4_gate.png'),
               f'z = {args.gate_z:.0f}: the slice the published tool refuses, slope '
               f'0.465.\nDrawing it showed why — see fig6: half the scored points here '
               f'are not on the scroll at all.')
    # The reason the gate fired at z = 18000 is a sampling defect, not a breakdown of
    # counting, and that is only visible on the slice: 52% of the points scored here
    # lie outside the scan mask, against 23% at z = 15694 and 0% below z = 12000.
    # Dropping them takes the slope from 0.465 to 1.184. The figure has to show this,
    # because the published write-up presents this slice as the method catching its
    # own bad case.
    figure_slice(gate, [gate_ray], os.path.join(args.out, 'fig6_gate_slice.png'),
                 f'z = {args.gate_z:.0f}: where the points scored on the refused slice '
                 f'actually are.\nThe scroll is narrower at the top of the fit domain, '
                 f'and the segment meshes run past its edge.')


if __name__ == '__main__':
    main()
