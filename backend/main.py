import io
import csv
import json
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException, Body, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from scoring import score_dataset, score_case, amount_percentiles, FAIRNESS_STATEMENT
from ml_compare import run_ml_comparison, MLCompareError
from pdf_report import build_case_pdf, build_queue_pdf

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title="ClearQueue", description="Explainable case prioritization engine")

# Wide-open CORS: this is a public portfolio demo, not a system holding real data.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


NUMERIC_FIELDS = {"amount", "days_open", "dependencies"}
CANONICAL_FIELDS = [
    "case_id", "category", "amount", "days_open",
    "missing_information", "urgency", "dependencies",
]

# Loose synonym list used to auto-suggest a column mapping for CSVs that
# don't already use ClearQueue's exact header names.
FIELD_SYNONYMS = {
    "case_id": ["case_id", "id", "ticket_id", "ticket", "case_number", "case_no", "reference", "ref", "wo_id", "work_order"],
    "category": ["category", "type", "case_type", "issue_type", "categoria"],
    "amount": ["amount", "cost", "value", "price", "claim_amount", "exposure", "total"],
    "days_open": ["days_open", "age", "open_days", "days_since_opened", "daysopen", "age_days"],
    "missing_information": ["missing_information", "missing_info", "incomplete", "missing", "info_missing"],
    "urgency": ["urgency", "priority", "severity", "urgency_level"],
    "dependencies": ["dependencies", "blocking", "blocked_by", "dependents", "blockers", "blocking_count"],
}


def _normalize_header(h: str) -> str:
    return h.strip().lower().replace(" ", "_").replace("-", "_")


def _suggest_mapping(headers: list[str]) -> dict[str, str]:
    """Best-effort guess of canonical_field -> uploaded header, for the
    mapping UI to pre-fill. Never guaranteed correct — the user confirms it."""
    normalized = {h: _normalize_header(h) for h in headers}
    suggestion = {}
    for canonical, synonyms in FIELD_SYNONYMS.items():
        for header, norm in normalized.items():
            if norm in synonyms:
                suggestion[canonical] = header
                break
    return suggestion


def _coerce(field: str, value: str):
    value = (value or "").strip()
    if value == "":
        return None
    if field in NUMERIC_FIELDS:
        try:
            return float(value)
        except ValueError:
            return None
    if field == "missing_information":
        return value
    return value


def _read_csv_text(raw_bytes: bytes) -> str:
    try:
        return raw_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        return raw_bytes.decode("latin-1")


def _parse_csv(raw_bytes: bytes, mapping: dict[str, str] | None = None) -> list[dict]:
    """mapping, if given, is {canonical_field: original_header_name}. Any
    uploaded column not referenced by the mapping is ignored. Without a
    mapping, headers are matched to canonical fields by exact name
    (case/space-insensitive) — the original zero-friction behaviour for
    CSVs that already use ClearQueue's column names."""
    text = _read_csv_text(raw_bytes)
    reader = csv.DictReader(io.StringIO(text))
    fieldnames = reader.fieldnames or []

    if mapping:
        header_to_canonical = {v: k for k, v in mapping.items() if v}
    else:
        header_to_canonical = {
            f: _normalize_header(f) for f in fieldnames if _normalize_header(f) in CANONICAL_FIELDS
        }

    if "case_id" not in header_to_canonical.values():
        raise HTTPException(
            status_code=400,
            detail="No column is mapped to 'case_id'. Every case needs a unique identifier.",
        )

    cases = []
    for row in reader:
        clean = {}
        for original, value in row.items():
            canonical = header_to_canonical.get(original)
            if not canonical:
                continue
            clean[canonical] = _coerce(canonical, value) if canonical not in ("case_id", "category") else (value or "").strip()
        if not clean.get("case_id"):
            continue
        cases.append(clean)
    if not cases:
        raise HTTPException(status_code=400, detail="No valid rows found in CSV")
    return cases


@app.post("/api/csv/preview")
async def csv_preview(file: UploadFile = File(...)):
    """Returns the raw headers, a few sample rows, and a best-effort
    suggested mapping — the frontend uses this to decide whether to show
    the column-mapping step, and to pre-fill it."""
    raw = await file.read()
    text = _read_csv_text(raw)
    reader = csv.DictReader(io.StringIO(text))
    headers = reader.fieldnames or []
    if not headers:
        raise HTTPException(status_code=400, detail="Could not read any columns from that file")
    rows = []
    for i, row in enumerate(reader):
        if i >= 5:
            break
        rows.append(row)
    exact_match = all(_normalize_header(h) in CANONICAL_FIELDS for h in headers) and \
        any(_normalize_header(h) == "case_id" for h in headers)
    return {
        "headers": headers,
        "preview_rows": rows,
        "suggested_mapping": _suggest_mapping(headers),
        "canonical_fields": CANONICAL_FIELDS,
        "needs_mapping": not exact_match,
    }


@app.post("/api/score")
async def score_csv(file: UploadFile = File(...), mapping: str | None = Form(None)):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a .csv file")
    raw = await file.read()
    mapping_dict = None
    if mapping:
        try:
            mapping_dict = json.loads(mapping)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Malformed column mapping")
    cases = _parse_csv(raw, mapping_dict)
    scored = score_dataset(cases)
    cutoffs = amount_percentiles([c.get("amount") for c in cases])
    return {"count": len(scored), "cases": scored, "percentile_cutoffs": list(cutoffs)}


@app.post("/api/simulate")
async def simulate(payload: dict = Body(...)):
    """Recompute a single case's score against an (optionally edited) set of
    field values, plus the percentile cutoffs from the case's original
    dataset context (passed through by the client) so simulation stays
    consistent with how the case was originally scored."""
    case = payload.get("case", {})
    cutoffs = tuple(payload.get("percentile_cutoffs", [0, 0, 0]))
    result = score_case(case, cutoffs)  # type: ignore[arg-type]
    return result.to_dict()


@app.post("/api/ml_compare")
async def ml_compare(payload: dict = Body(...)):
    """Trains a small gradient-boosted model to reproduce the rule-based
    engine's own scores, then explains it with SHAP — a controlled
    comparison between a transparent-by-construction engine and a
    black-box model explained after the fact."""
    cases = payload.get("cases", [])
    try:
        return run_ml_comparison(cases)
    except MLCompareError as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.post("/api/report/case")
async def report_case(payload: dict = Body(...)):
    """Generates a one-page PDF explanation for a single scored case."""
    case = payload.get("case")
    if not case:
        raise HTTPException(status_code=400, detail="Missing 'case'")
    pdf_bytes = build_case_pdf(case)
    filename = f"clearqueue_{case.get('case_id', 'case')}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post("/api/report/queue")
async def report_queue(payload: dict = Body(...)):
    """Generates a PDF summary of the full work queue."""
    cases = payload.get("cases", [])
    if not cases:
        raise HTTPException(status_code=400, detail="Missing 'cases'")
    pdf_bytes = build_queue_pdf(cases)
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="clearqueue_work_queue.pdf"'},
    )


SAMPLE_DATASETS = {
    "insurance": ("Insurance claims", "sample_data/insurance_claims.csv"),
    "support": ("Support tickets", "sample_data/support_tickets.csv"),
    "maintenance": ("Maintenance requests", "sample_data/maintenance_requests.csv"),
}


@app.get("/api/samples")
async def list_samples():
    return [{"id": k, "label": v[0]} for k, v in SAMPLE_DATASETS.items()]


@app.get("/api/sample/{dataset_id}")
async def sample_csv(dataset_id: str):
    entry = SAMPLE_DATASETS.get(dataset_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Unknown sample dataset")
    label, rel_path = entry
    path = BASE_DIR / rel_path
    return FileResponse(path, media_type="text/csv", filename=f"clearqueue_{dataset_id}_sample.csv")


@app.get("/api/fairness")
async def fairness():
    return FAIRNESS_STATEMENT


@app.get("/api/health")
async def health():
    return {"status": "ok"}


# Serve the static frontend last, so it doesn't shadow the /api routes above.
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
