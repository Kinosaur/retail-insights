from sqlalchemy.orm import Session

from app.models.product import Product
from app.models.sale import Sale
from app.schemas.product import (
    ProductDetail,
    ProductItem,
    ProductListResponse,
    SaleHistoryItem,
)


def get_products(
    db: Session,
    page: int = 1,
    limit: int = 50,
    category: str | None = None,
) -> ProductListResponse:
    limit = min(limit, 200)  # cap at 200 per api.md
    query = db.query(Product)
    if category:
        query = query.filter(Product.category == category)
    total = query.count()
    rows = query.order_by(Product.product_id).offset((page - 1) * limit).limit(limit).all()
    return ProductListResponse(
        total=total,
        page=page,
        limit=limit,
        items=[
            ProductItem(
                product_id=p.product_id,
                product_name=p.product_name,
                category=p.category,
                cost_price=p.cost_price,
                sell_price=p.sell_price,
            )
            for p in rows
        ],
    )


def get_product_by_id(db: Session, product_id: str) -> ProductDetail | None:
    product = db.query(Product).filter(Product.product_id == product_id.upper()).first()
    if not product:
        return None
    sales = (
        db.query(Sale)
        .filter(Sale.product_id == product_id.upper())
        .order_by(Sale.sale_date)
        .all()
    )
    return ProductDetail(
        product_id=product.product_id,
        product_name=product.product_name,
        category=product.category,
        cost_price=product.cost_price,
        sell_price=product.sell_price,
        sales_history=[
            SaleHistoryItem(
                sale_date=s.sale_date,
                quantity=s.quantity,
                revenue=s.revenue,
            )
            for s in sales
        ],
    )
