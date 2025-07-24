from pydantic import BaseModel

class SpeakerBase(BaseModel):
    speaker_name: str

class SpeakerCreate(SpeakerBase):
    pass

class SpeakerUpdate(SpeakerBase):
    pass

class SpeakerOut(SpeakerBase):
    id: int

    class Config:
        orm_mode = True