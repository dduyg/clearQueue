# ClearQueue — Explainable Case Prioritization Engine

ClearQueue turns a spreadsheet of operational cases (insurance claims, support
tickets, maintenance requests, complaints — any domain) into a transparent,
prioritized work queue. Every score is 100% explainable: no ML black box,
just named, weighted factors a reviewer can inspect and challenge.

**Live demo:** _add your deployed URL here once deployed_

## What it does

- **Upload a CSV** of cases and get a 0–100 priority score for each one.
- **Any column headers work**: if your CSV doesn't already use ClearQueue's
  field names, a mapping step lets you match your columns (e.g. `Cost`,
  `Ticket ID`, `Sev`) to the engine's expected fields before scoring.
- **See exactly why**: every score breaks down into named factors (financial
  impact, case age, missing information, urgency, blocking dependencies)
  with the exact points each one contributed.
- **Work queue**: cases sorted highest-priority-first, with a recommended
  action ("Review today" / "Review this week" / "Monitor").
- **Overview dashboard**: portfolio-level stats and distributions.
- **"What if" simulation**: drag a case's amount, age, urgency, or
  dependencies and watch the score recompute live, against the same
  scoring engine used for the real data (not a separate approximation).
- **PDF export**: download a one-page explanation for any case, or a
  summary report of the whole work queue.
- **ML comparison mode**: trains a small gradient-boosted model to
  reproduce the rule engine's own scores, then explains it with SHAP —
  a controlled check of whether a black-box model, explained after the
  fact, actually agrees with an engine you can read line by line. Surfaces
  the biggest disagreements first, which is usually the interesting part.
- **Responsible Scoring page**: states plainly what the model is (rule-based),
  what it excludes (all protected/personal attributes), and that it is a
  recommendation for a human reviewer, not an automated decision.
- **Three sample datasets** (insurance claims, support tickets, maintenance
  requests) via the "Try sample data" menu — the same engine, unmodified,
  scores all three domains.

## Architecture

```
clearqueue/
├── backend/
│   ├── main.py           # FastAPI app — API routes + serves the static frontend
│   ├── scoring.py         # Rule-based scoring engine (pure Python, framework-agnostic)
│   ├── ml_compare.py      # ML-comparison mode (GradientBoosting + SHAP)
│   ├── pdf_report.py      # PDF export (reportlab)
│   └── requirements.txt
├── static/
│   ├── index.html
│   ├── style.css
│   └── app.js               # No build step, no framework — vanilla JS
├── sample_data/
│   ├── insurance_claims.csv
│   ├── support_tickets.csv
│   └── maintenance_requests.csv
├── app.py                   # Hugging Face Gradio-SDK entrypoint (see deploy guides)
├── requirements.txt          # Root deps, used by the Hugging Face Space build
└── Dockerfile                # For Docker-capable hosts / paid HF plans
```

One FastAPI service serves both the API (`/api/*`) and the static frontend
(everything else), so there's exactly one thing to deploy. The frontend has
no build step (no npm, no bundler) — it's plain HTML/CSS/JS.

The rule-based scoring engine (`scoring.py`) has zero framework dependencies
— pure Python with dataclasses, easy to unit test or reuse elsewhere. The
ML-comparison model in `ml_compare.py` is intentionally kept separate and
clearly labeled: it's trained to imitate the rule engine's own output (there's
no real historical outcome data for a demo project), so its SHAP attributions
can be compared apples-to-apples against the rule engine's own factor
breakdown for the same cases.

## Run it locally

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

Then open **http://localhost:8000**.

Note: `requirements.txt` now includes `scikit-learn`, `shap`, and `reportlab`
for the ML comparison and PDF export features — install takes noticeably
longer than a minimal FastAPI app the first time, mostly because of `shap`.

## API reference

| Endpoint | Method | Description |
|---|---|---|
| `/api/csv/preview` | `POST` | Upload a CSV → headers, sample rows, and a suggested column mapping. |
| `/api/score` | `POST` | Upload a CSV (+ optional `mapping` field) → scored, sorted case list. |
| `/api/simulate` | `POST` | Recompute one case's score against edited field values. |
| `/api/ml_compare` | `POST` | Run the ML/SHAP comparison against an already-scored case list. |
| `/api/report/case` | `POST` | PDF explanation for one scored case. |
| `/api/report/queue` | `POST` | PDF summary of the full work queue. |
| `/api/samples` | `GET` | List available sample datasets. |
| `/api/sample/{id}` | `GET` | Download a specific sample CSV. |
| `/api/fairness` | `GET` | Responsible-scoring governance statement, as JSON. |

## Deploy it for free

**New to git/GitHub/deploying?** Full step-by-step walkthroughs are
included — pick one:
- [`GETTING_LIVE.md`](./GETTING_LIVE.md) — GitHub + Render
- [`GETTING_LIVE_HUGGINGFACE.md`](./GETTING_LIVE_HUGGINGFACE.md) — Hugging Face Spaces (free Gradio-SDK carrier — Docker SDK is now paid-plan-only on Hugging Face)
- [`GETTING_LIVE_BROWSER_ONLY.md`](./GETTING_LIVE_BROWSER_ONLY.md) — GitHub + Hugging Face Spaces, no terminal or Git install required

Quick reference if you've done this before:
- **Render** (recommended): root dir `backend`, build `pip install -r
  requirements.txt`, start `uvicorn main:app --host 0.0.0.0 --port $PORT`,
  free instance type. Free tier cold-starts after ~15 min idle (~30–60s to
  wake).
- **Hugging Face Spaces**: Gradio SDK, `app_file: app.py`, root
  `requirements.txt` — see the dedicated guide above. Docker SDK works too
  if you're on a paid HF plan (`Dockerfile` is included either way).
- **Fly.io**: `fly launch` from `backend/`, `fly deploy`. Small always-on
  free instance, avoids Render's cold start.

## Responsible scoring

| | |
|---|---|
| Model type | Rule-based scoring (primary) |
| Explainability | 100% |
| Human review | Required |
| Automated decision | No |

The optional ML-comparison mode is a separate, clearly-labeled experiment —
it never replaces the rule-based score shown in the work queue, and it's
trained only to imitate the rule engine, not to make independent judgments.

## Roadmap

- [x] Optional ML-comparison mode alongside the rule-based baseline, with
      SHAP-based explanations.
- [x] CSV column mapping UI, for datasets that use different header names.
- [x] Exportable PDF report per case or per work queue.
- [ ] Persisted work queues (currently everything is computed fresh per
      upload — no database, by design, but a saved-session option would be
      a natural next step).

## For your CV / README

> Built and deployed an explainable case-prioritization platform that scores
> operational cases 0–100 using a transparent, auditable rule-based engine.
> Implemented a Python/FastAPI backend, a dependency-free JS frontend, a
> column-mapping step for arbitrary CSV schemas, live "what-if" score
> simulation, PDF export, an ML-vs-rule-engine comparison mode using SHAP,
> and a responsible-AI governance page documenting model transparency and
> excluded attributes.
