from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.models import Customer, Ingredient, Order, Product


class SqlAlchemyRepository[T]:
    model: type[T]

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, entity_id: int) -> T | None:
        return self._session.get(self.model, entity_id)

    def add(self, entity: T) -> T:
        self._session.add(entity)
        # Flush assigns the primary key now, without committing, so callers can
        # reference the new id inside the same unit of work.
        self._session.flush()
        return entity


class SqlAlchemyProductRepository(SqlAlchemyRepository[Product]):
    model = Product

    def get_by_sku(self, sku: str) -> Product | None:
        return self._session.scalar(select(Product).where(Product.sku == sku))

    def list_available(self) -> Sequence[Product]:
        stmt = select(Product).where(Product.is_available.is_(True)).order_by(Product.category, Product.price)
        return self._session.scalars(stmt).all()

    def search(self, text: str) -> Sequence[Product]:
        pattern = f"%{text.strip()}%"
        stmt = (
            select(Product)
            .where(Product.is_available.is_(True), Product.name.ilike(pattern))
            .order_by(Product.name)
        )
        return self._session.scalars(stmt).all()


class SqlAlchemyIngredientRepository(SqlAlchemyRepository[Ingredient]):
    model = Ingredient

    def get_by_name(self, name: str) -> Ingredient | None:
        return self._session.scalar(select(Ingredient).where(Ingredient.name == name))

    def list_all(self) -> Sequence[Ingredient]:
        return self._session.scalars(select(Ingredient).order_by(Ingredient.name)).all()

    def list_below_reorder_level(self) -> Sequence[Ingredient]:
        stmt = (
            select(Ingredient)
            .where(Ingredient.stock_quantity <= Ingredient.reorder_level)
            .order_by(Ingredient.name)
        )
        return self._session.scalars(stmt).all()


class SqlAlchemyCustomerRepository(SqlAlchemyRepository[Customer]):
    model = Customer

    def get_by_phone(self, phone: str) -> Customer | None:
        return self._session.scalar(select(Customer).where(Customer.phone == phone))


class SqlAlchemyOrderRepository(SqlAlchemyRepository[Order]):
    model = Order

    def list_by_customer(self, customer_id: int, limit: int = 10) -> Sequence[Order]:
        stmt = (
            select(Order)
            .where(Order.customer_id == customer_id)
            .order_by(Order.created_at.desc(), Order.id.desc())
            .limit(limit)
        )
        return self._session.scalars(stmt).all()

    def list_between(self, start: datetime, end: datetime) -> Sequence[Order]:
        # Feeds the demand-forecast pipeline: half-open interval avoids double-counting days.
        stmt = (
            select(Order).where(Order.created_at >= start, Order.created_at < end).order_by(Order.created_at)
        )
        return self._session.scalars(stmt).all()
