from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class StudentCreate(BaseModel):
    name: str
    surname: str
    group: int


class StudentUpdate(BaseModel):
    name: Optional[str] = None
    surname: Optional[str] = None
    group: Optional[int] = None


class ReportCreate(BaseModel):
    title: str
    author: str
    group: int
    subject: str
    student_id: Optional[int] = None
    comment: Optional[str] = ""


class ReportUpdate(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    group: Optional[int] = None
    subject: Optional[str] = None
    comment: Optional[str] = None


class ChunkData(BaseModel):
    text: str
    hash: str


class PartData(BaseModel):
    type: str
    chunks: List[ChunkData]


class SearchParams(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    group: Optional[int] = None
    subject: Optional[str] = None
    word: Optional[str] = None
    min_flesh: Optional[int] = None
    min_originality: Optional[float] = None
