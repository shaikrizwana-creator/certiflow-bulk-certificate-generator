import os
import uuid
import zipfile
from datetime import datetime
from pathlib import Path

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from .certificates import generate_certificate
from .database import Base, SessionLocal, engine
from .models import Job, Recipient
from .schemas import CreateJobRequest

Base.metadata.create_all(bind=engine)
app = FastAPI(
    title="CertiFlow API",
    description="Bulk PDF certificate generation with job progress and downloadable results.",
    version="1.0.0",
)

OUTPUT_DIR = Path(os.getenv("CERTIFICATE_OUTPUT_DIR", "generated_certificates"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def process_job(job_id: str) -> None:
    """Process recipients independently so one PDF failure does not stop the batch."""
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return
        job.status = "processing"
        db.commit()

        recipients = db.query(Recipient).filter(Recipient.job_id == job_id).all()
        for recipient in recipients:
            try:
                recipient.status = "processing"
                db.commit()
                out = OUTPUT_DIR / job_id / f"certificate_{recipient.id}.pdf"
                generate_certificate(
                    str(out), recipient.name, recipient.course_name, recipient.completion_date
                )
                recipient.certificate_path = str(out)
                recipient.status = "succeeded"
                recipient.error_message = None
            except Exception as exc:
                recipient.status = "failed"
                recipient.error_message = f"Certificate generation failed: {type(exc).__name__}"
            db.commit()

        job = db.query(Job).filter(Job.id == job_id).first()
        job.succeeded = db.query(Recipient).filter_by(job_id=job_id, status="succeeded").count()
        job.failed = db.query(Recipient).filter_by(job_id=job_id, status="failed").count()
        job.status = "completed_with_errors" if job.failed else "completed"
        job.completed_at = datetime.utcnow()
        db.commit()
    finally:
        db.close()


@app.get("/")
def root():
    return {"name": "CertiFlow API", "docs": "/docs", "health": "/health"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/v1/jobs", status_code=202)
def create_job(payload: CreateJobRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    job_id = str(uuid.uuid4())
    job = Job(id=job_id, status="pending", total=len(payload.recipients))
    db.add(job)
    db.flush()

    for item in payload.recipients:
        recipient = Recipient(
            job_id=job_id,
            name=item.name,
            email=item.email,
            course_name=item.course_name,
            completion_date=item.completion_date.isoformat(),
            status="pending",
        )
        db.add(recipient)
    db.commit()
    background_tasks.add_task(process_job, job_id)
    return {
        "job_id": job_id,
        "status": "pending",
        "total": job.total,
        "status_url": f"/api/v1/jobs/{job_id}",
        "message": "Job accepted. Poll the status URL for progress.",
    }


@app.get("/api/v1/jobs/{job_id}")
def get_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    recipients = []
    for r in job.recipients:
        recipients.append({
            "id": r.id,
            "name": r.name,
            "email": r.email,
            "status": r.status,
            "error_message": r.error_message,
            "certificate_url": f"/api/v1/jobs/{job_id}/certificates/{r.id}" if r.status == "succeeded" else None,
        })
    return {
        "job_id": job.id,
        "status": job.status,
        "total": job.total,
        "succeeded": job.succeeded,
        "failed": job.failed,
        "pending_or_processing": job.total - job.succeeded - job.failed,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "recipients": recipients,
    }


@app.get("/api/v1/jobs/{job_id}/certificates/{recipient_id}")
def download_certificate(job_id: str, recipient_id: int, db: Session = Depends(get_db)):
    recipient = db.query(Recipient).filter_by(id=recipient_id, job_id=job_id).first()
    if not recipient:
        raise HTTPException(status_code=404, detail="Recipient not found in this job")
    if recipient.status != "succeeded" or not recipient.certificate_path:
        raise HTTPException(status_code=409, detail="Certificate is not available")
    path = Path(recipient.certificate_path)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Certificate file not found")
    return FileResponse(path, media_type="application/pdf", filename=f"certificate_{recipient.id}.pdf")


@app.get("/api/v1/jobs/{job_id}/download")
def download_zip(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status not in ("completed", "completed_with_errors"):
        raise HTTPException(status_code=409, detail="Job is still processing")
    zip_path = OUTPUT_DIR / job_id / "certificates.zip"
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for r in job.recipients:
            if r.status == "succeeded" and r.certificate_path and Path(r.certificate_path).is_file():
                archive.write(r.certificate_path, arcname=f"certificate_{r.id}_{r.name.replace(' ', '_')}.pdf")
    return FileResponse(zip_path, media_type="application/zip", filename=f"certiflow_{job_id}.zip")
