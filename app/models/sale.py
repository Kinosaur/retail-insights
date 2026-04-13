from sqlalchemy import Boolean, Column, Date, Float, ForeignKey, Integer, String, false
from app.db import Base


class Sale(Base):
    __tablename__ = "sales"

    sale_id = Column(Integer, primary_key=True, autoincrement=True)
    upload_batches_id = Column(String, ForeignKey("upload_batches.upload_batches_id"), nullable=False, index=True)
    product_id = Column(String, ForeignKey("products.product_id"), nullable=False, index=True)
    sale_date = Column(Date, nullable=False, index=True)
    quantity = Column(Integer, nullable=False)           # negative = return
    unit_price = Column(Float, nullable=False)
    revenue = Column(Float, nullable=False)              # quantity * unit_price — kept for analytics
    is_return = Column(Boolean, default=False, server_default=false(), nullable=False)
