from sqlalchemy import Column, String, Float, JSON, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = "sqlite:///./backend/ironmind.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class NodeTable(Base):
    __tablename__ = "nodes"
    id = Column(String, primary_key=True, index=True)
    name = Column(String)
    type = Column(String)
    layer = Column(String)
    metadata_json = Column(JSON)

class EdgeTable(Base):
    __tablename__ = "edges"
    id = Column(String, primary_key=True, index=True)
    source = Column(String, index=True)
    target = Column(String, index=True)
    type = Column(String)
    confidence = Column(Float)
    metadata_json = Column(JSON)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def bulk_insert_graph(db, nodes_data, edges_data):
    # Clear existing to ensure fresh state for the current analysis session
    db.query(NodeTable).delete()
    db.query(EdgeTable).delete()
    
    for n in nodes_data:
        db.add(NodeTable(**n))
    for e in edges_data:
        db.add(EdgeTable(**e))
    db.commit()
