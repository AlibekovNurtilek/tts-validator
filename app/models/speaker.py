from sqlalchemy import Column, Integer, String
from app.db import Base

class Speaker(Base):
    __tablename__ = "speakers"

    id = Column(Integer, primary_key=True, index=True)
    speaker_name = Column(String, unique=True, index=True, nullable=False)
    
