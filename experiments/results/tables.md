# CIV-Bench v0 head-to-head results

Items: 324 (216 violated, 108 holds). Proportions carry 95% Wilson score intervals.

## Detection, false alarm, abstention, and soundness

Abstentions are unknown verdicts (the verifier declines to answer within its resource bound). Unsound errors are decisive verdicts that contradict ground truth (a safe verdict on a violated item, or a violated verdict on a safe item); a sound method has zero.

| method | detection rate % [95% CI] | false-alarm rate % [95% CI] | witness validity % | abstain | unsound | mean s/item |
| --- | --- | --- | --- | --- | --- | --- |
| complete verification | 100.0 [98.3, 100.0] (n=216) | 0.0 [0.0, 3.4] (n=108) | 100.0 | 0 | 0 | 0.0057 |
| unit-test suite | 86.6 [81.4, 90.5] (n=216) | 0.0 [0.0, 3.4] (n=108) | 100.0 | 0 | 29 | 0.0058 |
| language-model judge | 100.0 [98.3, 100.0] (n=216) | 0.0 [0.0, 3.4] (n=108) | 100.0 | 0 | 0 | nan |
| NeMo Guardrails | not run in this environment | -- | -- | -- | -- | -- |
| Llama Guard | not run in this environment | -- | -- | -- | -- | -- |

## Detection by interaction depth (rate % [95% CI])

| method | depth 1 | depth 2 | depth 3 | depth 4 | depth 5 | depth 6 | depth 8 | depth 10 | depth 12 | depth slope (logit) [95% CI] |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| complete verification | 100.0 [86.2,100.0] | 100.0 [86.2,100.0] | 100.0 [86.2,100.0] | 100.0 [86.2,100.0] | 100.0 [86.2,100.0] | 100.0 [86.2,100.0] | 100.0 [86.2,100.0] | 100.0 [86.2,100.0] | 100.0 [86.2,100.0] | not identified |
| unit-test suite | 100.0 [86.2,100.0] | 100.0 [86.2,100.0] | 100.0 [86.2,100.0] | 100.0 [86.2,100.0] | 100.0 [86.2,100.0] | 100.0 [86.2,100.0] | 87.5 [69.0,95.7] | 58.3 [38.8,75.5] | 33.3 [18.0,53.3] | -0.81 [-1.09, -0.52] |
| language-model judge | 100.0 [86.2,100.0] | 100.0 [86.2,100.0] | 100.0 [86.2,100.0] | 100.0 [86.2,100.0] | 100.0 [86.2,100.0] | 100.0 [86.2,100.0] | 100.0 [86.2,100.0] | 100.0 [86.2,100.0] | 100.0 [86.2,100.0] | not identified |
| NeMo Guardrails | -- | -- | -- | -- | -- | -- | -- | -- | -- | not run |
| Llama Guard | -- | -- | -- | -- | -- | -- | -- | -- | -- | not run |
