from sqlalchemy import Column, Date, Float, ForeignKey, Integer, String
from app.db import Base


class Sale(Base):
    __tablename__ = "sales"

    id = Column(Integer, primary_key=True, autoincrement=True)
    batch_id = Column(String, ForeignKey("upload_batches.id"), nullable=False, index=True)
    sku = Column(String, ForeignKey("products.sku"), nullable=False, index=True)
    sale_date = Column(Date, nullable=False, index=True)
    quantity = Column(Integer, nullable=False)          # negative = return
    unit_price = Column(Float, nullable=False)
    revenue = Column(Float, nullable=False)             # stored = quantity * unit_price
    is_return = Column(Integer, default=0)              # 0 = sale, 1 = return (SQLite bool)
