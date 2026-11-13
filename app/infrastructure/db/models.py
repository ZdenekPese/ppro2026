import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional
from sqlalchemy import (
    Table,
    Column,
    ForeignKey,
    String,
    Text,
    Numeric,
    Integer,
    Boolean,
    DateTime,
    CheckConstraint,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.infrastructure.db.base import Base


# Asociační tabulka pro M:N vazbu mezi produkty a kategoriemi
product_categories = Table(
    "product_categories",
    Base.metadata,
    Column(
        "product_id",
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    ),
    Column(
        "category_id",
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    ),
    Column(
        "created_at",
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    ),
)


class Category(Base):
    """SQLAlchemy ORM entita reprezentující kategorii dřevěných hraček."""

    __tablename__ = "categories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    products: Mapped[list["Product"]] = relationship(
        "Product",
        secondary=product_categories,
        back_populates="categories",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Category(name='{self.name}')>"


class Product(Base):
    """SQLAlchemy ORM entita reprezentující dřevěnou hračku v katalogu."""

    __tablename__ = "products"

    __table_args__ = (
        CheckConstraint("purchase_price >= 0", name="ck_products_purchase_price_non_negative"),
        CheckConstraint("selling_price >= 0", name="ck_products_selling_price_non_negative"),
        CheckConstraint("min_stock_level >= 0", name="ck_products_min_stock_non_negative"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    purchase_price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )
    selling_price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )
    min_stock_level: Mapped[int] = mapped_column(
        Integer,
        default=5,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    categories: Mapped[list["Category"]] = relationship(
        "Category",
        secondary=product_categories,
        back_populates="products",
        lazy="selectin",
    )
    stocks: Mapped[list["WarehouseStock"]] = relationship(
        "WarehouseStock",
        back_populates="product",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    movements: Mapped[list["StockMovement"]] = relationship(
        "StockMovement",
        back_populates="product",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


    @property
    def total_physical_quantity(self) -> int:
        """Celková fyzická zásoba napříč všemi sklady."""
        return sum(s.physical_quantity for s in self.stocks)

    @property
    def total_reserved_quantity(self) -> int:
        """Celková rezervovaná zásoba napříč všemi sklady."""
        return sum(s.reserved_quantity for s in self.stocks)

    @property
    def total_available_quantity(self) -> int:
        """Celková volná (disponibilní) zásoba napříč všemi sklady."""
        return sum(s.available_quantity for s in self.stocks)

    def __repr__(self) -> str:
        return f"<Product(code='{self.code}', name='{self.name}', price={self.selling_price})>"


class Warehouse(Base):
    """SQLAlchemy ORM entita reprezentující sklad (např. Centrální sklad HK nebo Garáž Třebechovice)."""

    __tablename__ = "warehouses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    code: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    location: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    stocks: Mapped[list["WarehouseStock"]] = relationship(
        "WarehouseStock",
        back_populates="warehouse",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Warehouse(code='{self.code}', name='{self.name}', primary={self.is_primary})>"


class WarehouseStock(Base):
    """SQLAlchemy ORM entita skladové zásoby konkrétního produktu na daném skladě."""

    __tablename__ = "warehouse_stocks"

    __table_args__ = (
        CheckConstraint("physical_quantity >= 0", name="ck_warehouse_stocks_physical_non_negative"),
        CheckConstraint("reserved_quantity >= 0", name="ck_warehouse_stocks_reserved_non_negative"),
        CheckConstraint("reserved_quantity <= physical_quantity", name="ck_warehouse_stocks_reserved_le_physical"),
        UniqueConstraint("warehouse_id", "product_id", name="uq_warehouse_stocks_warehouse_product"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    physical_quantity: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    reserved_quantity: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    warehouse: Mapped["Warehouse"] = relationship(
        "Warehouse",
        back_populates="stocks",
        lazy="selectin",
    )
    product: Mapped["Product"] = relationship(
        "Product",
        back_populates="stocks",
        lazy="selectin",
    )

    @property
    def available_quantity(self) -> int:
        """Disponibilní zásoba = Fyzická zásoba - Rezervovaná zásoba."""
        return self.physical_quantity - self.reserved_quantity

    def __repr__(self) -> str:
        return (
            f"<WarehouseStock(warehouse_id={self.warehouse_id}, product_id={self.product_id}, "
            f"phys={self.physical_quantity}, res={self.reserved_quantity})>"
        )


class StockMovement(Base):
    """SQLAlchemy ORM entita pro 100% auditní stopu skladových pohybů (Fáze 5)."""

    __tablename__ = "stock_movements"

    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_stock_movements_quantity_positive"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_warehouse_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    destination_warehouse_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    movement_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True,
    )  # 'receipt', 'dispatch', 'transfer', 'inventory_adjustment'
    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    note: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    reference_code: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )
    performed_by: Mapped[Optional[str]] = mapped_column(
        String(150),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    product: Mapped["Product"] = relationship(
        "Product",
        back_populates="movements",
        lazy="selectin",
    )
    source_warehouse: Mapped[Optional["Warehouse"]] = relationship(
        "Warehouse",
        foreign_keys=[source_warehouse_id],
        lazy="selectin",
    )
    destination_warehouse: Mapped[Optional["Warehouse"]] = relationship(
        "Warehouse",
        foreign_keys=[destination_warehouse_id],
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<StockMovement(type='{self.movement_type}', product_id={self.product_id}, "
            f"qty={self.quantity}, from={self.source_warehouse_id}, to={self.destination_warehouse_id})>"
        )


class Customer(Base):
    """SQLAlchemy ORM entita reprezentující zákazníka e-shopu Dřevěnka s.r.o. (Fáze 6)."""

    __tablename__ = "customers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    first_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    last_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    phone: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    address: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )  # Fyzicky se zákazníci nemažou (historie reklamací dle zadání B)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    orders: Mapped[list["Order"]] = relationship(
        "Order",
        back_populates="customer",
        lazy="selectin",
    )

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def __repr__(self) -> str:
        return f"<Customer(name='{self.full_name}', email='{self.email}')>"


class Order(Base):
    """SQLAlchemy ORM entita reprezentující objednávku dřevěných hraček (Fáze 6)."""

    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    order_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )  # Např. OBJ-2026-0001
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="RESTRICT"),  # Ochrana před smazáním zákazníka
        nullable=False,
        index=True,
    )
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="RESTRICT"),  # Expediční sklad (HK dle ADR 1)
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(30),
        default="RESERVED",
        nullable=False,
        index=True,
    )  # 'NEW', 'RESERVED', 'DISPATCHED', 'CANCELLED'
    total_price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    note: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    dispatched_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    customer: Mapped["Customer"] = relationship(
        "Customer",
        back_populates="orders",
        lazy="selectin",
    )
    warehouse: Mapped["Warehouse"] = relationship(
        "Warehouse",
        lazy="selectin",
    )
    items: Mapped[list["OrderItem"]] = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Order(number='{self.order_number}', status='{self.status}', total={self.total_price})>"


class OrderItem(Base):
    """SQLAlchemy ORM entita položky objednávky s fixovanou prodejní cenou v čase nákupu."""

    __tablename__ = "order_items"

    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_order_items_quantity_positive"),
        CheckConstraint("unit_price >= 0", name="ck_order_items_unit_price_non_negative"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )  # Neměnnost prodejní ceny v objednávce dle zadání B

    order: Mapped["Order"] = relationship(
        "Order",
        back_populates="items",
        lazy="selectin",
    )
    product: Mapped["Product"] = relationship(
        "Product",
        lazy="selectin",
    )

    @property
    def total_price(self) -> Decimal:
        return Decimal(self.quantity) * self.unit_price

    def __repr__(self) -> str:
        return (
            f"<OrderItem(order_id={self.order_id}, product_id={self.product_id}, "
            f"qty={self.quantity}, unit_price={self.unit_price})>"
        )


class User(Base):
    """SQLAlchemy ORM entita oprávněného pracovníka skladu nebo vedení (Jednatel / Skladník)."""

    __tablename__ = "users"

    __table_args__ = (
        CheckConstraint("role IN ('manager', 'warehouse', 'customer')", name="ck_users_valid_role"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    username: Mapped[str] = mapped_column(
        String(60),
        unique=True,
        nullable=False,
        index=True,
    )
    full_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
    )
    role: Mapped[str] = mapped_column(
        String(30),
        default="warehouse",
        nullable=False,
        index=True,
    )  # 'manager' (Jednatel / Manažer), 'warehouse' (Skladník) nebo 'customer' (Zákazník)
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    customer: Mapped[Optional["Customer"]] = relationship(
        "Customer",
        lazy="selectin",
    )
    sessions: Mapped[list["UserSession"]] = relationship(
        "UserSession",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    @property
    def role_label(self) -> str:
        labels = {
            "manager": "Jednatel / Manažer",
            "warehouse": "Skladník",
            "customer": "Zákazník",
        }
        return labels.get(self.role, "Uživatel")

    def __repr__(self) -> str:
        return f"<User(username='{self.username}', role='{self.role}')>"


class UserSession(Base):
    """Databázová session přihlášeného uživatele (token je uložen jako SHA-256 hash)."""

    __tablename__ = "user_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    user: Mapped["User"] = relationship(
        "User",
        back_populates="sessions",
        lazy="selectin",
    )




