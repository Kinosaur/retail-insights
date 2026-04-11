from sqlalchemy import Column, DateTime, Float, String, func
from app.db import Base


class Sku(Base):
    __tablename__ = "sku"

    sku_id = Column(String, primary_key=True, index=True)
    sku_name = Column(String, nullable=False)
    category = Column(String, nullable=True, index=True)
    cost_price = Column(Float, nullable=True)
    sell_price = Column(Float, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
