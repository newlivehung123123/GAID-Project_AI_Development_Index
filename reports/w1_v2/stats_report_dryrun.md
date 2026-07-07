# GAID eval statistics — w1_v2 (DRY RUN — synthetic responses)

## Headline category rates (primary threshold ±10%)

| model | n | correct | fabrication | refusal | hedge | misattr. |
|---|---|---|---|---|---|---|
| deepseek-v3-0324 | 6658 | 11.3% | 16.7% | 58.6% | 13.4% | 0.0% |
| llama-4-maverick | 6658 | 11.6% | 16.8% | 58.6% | 13.0% | 0.0% |
| mistral-large-3 | 6658 | 11.7% | 17.2% | 58.5% | 12.5% | 0.0% |
| qwen3-235b-a22b | 6658 | 11.2% | 16.2% | 59.9% | 12.7% | 0.0% |

## Threshold sensitivity (fabrication share)

| model | ±5% | ±10% | ±20% | ±30% |
|---|---|---|---|---|
| deepseek-v3-0324 | 20.2% | 16.7% | 9.7% | 3.1% |
| llama-4-maverick | 20.0% | 16.8% | 9.6% | 3.3% |
| mistral-large-3 | 20.3% | 17.2% | 10.9% | 3.7% |
| qwen3-235b-a22b | 19.4% | 16.2% | 9.5% | 3.1% |

## Logistic regression (fabrication ~ magnitude + year + income tier + variant + binary; cluster-robust SEs by ISO3)

- **deepseek-v3-0324** (n=1863):
  - `C(income_tier)[T.LIC]` OR=0.9212 (p=0.7847)
  - `C(income_tier)[T.LMC]` OR=0.8898 (p=0.5224)
  - `C(income_tier)[T.UMC]` OR=0.6853 (p=0.0131)*
  - `C(income_tier)[T.UNCLASSIFIED]` OR=0.8988 (p=0.8468)
  - `C(variant)[T.v2_hedged]` OR=0.7274 (p=0.0341)*
  - `C(variant)[T.v3_anchored]` OR=0.8843 (p=0.4495)
  - `C(variant)[T.v4_comparative]` OR=0.7648 (p=0.0461)*
  - `C(variant)[T.v5_structured]` OR=0.8797 (p=0.3471)
  - `binary[T.True]` OR=1.6009 (p=0.7168)
  - `log10_magnitude` OR=1.0369 (p=0.0511)
  - `year_c` OR=0.965 (p=0.0019)**
- **llama-4-maverick** (n=1890):
  - `C(income_tier)[T.LIC]` OR=0.6538 (p=0.097)
  - `C(income_tier)[T.LMC]` OR=0.857 (p=0.3136)
  - `C(income_tier)[T.UMC]` OR=0.6701 (p=0.0033)**
  - `C(income_tier)[T.UNCLASSIFIED]` OR=1.4841 (p=0.6319)
  - `C(variant)[T.v2_hedged]` OR=0.9471 (p=0.7212)
  - `C(variant)[T.v3_anchored]` OR=0.8697 (p=0.3747)
  - `C(variant)[T.v4_comparative]` OR=0.8989 (p=0.4571)
  - `C(variant)[T.v5_structured]` OR=0.9703 (p=0.7879)
  - `binary[T.True]` OR=1.0935 (p=0.9203)
  - `log10_magnitude` OR=1.0606 (p=0.0007)***
  - `year_c` OR=0.973 (p=0.0151)*
- **mistral-large-3** (n=1929):
  - `C(income_tier)[T.LIC]` OR=0.6795 (p=0.0784)
  - `C(income_tier)[T.LMC]` OR=0.7448 (p=0.1175)
  - `C(income_tier)[T.UMC]` OR=0.7535 (p=0.046)*
  - `C(income_tier)[T.UNCLASSIFIED]` OR=1.1828 (p=0.7864)
  - `C(variant)[T.v2_hedged]` OR=1.1145 (p=0.4472)
  - `C(variant)[T.v3_anchored]` OR=1.09 (p=0.5966)
  - `C(variant)[T.v4_comparative]` OR=0.9492 (p=0.719)
  - `C(variant)[T.v5_structured]` OR=1.0937 (p=0.4579)
  - `binary[T.True]` OR=1.7414 (p=0.5349)
  - `log10_magnitude` OR=1.0312 (p=0.2674)
  - `year_c` OR=0.958 (p=0.0004)***
- **qwen3-235b-a22b** (n=1824):
  - `C(income_tier)[T.LIC]` OR=0.725 (p=0.115)
  - `C(income_tier)[T.LMC]` OR=0.6611 (p=0.0059)**
  - `C(income_tier)[T.UMC]` OR=0.7108 (p=0.0073)**
  - `C(income_tier)[T.UNCLASSIFIED]` OR=1.45 (p=0.3537)
  - `C(variant)[T.v2_hedged]` OR=1.0159 (p=0.9168)
  - `C(variant)[T.v3_anchored]` OR=0.8969 (p=0.5274)
  - `C(variant)[T.v4_comparative]` OR=0.9323 (p=0.649)
  - `C(variant)[T.v5_structured]` OR=1.2702 (p=0.0528)
  - `binary[T.True]` OR=3.9991 (p=0.1994)
  - `log10_magnitude` OR=1.0771 (p=0.0019)**
  - `year_c` OR=0.9611 (p=0.0005)***

## Scale-invariant error (|log10 model/truth|)

- **deepseek-v3-0324**: median 0.0754, within half an order of magnitude 99.9% (n=1549)
- **llama-4-maverick**: median 0.0738, within half an order of magnitude 100.0% (n=1573)
- **mistral-large-3**: median 0.0792, within half an order of magnitude 99.9% (n=1596)
- **qwen3-235b-a22b**: median 0.0724, within half an order of magnitude 100.0% (n=1527)

*Full machine-readable output: `stats.json` alongside this file.*
