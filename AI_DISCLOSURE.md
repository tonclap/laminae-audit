# AI disclosure

Required by the Vesuvius Challenge submission policy, and stated here in the form the
neighbouring community projects use.

The experimental decisions and the choice of what to claim are mine. The code, the
measurements and the English drafting were produced with an AI assistant (Claude,
Anthropic) working from my instructions in an agentic loop; I directed the work and
reviewed everything reported here.

Specifically, so that a reader can weigh it:

- the assistant wrote the streaming zarr reader, the counting code and the statistics,
  and ran every measurement quoted in this repository;
- the null control and the adversarial-slice criterion were proposed by the assistant
  and accepted by me after seeing them break earlier versions of the claim;
- **the largest correction came the same way.** This repository was published on
  12 August as a winding calibration. Measurement on 13–14 August withdrew the
  applicability gate, withdrew "the error is an offset, not a drift", and narrowed the
  constant to a domain — and then showed the mechanism underneath, which is now the
  subject of the repository. Each of those was a measurement with a baseline beside it,
  not a change of mind. The record is in `CORRECTION.md`; the history was kept public
  rather than rewritten, and the repository was renamed rather than replaced;
- the pre-registration in `protocol_run.py` — five heights per scroll fixed by
  quantiles of the data, 24 rays, every height published whatever it says — was written
  and committed before the run it describes, because the previous version of this work
  had been vulnerable to slice picking;
- no figure in this README is reproduced from memory or typed by hand: `protocol_run.py`
  writes one JSON per slice and `protocol_summary.py` and `offmask_check.py` read those
  into the published tables. That rule exists because three rows of the *original*
  results table turned out to have come from a script that was never shipped — see
  `CORRECTION.md`, item 5.
