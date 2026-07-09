# GAID eval statistics — w1_v2

## Headline category rates (primary threshold ±10%)

| model | n | correct | fabrication | refusal | hedge | misattr. |
|---|---|---|---|---|---|---|
| claude-opus-4-8 | 6658 | 2.2% | 22.8% | 65.2% | 9.0% | 0.8% |
| deepseek-v3-0324 | 6658 | 13.4% | 59.6% | 20.3% | 5.4% | 1.2% |
| glm-5-2 | 6658 | 17.6% | 49.2% | 31.2% | 0.7% | 1.4% |
| gpt-5-4 | 251 | 0.8% | 29.5% | 0.4% | 69.3% | 0.0% |
| gpt-5-5 | 1 | 0.0% | 100.0% | 0.0% | 0.0% | 0.0% |
| grok-4-20 | 6658 | 20.8% | 50.3% | 27.2% | 0.2% | 1.4% |
| grok-4-3 | 6658 | 15.2% | 41.8% | 33.9% | 8.0% | 1.1% |
| llama-4-maverick | 6658 | 7.4% | 28.8% | 58.3% | 5.1% | 0.3% |
| mistral-large-3 | 6658 | 23.5% | 60.1% | 13.9% | 1.2% | 1.4% |
| qwen3-235b-a22b | 6658 | 13.5% | 51.8% | 26.2% | 2.6% | 5.8% |

## Threshold sensitivity (fabrication share)

| model | ±5% | ±10% | ±20% | ±30% |
|---|---|---|---|---|
| claude-opus-4-8 | 23.2% | 22.8% | 21.6% | 20.2% |
| deepseek-v3-0324 | 62.8% | 59.6% | 52.9% | 41.3% |
| glm-5-2 | 52.8% | 49.2% | 42.5% | 32.0% |
| gpt-5-4 | 29.9% | 29.5% | 29.1% | 29.1% |
| gpt-5-5 | 100.0% | 100.0% | 100.0% | 100.0% |
| grok-4-20 | 54.4% | 50.3% | 42.3% | 30.2% |
| grok-4-3 | 43.9% | 41.8% | 37.1% | 28.0% |
| llama-4-maverick | 30.6% | 28.8% | 25.2% | 19.9% |
| mistral-large-3 | 65.3% | 60.1% | 51.9% | 41.6% |
| qwen3-235b-a22b | 54.6% | 51.8% | 46.1% | 36.4% |

## Logistic regression (fabrication ~ magnitude + year + income tier + variant + binary; cluster-robust SEs by ISO3)

- **claude-opus-4-8**: fit failed: LinAlgError: Singular matrix
- **deepseek-v3-0324** (n=4862):
  - `C(income_tier)[T.LIC]` OR=1.2664 (p=0.2035)
  - `C(income_tier)[T.LMC]` OR=0.9512 (p=0.7728)
  - `C(income_tier)[T.UMC]` OR=1.2639 (p=0.0431)*
  - `C(income_tier)[T.UNCLASSIFIED]` OR=1.2374 (p=0.7191)
  - `C(variant)[T.v2_hedged]` OR=8.6691 (p=0.0)***
  - `C(variant)[T.v3_anchored]` OR=0.6425 (p=0.0)***
  - `C(variant)[T.v4_comparative]` OR=0.7236 (p=0.0003)***
  - `C(variant)[T.v5_structured]` OR=1.08 (p=0.8976)
  - `binary[T.True]` OR=0.3153 (p=0.0001)***
  - `log10_magnitude` OR=1.4473 (p=0.0)***
  - `year_c` OR=1.0349 (p=0.0003)***
- **glm-5-2** (n=4442):
  - `C(income_tier)[T.LIC]` OR=0.7127 (p=0.1062)
  - `C(income_tier)[T.LMC]` OR=0.6853 (p=0.0101)*
  - `C(income_tier)[T.UMC]` OR=0.8315 (p=0.2044)
  - `C(income_tier)[T.UNCLASSIFIED]` OR=5.46 (p=0.045)*
  - `C(variant)[T.v2_hedged]` OR=0.8274 (p=0.829)
  - `C(variant)[T.v3_anchored]` OR=0.5531 (p=0.0)***
  - `C(variant)[T.v4_comparative]` OR=0.78 (p=0.0021)**
  - `C(variant)[T.v5_structured]` OR=0.8207 (p=0.6525)
  - `binary[T.True]` OR=0.3882 (p=0.0061)**
  - `log10_magnitude` OR=1.4294 (p=0.0003)***
  - `year_c` OR=1.0156 (p=0.1451)
- **gpt-5-4** (n=76):
  - `C(income_tier)[T.LIC]` OR=1154707151.9598 (p=0.0)***
  - `C(income_tier)[T.LMC]` OR=0.0165 (p=0.0044)**
  - `C(income_tier)[T.UMC]` OR=2085055336.2576 (p=0.0)***
  - `C(income_tier)[T.UNCLASSIFIED]` OR=566.3831 (p=0.0232)*
  - `log10_magnitude` OR=0.2157 (p=0.1387)
  - `year_c` OR=0.7967 (p=0.6539)
- **gpt-5-5**: insufficient variation (n=1)
- **grok-4-20** (n=4739):
  - `C(income_tier)[T.LIC]` OR=1.0623 (p=0.7917)
  - `C(income_tier)[T.LMC]` OR=0.8402 (p=0.1558)
  - `C(income_tier)[T.UMC]` OR=0.812 (p=0.0597)
  - `C(income_tier)[T.UNCLASSIFIED]` OR=1.2069 (p=0.5852)
  - `C(variant)[T.v2_hedged]` OR=0.308 (p=0.1458)
  - `C(variant)[T.v3_anchored]` OR=0.7879 (p=0.0034)**
  - `C(variant)[T.v4_comparative]` OR=1.2265 (p=0.0199)*
  - `C(variant)[T.v5_structured]` OR=2.3538 (p=0.0882)
  - `binary[T.True]` OR=0.169 (p=0.0001)***
  - `log10_magnitude` OR=1.6411 (p=0.0)***
  - `year_c` OR=0.9757 (p=0.0089)**
- **grok-4-3**: fit failed: LinAlgError: Singular matrix
- **llama-4-maverick** (n=2413):
  - `C(income_tier)[T.LIC]` OR=0.9255 (p=0.7343)
  - `C(income_tier)[T.LMC]` OR=0.7392 (p=0.2173)
  - `C(income_tier)[T.UMC]` OR=1.242 (p=0.2674)
  - `C(income_tier)[T.UNCLASSIFIED]` OR=1.8633 (p=0.4189)
  - `C(variant)[T.v2_hedged]` OR=1.1907 (p=0.6268)
  - `C(variant)[T.v3_anchored]` OR=0.6029 (p=0.0025)**
  - `C(variant)[T.v4_comparative]` OR=1.0188 (p=0.9076)
  - `C(variant)[T.v5_structured]` OR=1.0732 (p=0.7464)
  - `binary[T.True]` OR=0.1462 (p=0.0)***
  - `log10_magnitude` OR=1.7849 (p=0.0)***
  - `year_c` OR=1.0734 (p=0.0)***
- **mistral-large-3** (n=5565):
  - `C(income_tier)[T.LIC]` OR=1.0663 (p=0.7544)
  - `C(income_tier)[T.LMC]` OR=0.8829 (p=0.3637)
  - `C(income_tier)[T.UMC]` OR=1.1257 (p=0.2705)
  - `C(income_tier)[T.UNCLASSIFIED]` OR=1.1588 (p=0.7705)
  - `C(variant)[T.v2_hedged]` OR=2.5987 (p=0.0)***
  - `C(variant)[T.v3_anchored]` OR=0.5793 (p=0.0)***
  - `C(variant)[T.v4_comparative]` OR=0.8542 (p=0.055)
  - `C(variant)[T.v5_structured]` OR=0.5366 (p=0.213)
  - `binary[T.True]` OR=1.1683 (p=0.5007)
  - `log10_magnitude` OR=1.6479 (p=0.0)***
  - `year_c` OR=1.0198 (p=0.0272)*
- **qwen3-235b-a22b** (n=4350):
  - `C(income_tier)[T.LIC]` OR=1.0807 (p=0.6968)
  - `C(income_tier)[T.LMC]` OR=1.072 (p=0.5969)
  - `C(income_tier)[T.UMC]` OR=1.0104 (p=0.9249)
  - `C(income_tier)[T.UNCLASSIFIED]` OR=1.9832 (p=0.1711)
  - `C(variant)[T.v2_hedged]` OR=10.4566 (p=0.0008)***
  - `C(variant)[T.v3_anchored]` OR=0.6927 (p=0.0002)***
  - `C(variant)[T.v4_comparative]` OR=0.9278 (p=0.4107)
  - `C(variant)[T.v5_structured]` OR=1.2748 (p=0.5937)
  - `binary[T.True]` OR=0.3893 (p=0.0086)**
  - `log10_magnitude` OR=1.293 (p=0.0)***
  - `year_c` OR=0.9808 (p=0.0473)*

## Scale-invariant error (|log10 model/truth|)

- **claude-opus-4-8**: median 0.7749, within half an order of magnitude 22.8% (n=1474)
- **deepseek-v3-0324**: median 0.1761, within half an order of magnitude 49.9% (n=4044)
- **glm-5-2**: median 0.1308, within half an order of magnitude 54.2% (n=3585)
- **gpt-5-4**: median 2.0603, within half an order of magnitude 4.4% (n=68)
- **grok-4-20**: median 0.1139, within half an order of magnitude 57.1% (n=3869)
- **grok-4-3**: median 0.2102, within half an order of magnitude 47.2% (n=2908)
- **llama-4-maverick**: median 0.1734, within half an order of magnitude 50.1% (n=2081)
- **mistral-large-3**: median 0.1419, within half an order of magnitude 52.8% (n=4579)
- **qwen3-235b-a22b**: median 0.2007, within half an order of magnitude 47.9% (n=3505)

*Full machine-readable output: `stats.json` alongside this file.*
