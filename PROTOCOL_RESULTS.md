# Pre-registered protocol run — results

Five equidistant quantiles of each scroll's labelled z-extent, 24 rays each, every height published, a baseline beside every number. Protocol fixed before the run: `protocol_run.py`. Numbers below are read off the slices it wrote, by `protocol_summary.py`.

## Every slice

| scroll | z | segments | gaps | 0 | **1** | 2 | 3+ | random "1" (p95) |
|---|---|---|---|---|---|---|---|---|
| PHerc0139 | 2242 | 14/37 | 333 | 27.3% | **52.0%** | 13.2% | 7.5% | 27.2% (p95 30.6%) |
| PHerc0139 | 3634 | 31/37 | 755 | 30.7% | **52.7%** | 13.9% | 2.6% | 26.2% (p95 28.5%) |
| PHerc0139 | 5026 | 35/37 | 889 | 31.9% | **52.1%** | 12.7% | 3.3% | 27.5% (p95 29.9%) |
| PHerc0139 | 6417 | 35/37 | 894 | 31.8% | **54.0%** | 12.8% | 1.5% | 27.1% (p95 29.4%) |
| PHerc0139 | 7809 | 34/37 | 863 | 38.8% | **45.2%** | 12.5% | 3.5% | 26.2% (p95 28.3%) |
| PHercParis4 | 4495 | 28/28 | 2858 | 30.8% | **47.9%** | 16.1% | 5.2% | 31.5% (p95 33.0%) |
| PHercParis4 | 7495 | 28/28 | 2860 | 23.0% | **56.7%** | 17.1% | 3.2% | 32.1% (p95 33.5%) |
| PHercParis4 | 10496 | 28/28 | 2870 | 25.9% | **51.9%** | 16.9% | 5.3% | 32.1% (p95 33.5%) |
| PHercParis4 | 13496 | 28/28 | 2856 | 22.5% | **54.0%** | 20.6% | 2.9% | 33.1% (p95 34.6%) |
| PHercParis4 | 16496 | 28/28 | 2866 | 31.3% | **51.2%** | 15.6% | 1.9% | 32.1% (p95 33.3%) |

The **1** column is the measurement: the share of gaps between two neighbouring labelled sheets holding exactly one run of prediction. A prediction that resolved exactly the labelled sheets would put 100% there. The random column places the same number of runs along the same stretch of ray.

## PHerc0139 by winding, pooled over the five heights

3734 gaps; one run in **51.1%** against a random 26.8% — **1.90×**.

| windings | gaps | 0 | **1** | 2 | 3+ | vs random |
|---|---|---|---|---|---|---|
| 20–30 | 917 | 28.8% | **56.7%** | 13.6% | 0.9% | 2.11× |
| 30–40 | 1031 | 32.5% | **51.2%** | 11.5% | 4.8% | 1.91× |
| 40–50 | 995 | 36.7% | **44.0%** | 15.1% | 4.2% | 1.64× |
| 50–60 | 791 | 33.1% | **53.2%** | 11.4% | 2.3% | 1.98× |

Detection, pooled, in voxels either side of a labelled sheet (neighbouring sheets are ~22–26 vx apart):

| | ±1 | ±2 | ±3 | ±5 | ±8 | ±11 |
|---|---|---|---|---|---|---|
| mask on near a labelled sheet | 32.3% | 42.4% | 52.7% | 69.0% | 83.7% | 90.9% |
| same question at random radii | 23.0% | 31.9% | 41.5% | 58.3% | 76.0% | 85.0% |

## PHercParis4 by winding, pooled over the five heights

14310 gaps; one run in **52.3%** against a random 32.2% — **1.63×**.

| windings | gaps | 0 | **1** | 2 | 3+ | vs random |
|---|---|---|---|---|---|---|
| 10–20 | 1199 | 24.0% | **57.7%** | 16.4% | 1.8% | 1.79× |
| 20–30 | 1200 | 16.4% | **67.3%** | 15.3% | 0.9% | 2.09× |
| 30–40 | 1199 | 17.0% | **67.1%** | 14.5% | 1.4% | 2.08× |
| 40–50 | 1203 | 24.7% | **61.2%** | 12.2% | 1.9% | 1.90× |
| 50–60 | 1200 | 22.5% | **59.2%** | 14.9% | 3.4% | 1.84× |
| 60–70 | 1203 | 23.2% | **57.8%** | 15.8% | 3.2% | 1.80× |
| 70–80 | 1201 | 21.3% | **52.9%** | 21.3% | 4.5% | 1.64× |
| 80–90 | 1205 | 20.5% | **54.4%** | 20.0% | 5.1% | 1.69× |
| 90–100 | 1204 | 26.7% | **49.3%** | 19.4% | 4.5% | 1.53× |
| 100–110 | 1200 | 40.3% | **40.7%** | 15.8% | 3.2% | 1.26× |
| 110–120 | 1200 | 29.6% | **36.9%** | 25.0% | 8.5% | 1.15× |
| 120–130 | 1096 | 56.8% | **21.1%** | 15.9% | 6.2% | 0.66× |

Detection, pooled, in voxels either side of a labelled sheet (neighbouring sheets are ~22–26 vx apart):

| | ±1 | ±2 | ±3 | ±5 | ±8 | ±11 |
|---|---|---|---|---|---|---|
| mask on near a labelled sheet | 43.1% | 53.6% | 62.3% | 74.7% | 84.0% | 88.4% |
| same question at random radii | 37.0% | 46.1% | 54.9% | 68.4% | 79.4% | 85.2% |

