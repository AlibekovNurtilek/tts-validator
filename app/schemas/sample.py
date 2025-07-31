from pydantic import BaseModel
from datetime import datetime
from typing import List


class SampleBase(BaseModel):
    dataset_id: int
    speaker_id: int
    filename: str
    text: str | None = None
    duration: float | None = None

class SampleCreate(SampleBase):
    pass

class SampleUpdate(SampleBase):
    pass

class SampleOut(SampleBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True

class DatasetSamplesResponse(BaseModel):
    dataset_id: int
    page: int
    limit: int
    samples: List[SampleOut]
