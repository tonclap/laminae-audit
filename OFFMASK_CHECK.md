# Off-mask check on the protocol slices

Asked after the run, of the same slices, and not part of the protocol: what happens to the numbers when every gap with an endpoint outside the scanned volume is dropped. Criterion declared in `offmask_check.py` before running.

## PHerc0139

| scroll | z | gaps | dropped | one run, all | one run, on-scan |
|---|---|---|---|---|---|
| PHerc0139 | 2242 | 333 | 0.0% | 52.0% | **52.0%** |
| PHerc0139 | 3634 | 755 | 0.3% | 52.7% | **52.9%** |
| PHerc0139 | 5026 | 889 | 1.0% | 52.1% | **52.5%** |
| PHerc0139 | 6417 | 894 | 0.2% | 54.0% | **54.0%** |
| PHerc0139 | 7809 | 863 | 0.0% | 45.2% | **45.2%** |

Pooled: 3734 gaps, 0.3% dropped. One run in 51.1% over all gaps and **51.2%** over on-scan gaps, against the run's random baseline of 26.8%.

| windings | gaps | off-scan | one run, all | one run, on-scan | on-scan vs random |
|---|---|---|---|---|---|
| 20–30 | 917 | 0.3% | 56.7% | **56.8%** | 2.12× |
| 30–40 | 1031 | 0.1% | 51.2% | **51.3%** | 1.91× |
| 40–50 | 995 | 0.0% | 44.0% | **44.0%** | 1.64× |
| 50–60 | 791 | 1.1% | 53.2% | **53.7%** | 2.00× |

## PHercParis4

| scroll | z | gaps | dropped | one run, all | one run, on-scan |
|---|---|---|---|---|---|
| PHercParis4 | 4495 | 2858 | 0.7% | 47.9% | **48.1%** |
| PHercParis4 | 7495 | 2860 | 0.0% | 56.7% | **56.7%** |
| PHercParis4 | 10496 | 2870 | 7.0% | 51.9% | **55.1%** |
| PHercParis4 | 13496 | 2856 | 4.0% | 54.0% | **55.9%** |
| PHercParis4 | 16496 | 2866 | 14.7% | 51.2% | **59.0%** |

Pooled: 14310 gaps, 5.3% dropped. One run in 52.3% over all gaps and **54.9%** over on-scan gaps, against the run's random baseline of 32.2%.

| windings | gaps | off-scan | one run, all | one run, on-scan | on-scan vs random |
|---|---|---|---|---|---|
| 10–20 | 1199 | 0.0% | 57.7% | **57.7%** | 1.79× |
| 20–30 | 1200 | 0.0% | 67.3% | **67.3%** | 2.09× |
| 30–40 | 1199 | 0.0% | 67.1% | **67.1%** | 2.08× |
| 40–50 | 1203 | 0.0% | 61.2% | **61.2%** | 1.90× |
| 50–60 | 1200 | 0.0% | 59.2% | **59.2%** | 1.84× |
| 60–70 | 1203 | 0.0% | 57.8% | **57.8%** | 1.80× |
| 70–80 | 1201 | 0.0% | 52.9% | **52.9%** | 1.64× |
| 80–90 | 1205 | 1.7% | 54.4% | **54.8%** | 1.70× |
| 90–100 | 1204 | 7.6% | 49.3% | **51.7%** | 1.61× |
| 100–110 | 1200 | 14.3% | 40.7% | **46.2%** | 1.44× |
| 110–120 | 1200 | 17.3% | 36.9% | **44.2%** | 1.37× |
| 120–130 | 1096 | 23.9% | 21.1% | **26.4%** | 0.82× |

