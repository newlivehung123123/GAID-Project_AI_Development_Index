# GAID AI Development Index

Code, configuration and reference data that build the **GAID AI Development
Index**, a six-pillar composite index of national artificial intelligence
development for 227 countries and territories, published at
**[gaid.aiinsocietyhub.com](https://gaid.aiinsocietyhub.com/)**.

The index is computed from the **Global AI Dataset (GAID) Project, wave 1,
version 2**, deposited at Harvard Dataverse under
[doi:10.7910/DVN/PUMGYU](https://doi.org/10.7910/DVN/PUMGYU). This repository
contains no primary data. The pipeline downloads the deposited wave from
Dataverse, verifies it against the published MD5 checksum, and rebuilds every
published score from it.

Everything below is deterministic. Running the five commands in
[Reproduce the index](#reproduce-the-index) on the same wave reproduces the
scores on the website and in the accompanying paper, bit for bit.

---

## Contents

- [What the index measures](#what-the-index-measures)
- [Requirements](#requirements)
- [Reproduce the index](#reproduce-the-index)
- [Step by step, with expected output](#step-by-step-with-expected-output)
- [Method](#method)
- [Validation](#validation)
- [Verify against the published scores](#verify-against-the-published-scores)
- [Known defect in pillar one, edition 2025](#known-defect-in-pillar-one-edition-2025)
- [Rebuild the website](#rebuild-the-website)
- [Rebuild the paper figures](#rebuild-the-paper-figures)
- [Repository layout](#repository-layout)
- [The model evaluation pipeline](#the-model-evaluation-pipeline)
- [Citation](#citation)
- [Licence](#licence)

---

## What the index measures

Six pillars, 22 components, defined in full in
[`config/indices.yaml`](config/indices.yaml). That file is the single source of
truth. No weight, threshold or metric name is hardcoded in Python.

| Pillar | Name | Components |
|---|---|---|
| P1 | Research and Innovation | AI publications, field-weighted citation impact, AI patent publications, responsible AI papers |
| P2 | Talent and Skills | AI talent concentration, relative AI skill penetration, AI job postings |
| P3 | Governance and Regulation | four World Bank GovTech sub-indices, AI bills passed into law, AI mentions in legislative proceedings |
| P4 | AI Economy and Investment | cumulative private AI investment, newly funded AI companies |
| P5 | Infrastructure and Compute | national aggregate peak compute, total training compute |
| P6 | Responsible AI and Society | three GIRAI dimension scores, public attitudes to AI, business ICT security incidents (inverted) |

The overall index is the mean of the pillar scores. A secondary **readiness
lens** averages P2, P3 and P5. Composite indices ingested from Tortoise Media
and from the Global Index on Responsible AI are never used as components. They
are held out and used only to test convergent validity.

---

## Requirements

- Python 3.11 or later. Developed and published on 3.13.5
- No API key. The GAID deposit is public and Dataverse needs no credentials
- Roughly 700 MB of free disk space for the downloaded wave and the derived
  parquet files
- Network access to `dataverse.harvard.edu`

```bash
git clone https://github.com/newlivehung123123/GAID-Project_AI_Development_Index.git
cd GAID-Project_AI_Development_Index
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Versions used for the published build: pandas 2.2.3, pyarrow 20.0.0,
numpy 2.1.3, scipy 1.15.3, matplotlib 3.10.0.

---

## Reproduce the index

```bash
python -m gaid_pipeline sync        # download + checksum-verify wave 1 v2 from Dataverse
python -m gaid_pipeline harmonise   # -> data/processed/w1_v2/gaid_canonical.parquet
python -m gaid_pipeline indices     # -> data/processed/w1_v2/indices.parquet
python -m gaid_pipeline site-data   # -> site/data/*.json, the numbers the website serves
python -m gaid_pipeline site-build  # -> site/dist, the 230-page static site
```

`sync` and `harmonise` take a few minutes. `indices` takes seconds. Nothing in
this path spends money or calls a language model.

---

## Step by step, with expected output

### 1. Check what is on Dataverse

```bash
python -m gaid_pipeline check
```

Enumerates every dataset in the `gaidproject` dataverse, matches the
`gaid_w{wave}_v{version}.zip` naming convention and reports the highest
(wave, version) pair against what is installed locally. Exits without
downloading anything.

### 2. Download the wave

```bash
python -m gaid_pipeline sync
```

Downloads the archive, verifies the MD5 against the checksum Dataverse
publishes, extracts to `data/wave/w1_v2/` and writes `data/manifest.json`
recording the dataset DOI, the dataset version, the filename and the checksum.
A mismatched checksum aborts the run.

Use `--force` to re-download a wave that is already installed.

### 3. Harmonise into the canonical panel

```bash
python -m gaid_pipeline harmonise
```

Validates the extracted wave against the expected schema and writes
`data/processed/w1_v2/gaid_canonical.parquet`, a long-format panel with one row
per country, metric, year and source.

The main CSV inside a wave is located **by schema, not by filename**, so a
rename in a future wave does not break the pipeline. A genuine schema change
fails loudly with a printed diff rather than silently producing a wrong index.

### 4. Build the index

```bash
python -m gaid_pipeline indices
```

Reads `config/indices.yaml`, computes every edition, and writes
`data/processed/w1_v2/indices.parquet` plus the audit report
[`reports/w1_v2/index_report.md`](reports/w1_v2/index_report.md).

The report prints, per edition: the component coverage table, the group-level
Cronbach's alpha for every multi-component facet, the equal-weight against
PC1-weight comparison, the three normalisation variants, and the Spearman
correlations against the held-out external indices.

### 5. Export the site data and build the site

```bash
python -m gaid_pipeline site-data
python -m gaid_pipeline site-build
```

`site-data` writes `site/data/indices.json`, `site/data/meta.json` and one JSON
file per country under `site/data/countries/`. These are the exact numbers the
live website serves. `site-build` renders them into `site/dist`, a static site
of 230 pages including the choropleth home page, the full ranking table, the
methodology page and 227 country profiles.

`python -m gaid_pipeline status` prints the installed manifest at any point.

---

## Method

Set in [`config/indices.yaml`](config/indices.yaml). The steps below are the
whole method. There is nothing else.

**Editions and vintage.** For edition year Y, each component contributes its
latest observation inside the window (Y − 3, Y]. The year of observation is
recorded separately from the year of publication, so a 2025 report carrying
2023 measurements is treated as a 2023 observation. The three-year lookback
stops the cross-vintage mixing that an earlier dimensionality audit caught,
where 2019 publication counts sat beside 2024 patent counts in one score.

**Normalisation.** Components flagged `log: true` are transformed with `log1p`.
Every component is then winsorised at the 1st and 99th percentiles and rescaled
min-max to 0 to 100 within the edition. A component with `direction: -1` is
inverted, so higher always means more developed. A component observed for at
least three countries but holding the same value for all of them has no
dispersion to rescale, and every country then receives the midpoint of 50.

**Aggregation.** Nested equal weights. Components are averaged within their
facet group, then the groups are averaged to give the pillar. Components that
proved near-orthogonal are deliberately kept as separate facet groups rather
than averaged as if they measured one construct. P2 is the worked example, with
talent concentration and skill penetration at a group-level alpha of 0.05.

**Coverage gates.** A pillar is scored only when at least half its components
are present, `min_component_share: 0.5`. A country receives an overall score
only when at least four of the six pillars are scored, `min_pillars_for_overall: 4`.
Countries below either gate are reported as unscored rather than imputed.

**Weights.** Equal weights throughout. Principal component analysis is run as a
check, never as a weighting scheme. The index is formative, so components are
defining features of AI development rather than interchangeable symptoms of it,
and a data-driven weight would change what the index means every edition.

---

## Validation

Every check below runs inside `python -m gaid_pipeline indices` and is printed
in `reports/w1_v2/index_report.md`.

- **Internal consistency.** Cronbach's alpha for every facet group holding two
  or more components
- **Weighting sensitivity.** Equal-weight scores against PC1-weighted scores,
  from a singular value decomposition of the standardised component matrix
- **Normalisation sensitivity.** The headline min-max scores against a z-score
  variant, scaled ×15 + 50, and a percentile-rank variant
- **Convergent validity.** Spearman rank correlations against held-out indices
  that are ingested in GAID but never used as components, from Tortoise Media
  and from the Global Index on Responsible AI. The P6 comparison is flagged in
  the config as partially circular, because GIRAI dimension scores are P6
  components

---

## Verify against the published scores

`data/processed/w1_v2/indices.parquet` is committed, so the published scores
can be inspected without downloading or rebuilding anything.

```python
import pandas as pd
idx = pd.read_parquet("data/processed/w1_v2/indices.parquet")
print(idx[idx.edition == 2025].nlargest(10, "GAID_AI_Development_Index"))
```

To confirm a rebuild matches the published numbers, rebuild and compare:

```bash
python -m gaid_pipeline sync && python -m gaid_pipeline harmonise
python -m gaid_pipeline indices
git diff --stat data/processed/w1_v2/indices.parquet
```

An empty diff means the rebuild reproduced the published index exactly.

---

## Known defect in pillar one, edition 2025

Pillar one is degraded in the 2025 edition and this is disclosed rather than
silently patched.

- The two publication components draw on a series that ends in 2019, so neither
  has an observation inside the three-year window
- The patent component has an observation for 115 countries, but the source
  reports a value of zero for every country in 2023 and 2024. That is a
  reporting lag recorded as a zero rather than as a missing value. The component
  therefore has no dispersion and normalises to the constant 50

Pillar one in the 2025 edition is consequently the mean of that constant and one
normalised component, which is why it runs from 25.0 to 75.0 and no wider. In
the 2024 edition the pillar falls below the coverage gate and is not published.

Removing pillar one moves the ranking very little. Overall scores computed
without it correlate with the published overall scores at Spearman rho = 0.99
across the 50 countries that still clear the four-pillar gate, the median
country moves one place, and only one country moves more than five places.
Pillar one still matters for coverage, because 15 of the 65 scored countries
clear the four-pillar gate only by counting it. The published scores retain the
pillar for that reason.

Users for whom research capacity is the construct of interest should set pillar
one aside and go to the underlying publication and citation series directly.

---

## Rebuild the website

`site/dist` is the generated static site and `gaid-site-upload/` is the copy
deployed to the subdomain document root. Both are committed so the published
state is inspectable without a build.

```bash
python -m gaid_pipeline site-data
python -m gaid_pipeline site-build
python3 -m http.server 8000 --directory site/dist   # then open localhost:8000
```

---

## Rebuild the paper figures

The four figures in the accompanying paper are built from the same canonical
panel and index config, in black and white.

```bash
python -m gaid_pipeline indices     # figures read indices + the canonical panel
python paper/make_figures.py        # -> paper/figures/figure{1,2,3,4}.png
```

`paper/figure_audit.py` is a bounding-box overlap check. `make_figures.py` calls
it on every figure and raises if any two text or patch elements collide, so a
figure cannot be committed with overlapping labels.

---

## Repository layout

```
gaid_pipeline/          the pipeline package
  dataverse.py            wave detection, checksum-verified download, manifest
  harmonise.py            schema validation -> canonical panel
  screening.py            indicator screening (parallel branch, not in the index path)
  indices.py              composite index construction + the validation suite
  dashboard_data.py       canonical + indices -> static JSON
  site_build.py           static JSON -> 230-page site
  geo.py                  World Bank country reference and income tiers
  queries.py classify.py client.py results.py stats.py validate.py watch.py
                          the model evaluation pipeline, separate from the index
config/
  indices.yaml            pillars, components, normalisation, gates, validation
  indicators.yaml         indicator screening definitions
  models.yaml prompts.yaml  model evaluation panel and prompts
data/
  manifest.json           which wave is installed, with DOI and checksum
  reference/              World Bank country and income reference, world geometry
  processed/w1_v2/
    indices.parquet       the published index, committed
    (other parquet files are regenerated by the pipeline and not committed)
reports/w1_v2/
  index_report.md         coverage, alpha, PCA check, sensitivity, convergent validity
  screening_report.md     indicator screening output
  wave_report.md          harmonisation and coverage for the installed wave
site/                     static site source and build output
gaid-site-upload/         the copy deployed to gaid.aiinsocietyhub.com
paper/                    figure scripts and the figures for the accompanying paper
tests/                    unit tests
```

Large regenerated artefacts are deliberately not committed. `data/raw/`,
`data/wave/`, `data/eval/` and the bulky parquet files under `data/processed/`
are all rebuilt from the Dataverse deposit by `sync` and `harmonise`.

---

## The model evaluation pipeline

The same repository holds a separate pipeline that tests large language models
against GAID ground truth. It shares the canonical panel but has no part in
building the index, and none of its commands are needed to reproduce any
published score.

```bash
python -m gaid_pipeline screen            # indicator screening
python -m gaid_pipeline queries           # versioned query set
python -m gaid_pipeline run-eval --model <id> --dry-run --limit 400   # $0, synthetic
python -m gaid_pipeline classify --dry-run
python -m gaid_pipeline stats
```

Live runs need an OpenRouter key in a gitignored `.env` file as
`OPENROUTER_API_KEY=...`, are capped by `--budget`, are cached and resumable,
and are launched manually. The dry-run path costs nothing, uses a separate
cache and exercises the whole chain.

---

## Citation

Cite the dataset and the index separately.

**Dataset**

> Hung, J. (2026). Global AI Dataset (GAID) Project, wave 1, version 2 [Data set].
> Harvard Dataverse. https://doi.org/10.7910/DVN/PUMGYU

**Index and code**

> Hung, J., & Grossman, N. (2026). GAID AI Development Index [Computer software].
> https://github.com/newlivehung123123/GAID-Project_AI_Development_Index

See [`CITATION.cff`](CITATION.cff) for the machine-readable form.

---

## Licence

MIT. See [LICENSE](LICENSE).

The GAID dataset itself is distributed under the licence stated on its Harvard
Dataverse record. Third-party sources aggregated in GAID keep their own terms,
which are recorded per observation in the deposited panel.
