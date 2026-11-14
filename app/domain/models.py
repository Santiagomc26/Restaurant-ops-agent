from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.domain.enums import OrderChannel, OrderStatus, ProductCategory, UnitOfMeasure


def _enum(enum_cls: type) -> Enum:
    # Stored as VARCHAR + CHECK instead of a native PostgreSQL ENUM type:
    # adding a new status later is a plain migration, and SQLite behaves the same.
    return Enum(enum_cls, native_enum=False, length=30, values_callable=lambda e: [m.value for m in e])


class Ingredient(Base):
    __tablename__ = "ingredients"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    unit: Mapped[UnitOfMeasure] = mapped_column(_enum(UnitOfMeasure))
    stock_quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    reorder_level: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))

    @property
    def needs_reorder(self) -> bool:
        return self.stock_quantity <= self.reorder_level

    def has_stock_for(self, quantity: Decimal) -> bool:
        return self.stock_quantity >= quantity

    def consume(self, quantity: Decimal) -> None:
        if not self.has_stock_for(quantity):
            raise ValueError(f"Insufficient stock for '{self.name}'")
        self.stock_quantity -= quantity


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    sku: Mapped[str] = mapped_column(String(30), unique=True)
    name: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(String(255), default="")
    category: Mapped[ProductCategory] = mapped_column(_enum(ProductCategory))
    # Colombian pesos have no cents in practice, so prices are whole integers.
    price: Mapped[int]
    is_available: Mapped[bool] = mapped_column(default=True)

    recipe: Mapped[list["RecipeItem"]] = relationship(
        back_populates="product", cascade="all, delete-orphan", lazy="selectin"
    )


class RecipeItem(Base):
    __tablename__ = "recipe_items"
    __table_args__ = (UniqueConstraint("product_id", "ingredient_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    ingredient_id: Mapped[int] = mapped_column(ForeignKey("ingredients.id"))
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2))

    product: Mapped[Product] = relationship(back_populates="recipe")
    ingredient: Mapped[Ingredient] = relationship(lazy="joined")


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    # E.164 format (e.g. 573001234567) is the identifier WhatsApp sends in webhooks.
    phone: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    name: Mapped[str | None] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    orders: Mapped[list["Order"]] = relationship(back_populates="customer")


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    status: Mapped[OrderStatus] = mapped_column(_enum(OrderStatus), default=OrderStatus.PENDING, index=True)
    channel: Mapped[OrderChannel] = mapped_column(_enum(OrderChannel))
    total: Mapped[int] = mapped_column(default=0)
    notes: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    customer: Mapped[Customer] = relationship(back_populates="orders")
    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan", lazy="selectin"
    )

    def add_item(self, product: Product, quantity: int, notes: str = "") -> "OrderItem":
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        # The price is copied at order time so later menu price changes
        # never alter historical orders or the demand-forecast dataset.
        item = OrderItem(product=product, quantity=quantity, unit_price=product.price, notes=notes)
        self.items.append(item)
        self.total = sum(i.subtotal for i in self.items)
        return item


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    quantity: Mapped[int]
    unit_price: Mapped[int]
    notes: Mapped[str] = mapped_column(String(255), default="")

    order: Mapped[Order] = relationship(back_populates="items")
    product: Mapped[Product] = relationship(lazy="joined")

    @property
    def subtotal(self) -> int:
        return self.quantity * self.unit_price
