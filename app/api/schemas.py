"""Pydantic-схемы запросов и ответов REST API."""
from datetime import date
from typing import Optional

from pydantic import BaseModel, Field

from ..domain import Role, Status


class RegisterRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255, examples=["student@example.kz"])
    password: str = Field(..., min_length=8, max_length=128, examples=["secret123"])
    full_name: str = Field(..., min_length=1, max_length=255, examples=["Шамсетдинов М.Д."])
    role: Role
    group: Optional[str] = Field(None, max_length=100, examples=["БИС 31с"])


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=1, max_length=128)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    role: Role
    group_id: Optional[int] = None


class SubjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, examples=["Технологии разработки ПО"])
    group: str = Field(..., min_length=1, max_length=100, examples=["БИС 31с"])


class SubjectOut(BaseModel):
    id: int
    name: str
    group_id: int


class AssignmentCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, examples=["ПР1"])
    description: str = Field("", max_length=5000)
    deadline: date = Field(..., examples=["2026-11-20"])


class AssignmentUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=5000)
    deadline: Optional[date] = None


class AssignmentOut(BaseModel):
    id: int
    subject_id: int
    title: str
    description: str
    deadline: date


class StatusChange(BaseModel):
    status: Status


class ReviewRequest(BaseModel):
    accept: bool
    comment: str = Field("", max_length=2000)


class SubmissionOut(BaseModel):
    id: int
    assignment_id: int
    title: str
    subject_id: int
    subject: str
    deadline: str
    status: Status
    comment: str
    submitted_at: Optional[str] = None
    days_left: int
    flag: str


class SubmissionRowOut(BaseModel):
    submission_id: int
    student: str
    status: Status
    comment: str


class DebtorOut(BaseModel):
    student: str
    assignment: str
    status: Status


class ProgressOut(BaseModel):
    percent: int
    total: int
    accepted: int
