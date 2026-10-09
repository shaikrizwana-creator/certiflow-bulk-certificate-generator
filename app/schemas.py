from datetime import date, datetime
from pydantic import BaseModel, Field, field_validator

class RecipientInput(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=5, max_length=254)
    course_name: str = Field(min_length=2, max_length=160)
    completion_date: date

    @field_validator("name", "course_name", "email")
    @classmethod
    def strip_and_check(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Must not be blank")
        return value

    @field_validator("email")
    @classmethod
    def basic_email_check(cls, value: str) -> str:
        if "@" not in value or "." not in value.rsplit("@", 1)[-1]:
            raise ValueError("Must be a valid email address")
        return value

class CreateJobRequest(BaseModel):
    recipients: list[RecipientInput] = Field(min_length=1, max_length=500)

class RecipientResult(BaseModel):
    id: int
    name: str
    email: str
    status: str
    error_message: str | None = None
    certificate_url: str | None = None

class JobResult(BaseModel):
    id: str
    status: str
    total: int
    succeeded: int
    failed: int
    created_at: datetime
    completed_at: datetime | None
    recipients: list[RecipientResult]

