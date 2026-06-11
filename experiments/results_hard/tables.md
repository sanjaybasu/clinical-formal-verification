# CIV-Bench-hard head-to-head results

Items: 60 (48 violated, 12 holds). Proportions carry 95% Wilson score intervals.

## Detection, false alarm, abstention, and soundness

Abstentions are unknown verdicts (the verifier declines to answer within its resource bound). Unsound errors are decisive verdicts that contradict ground truth (a safe verdict on a violated item, or a violated verdict on a safe item); a sound method has zero.

| method | detection rate % [95% CI] | false-alarm rate % [95% CI] | witness validity % | abstain | unsound | mean s/item |
| --- | --- | --- | --- | --- | --- | --- |
| SMT verification | 100.0 [92.6, 100.0] (n=48) | 0.0 [0.0, 24.2] (n=12) | 100.0 | 0 | 0 | 0.0674 |
| unit-test suite | 25.0 [14.9, 38.8] (n=48) | 0.0 [0.0, 24.2] (n=12) | 100.0 | 0 | 36 | 0.0591 |
| language-model judge | 100.0 [92.6, 100.0] (n=48) | 0.0 [0.0, 24.2] (n=12) | 100.0 | 0 | 0 | nan |

## Detection by interaction depth (rate % [95% CI])

| method | depth 2 | depth 4 | depth 6 | depth 8 | depth 10 | depth 12 | depth slope (logit) [95% CI] |
| --- | --- | --- | --- | --- | --- | --- | --- |
| SMT verification | 100.0 [67.6,100.0] | 100.0 [67.6,100.0] | 100.0 [67.6,100.0] | 100.0 [67.6,100.0] | 100.0 [67.6,100.0] | 100.0 [67.6,100.0] | not identified |
| unit-test suite | 100.0 [67.6,100.0] | 50.0 [21.5,78.5] | 0.0 [0.0,32.4] | 0.0 [0.0,32.4] | 0.0 [0.0,32.4] | 0.0 [0.0,32.4] | -10.71 [-1978.56, 1957.14] |
| language-model judge | 100.0 [67.6,100.0] | 100.0 [67.6,100.0] | 100.0 [67.6,100.0] | 100.0 [67.6,100.0] | 100.0 [67.6,100.0] | 100.0 [67.6,100.0] | not identified |
