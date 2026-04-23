import os
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

# Use environment variable or default to local SQLite
# For Vercel/serverless: use in-memory SQLite or configure DATABASE_URL
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:////tmp/market.db")

# For in-memory SQLite during development on serverless (optional):
# DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    pool_pre_ping=True
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(String, nullable=True)
    image_url = Column(String, nullable=True) # For the cards

    products = relationship("Product", back_populates="category")

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    variant = Column(String, nullable=True)
    price = Column(Float)
    partition = Column(String, nullable=True)
    category_id = Column(Integer, ForeignKey("categories.id"))

    category = relationship("Category", back_populates="products")

def init_db():
    Base.metadata.create_all(bind=engine)
