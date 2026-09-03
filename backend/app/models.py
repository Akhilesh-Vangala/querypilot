from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(32), default="analyst")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (CheckConstraint("role in ('analyst','admin')", name="ck_user_role"),)


class AskLog(Base):
    __tablename__ = "ask_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    question: Mapped[str] = mapped_column(Text)
    sql: Mapped[str] = mapped_column(Text, default="")
    answer: Mapped[str] = mapped_column(Text, default="")
    refused: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class DimSku(Base):
    __tablename__ = "dim_sku"

    sku_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sku_code: Mapped[str] = mapped_column(String(64), unique=True)
    family: Mapped[str] = mapped_column(String(32))
    brand: Mapped[str] = mapped_column(String(64))

    __table_args__ = (
        CheckConstraint(
            "family in ('Daily Disposable','Monthly','Toric','Multifocal','IOL')",
            name="ck_sku_family",
        ),
    )


class DimPlant(Base):
    __tablename__ = "dim_plant"

    plant_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plant_code: Mapped[str] = mapped_column(String(16), unique=True)
    name: Mapped[str] = mapped_column(String(64))
    country: Mapped[str] = mapped_column(String(32))


class DimDc(Base):
    __tablename__ = "dim_dc"

    dc_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dc_code: Mapped[str] = mapped_column(String(16), unique=True)
    name: Mapped[str] = mapped_column(String(64))
    region: Mapped[str] = mapped_column(String(32))


class DimDate(Base):
    __tablename__ = "dim_date"

    date_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    date: Mapped[date] = mapped_column(Date, unique=True)
    year: Mapped[int] = mapped_column(Integer)
    quarter: Mapped[int] = mapped_column(Integer)
    month: Mapped[int] = mapped_column(Integer)
    week: Mapped[int] = mapped_column(Integer)


class FactSales(Base):
    __tablename__ = "fact_sales"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date_id: Mapped[int] = mapped_column(ForeignKey("dim_date.date_id"))
    sku_id: Mapped[int] = mapped_column(ForeignKey("dim_sku.sku_id"))
    dc_id: Mapped[int] = mapped_column(ForeignKey("dim_dc.dc_id"))
    units: Mapped[int] = mapped_column(Integer)
    revenue_usd: Mapped[float] = mapped_column(Float)

    __table_args__ = (UniqueConstraint("date_id", "sku_id", "dc_id", name="uq_sales_grain"),)


class FactProduction(Base):
    __tablename__ = "fact_production"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date_id: Mapped[int] = mapped_column(ForeignKey("dim_date.date_id"))
    sku_id: Mapped[int] = mapped_column(ForeignKey("dim_sku.sku_id"))
    plant_id: Mapped[int] = mapped_column(ForeignKey("dim_plant.plant_id"))
    units: Mapped[int] = mapped_column(Integer)
    hours: Mapped[float] = mapped_column(Float)
    scrap_units: Mapped[int] = mapped_column(Integer)

    __table_args__ = (UniqueConstraint("date_id", "sku_id", "plant_id", name="uq_production_grain"),)


class FactInventory(Base):
    __tablename__ = "fact_inventory"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date_id: Mapped[int] = mapped_column(ForeignKey("dim_date.date_id"))
    sku_id: Mapped[int] = mapped_column(ForeignKey("dim_sku.sku_id"))
    dc_id: Mapped[int] = mapped_column(ForeignKey("dim_dc.dc_id"))
    closing_units: Mapped[int] = mapped_column(Integer)
    stockout_flag: Mapped[bool] = mapped_column(Boolean)

    __table_args__ = (UniqueConstraint("date_id", "sku_id", "dc_id", name="uq_inventory_grain"),)


class FactFreight(Base):
    __tablename__ = "fact_freight"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date_id: Mapped[int] = mapped_column(ForeignKey("dim_date.date_id"))
    plant_id: Mapped[int] = mapped_column(ForeignKey("dim_plant.plant_id"))
    dc_id: Mapped[int] = mapped_column(ForeignKey("dim_dc.dc_id"))
    units: Mapped[int] = mapped_column(Integer)
    cost_usd: Mapped[float] = mapped_column(Float)

    __table_args__ = (UniqueConstraint("date_id", "plant_id", "dc_id", name="uq_freight_grain"),)
