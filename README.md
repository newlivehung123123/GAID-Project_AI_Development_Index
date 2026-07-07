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
Harvard Dataverse (gaidproject)          OpenRouter /models + Hugging Face orgs
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
python -m gaid_pipeline screen      # indicator screening -> observations.parquet + report
python -m gaid_pipeline queries     # versioned query set (5 variants, paired subsample)

# $0 pipeline test with synthetic responses (separate cache):
python -m gaid_pipeline run-eval --model llama-4-maverick --dry-run --limit 400
python -m gaid_pipeline classify --dry-run

# real run (launched by the researcher only; resumable, hard budget cap,
# free-tier endpoint by default — needs OPENROUTER_API_KEY in .env):
python -m gaid_pipeline run-eval --model llama-4-maverick --budget 5
python -m gaid_pipeline classify              # $0 post-processing, re-runnable
python -m gaid_pipeline validate-export      # blind-coding CSV for human validation
python -m gaid_pipeline validate-kappa       # Cohen's kappa after coding

python -m gaid_pipeline status      # what is installed locally
```

Methodology decisions and their mapping to the pilots' peer review:
see [METHODOLOGY.md](METHODOLOGY.md).

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
- [x] Indicator screening as code (thematic mapping, coverage incl. income tiers,
      redundancy with printed keep-justifications) — reproduces the IEEE frame
      on w1_v2: 18 indicators, 2,978 observations
- [x] Eval engine: versioned query templates (5 variants incl. the
      refusal-elicitation JSON contract), paired variant subsampling, cached
      budget-capped resumable OpenRouter client with dry-run mode,
      multi-threshold scale-aware classifier (18 unit tests),
      human-validation harness (blind coding + Cohen's kappa)
- [x] Composite index module (Phase 3): six formative pillars -> overall index
      + readiness lens, annual editions with 3-year lookback, nested equal
      weights; per-wave dimensionality audit (group-level Cronbach's alpha,
      equal-vs-PCA weighting check), normalisation sensitivity variants,
      convergent validity vs held-out Tortoise + GIRAI indices
- [x] Stats module (`stats`): multi-threshold headline rates + Kendall
      ranking stability, logistic regression with cluster-robust SEs by
      country (+ optional `--mixed` Bayesian GLMM with country random
      intercepts), income-tier stratification with chi-square, documented-vs-
      estimated cutoff sensitivity, balanced-subset check, scale-invariant
      |log10 ratio| error; emits reports/<tag>/stats_report.md + stats.json
- [x] Release watcher (`watch`): diffs OpenRouter /models + Hugging Face orgs
      against the registry, flag-and-wait (exit 2 -> CI opens an issue);
      `watch --bootstrap` records the baseline catalogue
- [x] Dashboard static build (`site-data` + `site-build`): 230 SEO-indexable
      HTML pages — home with interactive choropleth + edition slider, full
      rankings, methodology, 227 country profiles (server-rendered radar,
      full metric browser) — design harmonised with aiinsocietyhub.com;
      sitemap.xml + robots.txt included; verified in browser preview
- [x] Hostinger deploy of site/dist to gaid.aiinsocietyhub.com (subdomain
      document root only; WordPress never touched) — LIVE; Search Console
      verified; clean URLs (/rankings/, /methodology/) + favicon + og cards
- [x] `run-panel`: every active model in one command, per-model budget caps,
      fully resumable from the response cache
- [x] GitHub Actions: weekly wave + release watch (opens an issue, never
      spends) and manual `workflow_dispatch` eval runs (budget input,
      response cache persisted as artifact, OPENROUTER_API_KEY secret)
