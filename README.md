# CertiFlow — Bulk Certificate Generation API

CertiFlow is a Python REST API that accepts a batch of recipients, generates a PDF certificate for each recipient, tracks job progress in a relational database, and provides individual PDF and ZIP downloads.

## Features
- Bulk submission (1–500 recipients per job)
- Input validation with useful HTTP 422 responses
- Background job processing using FastAPI `BackgroundTasks`
- SQLite + SQLAlchemy persistence for jobs and recipient outcomes
- Per-recipient error handling: one generation failure does not stop the batch
- Progress counts and status endpoint
- Individual PDF downloads and ZIP of successful certificates
- Interactive OpenAPI docs at `/docs`
- Automated tests for creation, validation, generation, progress, failure isolation and downloads

## Requirements
- Python 3.11 or newer recommended
- pip

## Setup

### Windows PowerShell
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If PowerShell blocks activation, use:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### macOS / Linux
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Run the API
```bash
uvicorn app.main:app --reload
```
Open:
- API docs: http://127.0.0.1:8000/docs
- Health: http://127.0.0.1:8000/health

## Submit a bulk request
Use `POST /api/v1/jobs` in `/docs` with this example:

```json
{
  "recipients": [
    {
      "name": "Asha Rao",
      "email": "asha@example.com",
      "course_name": "Python Basics",
      "completion_date": "2026-10-09"
    },
    {
      "name": "Ravi Kumar",
      "email": "ravi@example.com",
      "course_name": "Python Basics",
      "completion_date": "2026-10-09"
    }
  ]
}
```

The response includes a `job_id` and `status_url`. Save the ID.

## Check progress
Call `GET /api/v1/jobs/{job_id}`. The response includes `status`, `total`, `succeeded`, `failed`, `pending_or_processing`, and recipient-level status/errors.

Possible job states: `pending`, `processing`, `completed`, `completed_with_errors`.

## Retrieve certificates
- Individual PDF: `GET /api/v1/jobs/{job_id}/certificates/{recipient_id}`
- ZIP of all successful PDFs: `GET /api/v1/jobs/{job_id}/download`

The ZIP endpoint returns HTTP 409 while the job is still processing.

## Run tests
```bash
pytest -q
```

## Design decisions and limitations
- **FastAPI** provides validation, API documentation and a clean REST interface.
- **SQLite** keeps local setup simple; SQLAlchemy makes the data layer portable to PostgreSQL.
- **BackgroundTasks** lets the request return after accepting a job. It is suitable for a small demonstration, but work is not durable across process crashes and it is not intended for heavy production workloads. A production deployment should use a durable queue (e.g. Celery/RQ with Redis), dedicated workers, retries and object storage.
- **Failure isolation** is per recipient: each PDF is generated in its own `try/except`, and every recipient outcome is stored.
- **Validation** rejects malformed request data before creating a job. A generation-time failure is recorded against that recipient while the remaining recipients continue.
- This demo has no authentication or authorization; add those before exposing it publicly.
- Generated PDFs and the SQLite database are local files and should not be committed to Git.

## Suggested next steps
- Add database migrations (Alembic)
- Add auth/API keys and rate limiting
- Move PDFs to S3-compatible object storage
- Add a durable worker queue and retry policy
- Add a frontend dashboard
