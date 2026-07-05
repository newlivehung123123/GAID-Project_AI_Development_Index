# GAID composite index report — w1_v2, edition 2025

Normalisation: log1p (flagged) -> winsorise [0.01, 0.99] -> min-max within edition. Weights: nested equal. Lookback: 3 years.

## Coverage (latest edition)

| id                        |   countries |
|:--------------------------|------------:|
| GAID_AI_Development_Index |          65 |
| P1                        |          70 |
| P2                        |          48 |
| P3                        |         197 |
| P4                        |          91 |
| P5                        |          34 |
| P6                        |         136 |
| readiness                 |          55 |

## Top 15 — GAID_AI_Development_Index (edition 2025)

| ISO3   |   score |
|:-------|--------:|
| USA    |   77.91 |
| CHN    |   73.38 |
| GBR    |   63.5  |
| SGP    |   63.08 |
| IND    |   60.77 |
| JPN    |   60.46 |
| KOR    |   60.1  |
| DEU    |   57.24 |
| CAN    |   57.16 |
| CHE    |   55.64 |
| FRA    |   55.58 |
| ARE    |   53.29 |
| ITA    |   53.21 |
| ISR    |   52.48 |
| AUS    |   51.9  |

## Dimensionality audit — edition 2025

| pillar   | name                     |   k_active |   alpha_pillar(info) |   n | group_alphas(test)                            |   rho_equal_vs_pca |
|:---------|:-------------------------|-----------:|---------------------:|----:|:----------------------------------------------|-------------------:|
| P1       | Research & Innovation    |          2 |                 0    |  70 | single-component groups                       |            nan     |
| P2       | Talent & Skills          |          3 |                 0.58 |  21 | talent_stock=0.05 (n=48)                      |              0.965 |
| P3       | Governance & Regulation  |          6 |                 0.83 |  63 | govtech=0.96 (n=197), legislation=0.39 (n=68) |              0.953 |
| P4       | AI Economy & Investment  |          2 |                 0.93 |  91 | single-component groups                       |              1     |
| P5       | Infrastructure & Compute |          2 |                 0.53 |  24 | compute=0.53 (n=24)                           |              0.997 |
| P6       | Responsible AI & Society |          5 |                 0.25 |  12 | girai=0.96 (n=136)                            |              0.986 |

## Dimensionality audit — benchmark edition 2019 (fullest P1 form)

| pillar   | name                     |   k_active |   alpha_pillar(info) |   n | group_alphas(test)       |   rho_equal_vs_pca |
|:---------|:-------------------------|-----------:|---------------------:|----:|:-------------------------|-------------------:|
| P1       | Research & Innovation    |          3 |                  0.7 | 104 | publications=0.5 (n=173) |              0.995 |
| P2       | Talent & Skills          |          1 |                nan   |  14 | single-component groups  |            nan     |
| P3       | Governance & Regulation  |          0 |                nan   |   0 | single-component groups  |            nan     |
| P4       | AI Economy & Investment  |          0 |                nan   |   0 | single-component groups  |            nan     |
| P5       | Infrastructure & Compute |          2 |                nan   |   6 | compute=None (n=6)       |            nan     |
| P6       | Responsible AI & Society |          1 |                nan   |  33 | single-component groups  |            nan     |

Interpretation: pillars are FORMATIVE composites (OECD/JRC handbook) — internal consistency (alpha >= 0.7) is required within reflective groups, shown in group_alphas; pillar-level alpha is informational only. rho_equal_vs_pca near 1 means equal and PCA weighting produce the same ordering (equal weights defensible).

## Cross-pillar correlations (Spearman)

|    |   P1 |   P2 |    P3 |   P4 |    P5 |   P6 |
|:---|-----:|-----:|------:|-----:|------:|-----:|
| P1 | 1    | 0.75 |  0.27 | 0.84 |  0.25 | 0.26 |
| P2 | 0.75 | 1    |  0.22 | 0.78 |  0.09 | 0.06 |
| P3 | 0.27 | 0.22 |  1    | 0.36 | -0.02 | 0.67 |
| P4 | 0.84 | 0.78 |  0.36 | 1    |  0.27 | 0.58 |
| P5 | 0.25 | 0.09 | -0.02 | 0.27 |  1    | 0.23 |
| P6 | 0.26 | 0.06 |  0.67 | 0.58 |  0.23 | 1    |

## Normalisation sensitivity (Spearman vs headline min-max)

|    |   zscore |   percentile |
|:---|---------:|-------------:|
| P1 |    1     |        1     |
| P2 |    0.988 |        0.956 |
| P3 |    0.951 |        0.93  |
| P4 |    1     |        0.997 |
| P5 |    0.954 |        0.918 |
| P6 |    0.98  |        0.951 |

## Convergent validity vs held-out external indices

| ours    | theirs                                   |   n |      rho | note                                                          |
|:--------|:-----------------------------------------|----:|---------:|:--------------------------------------------------------------|
| overall | AI Index: Overall Score                  |  62 | 0.821965 |                                                               |
| P1      | AI Index: Research Score                 |  64 | 0.757854 |                                                               |
| P2      | AI Index: Talent Score                   |  45 | 0.836288 |                                                               |
| P3      | AI Index: Government Strategy Score      |  82 | 0.390511 |                                                               |
| P4      | AI Index: Commercial Score               |  71 | 0.732411 |                                                               |
| P5      | AI Index: Infrastructure Score           |  34 | 0.315105 |                                                               |
| P6      | The Global Index on Responsible AI Score | 136 | 0.941959 | partially circular — GIRAI dimension scores are P6 components |
