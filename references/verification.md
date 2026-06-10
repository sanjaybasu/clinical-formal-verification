# Citation verification provenance

Every citation in `references.bib` was verified through independent layers before use. This
file records how, so a reader or reviewer can retrace it.

## Layer 1: full-text source verification with adversarial audit

Each citation was assigned to a reader that fetched the primary source (arXiv abstract and
relevant theorem or section, ACL Anthology, proceedings or DOI page, or the official document)
and returned the bibliographic record, a faithful one-paragraph summary, the exact scope and
assumptions, and an explicit statement of what the result does not prove. The six load-bearing
theoretical results were then passed to a second, independent adversarial reader instructed to
find overclaim relative to the source. All six returned a verdict of summary faithful:

- Hallucination is inevitable (Xu, Jain, Kankanhalli)
- Calibrated language models must hallucinate (Kalai, Vempala)
- Evaluating large language models for accuracy incentivizes hallucinations (Kalai, Nachum,
  Vempala, Zhang)
- The parallelism tradeoff, and the expressive power of transformers with chain of thought
  (Merrill, Sabharwal)
- Faith and fate (Dziri et al.)
- Reluplex (Katz et al.)

The summaries, scope statements, and not-proved statements are in `summaries.md`.

## Layer 2: identifier confirmation against the Crossref registry

Every DOI was confirmed against the Crossref API, which returned matching title, authors,
container title, and year for each of:

- 10.1145/3618260.3649777 (STOC 2024)
- 10.1038/s41586-026-10549-w (Nature, published 22 April 2026)
- 10.1007/978-3-031-99965-9_39 (IntelliSys 2025, Springer)
- 10.1162/tacl_a_00562 (TACL 2023)
- 10.1007/978-3-319-63387-9_5 (CAV 2017)
- 10.1090/S0002-9947-1953-0053041-6 (Trans. AMS 1953)
- 10.1145/359104.359106 (CACM 1979)
- 10.1145/242223.242257 (ACM Comput. Surv. 1996)
- 10.1007/978-3-540-78800-3_24 (TACAS 2008)
- 10.18653/v1/2023.emnlp-demo.40 (EMNLP 2023 demo)

The NeurIPS 2023 proceedings DOI for Dziri et al. is not registered with Crossref; that entry
is confirmed through arXiv:2305.18654 and OpenReview id Fkckkr3ya8 instead.

## Layer 3: paperclip full-text repository

A paperclip repository named `clinical-formal-verification` holds the full text of the ten core
arXiv papers and the FDA draft guidance. The FDA lifecycle-management claim is verified against
the document text with line-level evidence (lines 29, 67, 398-403): the total product lifecycle
approach, the predetermined change control plan, and post-market performance monitoring. Stable
citation links use the form `https://citations.gxl.ai/{papers,fda}/<doc_id>#L<n>`. Document ids:

| reference | paperclip id |
| --- | --- |
| Xu, Jain, Kankanhalli | arx_2401.11817 |
| Kalai, Nachum, Vempala, Zhang (preprint) | arx_2509.04664 |
| Kalai, Vempala (calibrated) | arx_2311.14648 |
| Merrill, Sabharwal (parallelism tradeoff) | arx_2207.00729 |
| Merrill, Sabharwal (chain of thought) | arx_2310.07923 |
| Dziri et al. (faith and fate) | arx_2305.18654 |
| Katz et al. (Reluplex) | arx_1702.01135 |
| Hackett et al. (guardrail bypass) | arx_2504.11168 |
| Inan et al. (Llama Guard) | arx_2312.06674 |
| Rebedea et al. (NeMo Guardrails) | arx_2310.10501 |
| FDA AI-enabled device software functions (draft) | fda_c22512aba681 |

## Corrections applied during verification

- The Kalai, Nachum, Vempala, Zhang preprint "Why language models hallucinate" (arXiv:2509.04664)
  is superseded by the peer-reviewed Nature article "Evaluating large language models for
  accuracy incentivizes hallucinations" (2026); the Nature version is cited.
- Banerjee et al. (arXiv:2409.05746) is superseded by the peer-reviewed IntelliSys 2025
  proceedings chapter; it is cited as supporting only, given its informal halting-style
  reductions and contested framing.
- There is no single standalone FDA generative-AI assurance guidance. The FDA draft guidance on
  AI-enabled device software functions, the FDA final guidance on predetermined change control
  plans, and the Coalition for Health AI assurance-lab framework are cited as the distinct
  documents they are. The assurance-lab concept is attributed to the Coalition for Health AI,
  not to the FDA.
- For the deployed guardrail baseline, the original Llama Guard (arXiv:2312.06674) is cited for
  method and lineage, and Llama Guard 4 (April 2025) is cited as the current version used.
