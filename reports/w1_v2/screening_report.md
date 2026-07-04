# Indicator screening report — w1_v2

Candidates: 18 | retained: 18 | observations: 2,978
Eval years: [2010, 2013, 2016, 2019, 2022, 2023]

## Stage 1 — thematic mapping
- Candidates with zero matching rows in this wave: none
- ISO3 codes without World Bank income classification (kept, excluded from income-tier strata): ['ATF', 'CCK', 'GLP', 'KSV', 'MTQ', 'REU', 'UMI', 'VAT']

## Stage 2 — coverage
- Rule: >= 10 countries in at least one eval year
- Excluded as thin: none
- Balanced-coverage subset (>= 5 countries in every income tier): ['AI_Bills', 'AI_Pubs', 'Coursera_Biz', 'Coursera_Tech', 'FWCI', 'WB_GTMI', 'WIPO_Patents']

## Stage 3 — redundancy
- Rule: |Spearman rho| > 0.9 on the 2022 cross-section (fallback: latest shared year)
- no pairs flagged

## Retained indicators

| indicator_id   | theme          |   n_obs |   n_countries |   max_countries_single_year | years                         |   n_HIC |   n_UMC |   n_LMC |   n_LIC |
|:---------------|:---------------|--------:|--------------:|----------------------------:|:------------------------------|--------:|--------:|--------:|--------:|
| AI_Benefits    | Ethics         |      28 |            28 |                          28 | 2023                          |      18 |       9 |       1 |       0 |
| AI_Bills       | Regulation     |     124 |           124 |                         124 | 2023                          |      67 |      32 |      17 |       8 |
| AI_Legis       | Accountability |      80 |            80 |                          80 | 2023                          |      48 |      19 |      10 |       3 |
| AI_Nervous     | Ethics         |      28 |            28 |                          28 | 2023                          |      18 |       9 |       1 |       0 |
| AI_Pubs        | Transparency   |     559 |           171 |                         160 | 2010,2013,2016,2019           |      63 |      45 |      38 |      22 |
| BigData_Biz    | Adoption       |      65 |            34 |                          32 | 2013,2016,2019,2022,2023      |      31 |       3 |       0 |       0 |
| CS_Grad_F      | Fairness       |      81 |            21 |                          21 | 2013,2016,2019,2022           |      20 |       1 |       0 |       0 |
| CS_PhD_F       | Fairness       |      60 |            16 |                          16 | 2013,2016,2019,2022           |      15 |       1 |       0 |       0 |
| Coursera_Biz   | Adoption       |     184 |           119 |                         111 | 2022,2023                     |      53 |      32 |      20 |      10 |
| Coursera_Tech  | Adoption       |      86 |            69 |                          43 | 2022,2023                     |      31 |      23 |       7 |       6 |
| FWCI           | Transparency   |     559 |           171 |                         160 | 2010,2013,2016,2019           |      63 |      45 |      38 |      22 |
| ICT_Sec_All    | Security       |      41 |            33 |                          29 | 2013,2016,2019,2022,2023      |      31 |       2 |       0 |       0 |
| ICT_Sec_ICT    | Security       |      40 |            33 |                          29 | 2013,2016,2019,2022,2023      |      31 |       2 |       0 |       0 |
| Model_Params   | Safety         |      62 |            25 |                          22 | 2010,2013,2016,2019,2022,2023 |      24 |       1 |       0 |       0 |
| Nat_AI_Strat   | Regulation     |      35 |            35 |                          26 | 2019,2022                     |      22 |       6 |       6 |       1 |
| Train_Compute  | Safety         |      58 |            22 |                          19 | 2010,2013,2016,2019,2022,2023 |      20 |       2 |       0 |       0 |
| WB_GTMI        | Adoption       |     198 |           198 |                         198 | 2022                          |      67 |      58 |      47 |      25 |
| WIPO_Patents   | Transparency   |     690 |           115 |                         115 | 2010,2013,2016,2019,2022,2023 |      62 |      35 |      13 |       5 |

## Observations by income tier x theme

| theme          |   HIC |   LIC |   LMC |   UMC |
|:---------------|------:|------:|------:|------:|
| Accountability |    48 |     3 |    10 |    19 |
| Adoption       |   248 |    48 |    87 |   142 |
| Ethics         |    36 |     0 |     2 |    18 |
| Fairness       |   133 |     0 |     0 |     8 |
| Regulation     |    89 |     9 |    23 |    38 |
| Safety         |   111 |     0 |     0 |     9 |
| Security       |    77 |     0 |     0 |     4 |
| Transparency   |   834 |   130 |   298 |   534 |
