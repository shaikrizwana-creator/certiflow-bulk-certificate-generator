import io
import zipfile
from fastapi.testclient import TestClient
from app.main import app, process_job
from app.database import Base, engine

client = TestClient(app)

def sample_payload():
    return {"recipients": [
        {"name": "Asha Rao", "email": "asha@example.com", "course_name": "Python Basics", "completion_date": "2026-10-09"},
        {"name": "Ravi Kumar", "email": "ravi@example.com", "course_name": "Python Basics", "completion_date": "2026-10-09"},
    ]}

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_create_job_and_track_progress():
    response = client.post("/api/v1/jobs", json=sample_payload())
    assert response.status_code == 202
    data = response.json()
    assert data["total"] == 2
    # BackgroundTasks runs before TestClient returns, so the job should be finished.
    status = client.get(data["status_url"])
    assert status.status_code == 200
    result = status.json()
    assert result["total"] == 2
    assert result["succeeded"] == 2
    assert result["status"] == "completed"

def test_input_validation():
    response = client.post("/api/v1/jobs", json={"recipients": [
        {"name": "", "email": "bad", "course_name": "X", "completion_date": "not-a-date"}
    ]})
    assert response.status_code == 422

def test_individual_generation_failure(monkeypatch):
    from app import main
    original = main.generate_certificate
    def fail_one(output_path, name, course_name, completion_date):
        if name == "Asha Rao":
            raise RuntimeError("simulated failure")
        return original(output_path, name, course_name, completion_date)
    monkeypatch.setattr(main, "generate_certificate", fail_one)
    response = client.post("/api/v1/jobs", json=sample_payload())
    status = client.get(response.json()["status_url"]).json()
    assert status["succeeded"] == 1
    assert status["failed"] == 1
    assert status["status"] == "completed_with_errors"
    failed = [r for r in status["recipients"] if r["name"] == "Asha Rao"][0]
    assert failed["status"] == "failed"
    assert failed["error_message"]

def test_retrieve_pdf_and_zip():
    response = client.post("/api/v1/jobs", json=sample_payload())
    job_id = response.json()["job_id"]
    status = client.get(f"/api/v1/jobs/{job_id}").json()
    recipient = status["recipients"][0]
    pdf = client.get(recipient["certificate_url"])
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
    zipped = client.get(f"/api/v1/jobs/{job_id}/download")
    assert zipped.status_code == 200
    with zipfile.ZipFile(io.BytesIO(zipped.content)) as archive:
        assert len(archive.namelist()) == 2

def test_unknown_job_returns_404():
    response = client.get("/api/v1/jobs/not-a-real-job")
    assert response.status_code == 404
