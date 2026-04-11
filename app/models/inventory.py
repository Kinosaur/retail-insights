from sqlalchemy import Column, Date, ForeignKey, Integer, String
from app.db import Base


class InventorySnapshot(Base):
    __tablename__ = "inventory_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    batch_id = Column(String, ForeignKey("upload_batches.id"), nullable=False, index=True)
    sku = Column(String, ForeignKey("products.sku"), nullable=False, index=True)
    quantity_on_hand = Column(Integer, nullable=False)
    snapshot_date = Column(Date, nullable=False, index=True)
