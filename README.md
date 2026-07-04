# GAID Pipeline — Phases 3–4 of the Global AI Dataset (GAID) Project

Living benchmark infrastructure built on the [GAID dataset](https://dataverse.harvard.edu/dataverse/gaidproject)
(Harvard Dataverse). Two coupled deliverables:

- **Phase 3** — an interactive dashboard of national AI profiles for all 227
  countries/territories, hosted at **gaid.aiinsocietyhub.com** (static build,
  design harmonised with [AI in Society](https://aiinsocietyhub.com)).
- **Phase 4** — an automated AI evaluation pipeline that stress-tests frontier
  LLMs against GAID ground truth, quantifying geographic fabrication bias.
  Successor to two published pilots (Apart Research AI Control Hackathon 2026;
  IEEE IRAI 2026), with the peer-review-driven methodology refinements baked in.

## Architecture

```
Harvard Dataverse (gaidproject)          OpenRouter /models + HF org feeds
        │  weekly check                          │  weekly check
        ▼                                        ▼
1. dataverse.py ── new wave? ──┐        release watcher ── new frontier model?
        │                      │                 │
        ▼                      │                 ▼
2. harmonise.py                │        candidate entry in config/models.yaml
   canonical parquet +         │        + notification (flag-and-wait —
   validation + coverage       │          nothing runs without Jason)
        │                      │
        ▼                      ▼
3. eval engine  ◄── config/models.yaml (panel, cutoffs, endpoints)
   queries → responses (cached) → 5-category classifier (multi-threshold,
   scale-aware) → stats (mixed-effects, DiD, PCA, income tiers)
        │
        ▼
4. dashboard build: pre-computed JSON → static site → Hostinger subdomain
```

Two triggers, one engine: a **data trigger** (new GAID wave → delta-evaluate
the active panel) and a **model trigger** (new frontier release → evaluate the
newcomer against the current wave). All paid runs are launched manually with a
budget cap; the pipeline is checkpointed and resumable so free-tier rate
limits just stretch a run over days instead of costing money.

## Usage

```bash
pip install -r requirements.txt

python -m gaid_pipeline check       # is there a newer wave on Dataverse?
python -m gaid_pipeline sync        # download + verify + extract it
python -m gaid_pipeline harmonise   # validate -> data/processed/<tag>/gaid_canonical.parquet
python -m gaid_pipeline status      # what is installed locally
```

Wave detection needs no API key (GAID is public). New waves are found by
enumerating every dataset in the `gaidproject` dataverse and matching the
`gaid_w{wave}_v{version}.zip` naming convention; the highest (wave, version)
wins. Downloads are MD5-verified against Dataverse checksums. The main CSV
inside a wave is located by **schema, not filename**, so renames in future
waves don't break the pipeline; a schema change fails loudly with a diff
report rather than silently producing a wrong benchmark.

## Roadmap

- [x] Dataverse sync module (wave detection, checksum-verified download, manifest)
- [x] Harmonisation layer (canonical schema, validation, per-wave coverage report)
- [ ] Indicator screening as code (thematic mapping, coverage, redundancy) per wave
- [ ] Eval engine: model registry client (OpenRouter free tiers + provider batch),
      response cache, multi-threshold scale-aware classifier, refusal-elicitation
      variant, human-validation harness
- [ ] Stats module: mixed-effects logistic regression, DiD, PCA, World Bank
      income-tier stratification, built-in threshold sensitivity
- [ ] Release watcher (OpenRouter /models + Hugging Face org diff → candidates)
- [ ] Dashboard static build + Hostinger deploy (gaid.aiinsocietyhub.com)
- [ ] GitHub Actions: weekly wave check (free path), manual `workflow_dispatch`
      eval runs (paid path, budget-capped)
