# CIV-Bench-compute head-to-head results

Items: 56 (40 violated, 16 holds). Proportions carry 95% Wilson score intervals.

## Detection, false alarm, abstention, and soundness

Abstentions are unknown verdicts (the verifier declines to answer within its resource bound). Unsound errors are decisive verdicts that contradict ground truth (a safe verdict on a violated item, or a violated verdict on a safe item); a sound method has zero.

| method | detection rate % [95% CI] | false-alarm rate % [95% CI] | witness validity % | abstain | unsound | mean s/item |
| --- | --- | --- | --- | --- | --- | --- |
| complete verification | 72.5 [57.2, 83.9] (n=40) | 0.0 [0.0, 19.4] (n=16) | 100.0 | 25 | 0 | 6.1840 |
| unit-test suite | 100.0 [91.2, 100.0] (n=40) | 0.0 [0.0, 19.4] (n=16) | 100.0 | 0 | 0 | 0.0025 |
| language-model judge | 100.0 [91.2, 100.0] (n=40) | 0.0 [0.0, 19.4] (n=16) | 100.0 | 0 | 0 | nan |

## Detection by interaction depth (rate % [95% CI])

| method | depth 8 | depth 16 | depth 32 | depth 48 | depth 64 | depth slope (logit) [95% CI] |
| --- | --- | --- | --- | --- | --- | --- |
| complete verification | 100.0 [67.6,100.0] | 100.0 [67.6,100.0] | 100.0 [67.6,100.0] | 62.5 [30.6,86.3] | 0.0 [0.0,32.4] | -1.41 [-392.71, 389.90] |
| unit-test suite | 100.0 [67.6,100.0] | 100.0 [67.6,100.0] | 100.0 [67.6,100.0] | 100.0 [67.6,100.0] | 100.0 [67.6,100.0] | not identified |
| language-model judge | 100.0 [67.6,100.0] | 100.0 [67.6,100.0] | 100.0 [67.6,100.0] | 100.0 [67.6,100.0] | 100.0 [67.6,100.0] | not identified |
