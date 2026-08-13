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
- the null control, the adversarial-slice criterion, and the applicability gate were
  proposed by the assistant and accepted by me after seeing them break earlier
  versions of the claim;
- the claim widened once after publication, on 13.08: two slices run to test an
  unrelated question both gave C = +8, so `+1/−2` became `±2`. The correction is a dated
  note in the README rather than an edit of the old numbers;
- the claim narrowed four times before publication, each time from a check rather than
  from second thoughts: `±1` became `+1/−2` after an adversarially chosen slice broke
  it; a validity domain was added when the same slice failed outright; "two independent
  ground truths" became one truth propagated by the spiral fit, once its documented
  input list was read; and "a point gets its exact absolute number" became "lands
  inside an interval 2 to 18 windings wide". Two of the four came from independent
  review passes rather than from the assistant or me;
- no figure in the README is reproduced from memory: `absolute_winding_calibration.py`
  prints all of them, and the expected output is quoted in full.
