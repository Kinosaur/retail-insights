from sqlalchemy import Column, Date, ForeignKey, Integer, String
from app.db import Base


class InventorySnapshot(Base):
    __tablename__ = "inventory_snapshots"

    inventory_snapshots_id = Column(Integer, primary_key=True, autoincrement=True)
    upload_batches_id = Column(String, ForeignKey("upload_batches.upload_batches_id"), nullable=False, index=True)
    product_id = Column(String, ForeignKey("products.product_id"), nullable=False, index=True)
    quantity_on_hand = Column(Integer, nullable=False)
    snapshot_date = Column(Date, nullable=False, index=True)
