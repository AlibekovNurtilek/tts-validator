from sqlalchemy import Column, Integer, String
from app.db import Base
from sqlalchemy.orm import relationship

class Speaker(Base):
    __tablename__ = "speakers"

    id = Column(Integer, primary_key=True, index=True)
    speaker_name = Column(String, unique=True, index=True, nullable=False)
    
    # relationships
    samples = relationship(
        "SampleText",
        back_populates="speaker",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )