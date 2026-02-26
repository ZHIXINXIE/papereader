from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class TaskBase(BaseModel):
    name: str
    description: Optional[str] = None
    template_id: Optional[str] = None
    model_name: Optional[str] = "gemini-3-flash-preview"

class TaskCreate(TaskBase):
    pass

class TaskUpdate(BaseModel):
    status: Optional[str] = None

class Task(TaskBase):
    id: str
    user_id: str
    status: str
    model_name: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class PaperBase(BaseModel):
    title: str

class PaperCreate(BaseModel):
    titles: List[str]

class Interpretation(BaseModel):
    content: str
    template_used: str
    created_at: datetime

    class Config:
        from_attributes = True

class Paper(PaperBase):
    id: str
    task_id: str
    pdf_path: Optional[str] = None
    source: Optional[str] = None
    source_url: Optional[str] = None
    status: str
    failure_reason: Optional[str] = None
    created_at: datetime
    interpretation: Optional[Interpretation] = None

    class Config:
        from_attributes = True

class TemplateBase(BaseModel):
    name: str
    content: List[str]
    is_default: bool = False

class TemplateCreate(TemplateBase):
    pass

class Template(TemplateBase):
    id: str
    user_id: str
    created_at: datetime

    class Config:
        from_attributes = True

class TemplateUpdate(BaseModel):
    is_default: Optional[bool] = None

class TaskStatistics(BaseModel):
    total: int
    done: int
    failed: int
    skipped: int
    queued: int
    processing: int

class TaskWithStats(Task):
    statistics: TaskStatistics

class TaskBatchDelete(BaseModel):
    ids: List[str]

class ReReadRequest(BaseModel):
    template_id: Optional[str] = None
    model_name: Optional[str] = None
