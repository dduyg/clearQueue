<div align="center">

# ClearQueue

**An explainable case-prioritization engine for operational teams.**

Upload a spreadsheet of cases. Get a transparent 0–100 priority score for
every one of them — with a full, inspectable breakdown of *why*.

[![Python](https://img.shields.io/badge/python-3.11-blue?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/backend-FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Frontend](https://img.shields.io/badge/frontend-HTML%2FCSS%2FJS-f7df1e)](#tech-stack)
[![License](https://img.shields.io/badge/license-MIT-lightgrey)](#license)
[![Model type](https://img.shields.io/badge/model-rule--based%2C%20100%25%20explainable-4b9c7a)](#responsible-scoring)

**[Live demo](#) · [Quickstart](#quickstart) · [How the scoring works](#how-the-scoring-works) · [Deploy your own](#deploy-your-own)**

</div>

---

## The problem

Most triage tools give a team a ranked list and ask them to trust it. When
the ranking comes from a model no one can inspect, "trust it" is the only
option — which makes the tool useless the moment someone asks *why is this
case first?* and nobody can answer.

ClearQueue takes the opposite position: **every point in every score is
named, weighted, and visible.** A reviewer can see exactly which factors
pushed a case to the top of the queue, and exactly what would bring it back
down. It's a decision-support tool a human stays in charge of, not a
black-box ranking they're asked to defer to.

## What it does

| | |
|---|---|
| 📤 **Upload any CSV** | `case_id`, `category`, `amount`, `days_open`, `missing_information`, `urgency`, `dependencies` — works across insurance claims, support tickets, maintenance requests, complaints, or any operational case type with this shape. |
| 🎯 **Explainable 0–100 scoring** | Every score breaks down into five named, weighted factors, each with the exact points it contributed and a plain-language reason why. |
| 📋 **Prioritized work queue** | Cases sorted highest-priority-first with a concrete recommended action — *Review today*, *Review this week*, or *Monitor*. |
| 📊 **Portfolio analytics** | Priority distribution, category breakdown, top scoring factors across the dataset, and case-age distribution — the view a team lead actually needs. |
| 🧪 **Live "what-if" simulation** | Drag a case's amount, age, urgency, or dependencies and watch the score recompute instantly — against the *same* engine that scored the real data, not a separate approximation. |
| 🛡️ **Responsible Scoring page** | States plainly what the model is (rule-based), what it never uses (protected/personal attributes), and that every score is a recommendation for a human reviewer — never an automated decision. |
| 🔁 **Proven cross-domain** | Three bundled sample datasets — insurance claims, support tickets, maintenance requests — score correctly through the exact same, unmodified engine. Not a claim; a click-through demo. |

## Screenshots

> _Add 2–3 screenshots or a short GIF here once deployed — the work queue
> view and the factor-breakdown detail panel are the two most convincing
> shots for a portfolio._

## How the scoring works

Every case is scored against five independently-weighted factors that sum
to a maximum of 100 points:

| Factor | Max points | What it measures |
|---|---|---|
| Financial impact | 25 | Case's `amount`, normalized against the *percentile distribution of the uploaded dataset itself* — so the same engine correctly treats a €500 support ticket and a €50,000 insurance claim as "high impact" for their respective domains, with no hardcoded thresholds. |
| Case age | 20 | Days the case has been open. |
| Missing information | 20 | Whether required information is still outstanding. |
| Urgency | 25 | Reported urgency level (low / medium / high). |
| Blocking dependencies | 10 | Whether the case is blocking other work. |

If a column is missing from the uploaded CSV, that factor is marked
`unavailable` and contributes zero — the engine degrades gracefully on
messy, partial, real-world exports instead of failing.

The full logic lives in [`backend/scoring.py`](./backend/scoring.py): pure
Python, zero framework dependencies, fully readable in one sitting.

## Tech stack

- **Backend:** Python, FastAPI — serves both the JSON API and the static
  frontend from a single service.
- **Frontend:** Plain HTML/CSS/vanilla JS — no framework, no build step, no
  npm. Keeps the whole project deployable with nothing but Python installed.
- **Scoring engine:** Pure Python (`dataclasses`, no dependencies) —
  reusable outside the web app, e.g. in a notebook or batch job.

No database, no auth, no build pipeline — deliberately minimal so the
project stays easy to read end-to-end, run locally in under a minute, and
deploy for free on a single service.

## Quickstart

```bash
git clone https://github.com/YOUR-USERNAME/clearqueue.git
cd clearqueue/backend
pip install -r requirements.txt
uvicorn main:app --reload
```

Open **http://localhost:8000**, click **Try sample data**, and pick any of
the three bundled datasets.

## Project structure

```
clearqueue/
├── backend/
│   ├── main.py           # FastAPI app — API routes + serves the static frontend
│   ├── scoring.py         # The scoring engine (pure Python, framework-agnostic)
│   └── requirements.txt
├── static/
│   ├── index.html
│   ├── style.css
│   └── app.js               # No build step, no framework — vanilla JS
├── sample_data/
│   ├── insurance_claims.csv
│   ├── support_tickets.csv
│   └── maintenance_requests.csv
└── Dockerfile               # For Hugging Face Spaces / any Docker host
```

## API reference

| Endpoint | Method | Description |
|---|---|---|
| `/api/score` | `POST` | Upload a CSV (`multipart/form-data`, field `file`) → scored, sorted case list. |
| `/api/simulate` | `POST` | Recompute one case's score against edited field values. |
| `/api/samples` | `GET` | List available sample datasets. |
| `/api/sample/{id}` | `GET` | Download a specific sample CSV. |
| `/api/fairness` | `GET` | Responsible-scoring governance statement, structured as JSON. |

## Responsible scoring

| | |
|---|---|
| Model type | Rule-based scoring |
| Explainability | 100% |
| Human review | Required |
| Automated decision | No |

The score is a prioritization recommendation for operational triage — never
an automated decision about a person. It does not use, and was designed
from the start to exclude, name, gender, ethnicity, religion, nationality,
health information, or postcode used as a proxy for personal
characteristics. Full statement in-app under **Responsible scoring**.

## Deploy your own

Three complete, free deployment paths, each with a full beginner walkthrough:

| Guide | Platform | Requires |
|---|---|---|
| [`GETTING_LIVE.md`](./GETTING_LIVE.md) | GitHub + Render | Git installed |
| [`GETTING_LIVE_HUGGINGFACE.md`](./GETTING_LIVE_HUGGINGFACE.md) | Hugging Face Spaces (Docker) | Git installed |
| [`GETTING_LIVE_BROWSER_ONLY.md`](./GETTING_LIVE_BROWSER_ONLY.md) | GitHub + Hugging Face Spaces | Nothing — browser only |

## License

MIT — see [`LICENSE`](./LICENSE). Free to use, fork, and adapt.
