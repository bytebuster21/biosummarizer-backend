from sqlalchemy import Column, Integer, String, ForeignKey
from app.core.database import Base

class Entity(Base):
    __tablename__ = "entities"

    id = Column(Integer, primary_key=True, index=True)
    paper_id = Column(Integer, ForeignKey("papers.id"))
    name = Column(String, index=True)
    type = Column(String)  # e.g. DISEASE, DRUG, GENE

class Relation(Base):
    __tablename__ = "relations"

    id = Column(Integer, primary_key=True, index=True)
    paper_id = Column(Integer, ForeignKey("papers.id"))
    source_entity_id = Column(Integer, ForeignKey("entities.id"))
    target_entity_id = Column(Integer, ForeignKey("entities.id"))
    relation_type = Column(String)  # e.g. TREATS, CAUSES, ASSOCIATED_WITH