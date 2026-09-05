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


class DimProvider(Base):
    __tablename__ = "dim_provider"

    provider_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    npi: Mapped[str] = mapped_column(String(64), unique=True)
    specialty: Mapped[str] = mapped_column(String(32))
    group_name: Mapped[str] = mapped_column(String(64))

    __table_args__ = (
        CheckConstraint(
            "specialty in ('Primary Care','Cardiology','Orthopedic Surgery','Endocrinology','Oncology')",
            name="ck_provider_specialty",
        ),
    )


class DimRegion(Base):
    __tablename__ = "dim_region"

    region_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    region_code: Mapped[str] = mapped_column(String(16), unique=True)
    name: Mapped[str] = mapped_column(String(64))
    country: Mapped[str] = mapped_column(String(32))


class DimEmployerGroup(Base):
    __tablename__ = "dim_employer_group"

    employer_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employer_code: Mapped[str] = mapped_column(String(16), unique=True)
    name: Mapped[str] = mapped_column(String(64))
    industry: Mapped[str] = mapped_column(String(32))


class DimDate(Base):
    __tablename__ = "dim_date"

    date_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    date: Mapped[date] = mapped_column(Date, unique=True)
    year: Mapped[int] = mapped_column(Integer)
    quarter: Mapped[int] = mapped_column(Integer)
    month: Mapped[int] = mapped_column(Integer)
    week: Mapped[int] = mapped_column(Integer)


class FactClaims(Base):
    """Claims paid to a provider, attributed to an employer group's member population."""

    __tablename__ = "fact_claims"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date_id: Mapped[int] = mapped_column(ForeignKey("dim_date.date_id"))
    provider_id: Mapped[int] = mapped_column(ForeignKey("dim_provider.provider_id"))
    employer_id: Mapped[int] = mapped_column(ForeignKey("dim_employer_group.employer_id"))
    claim_count: Mapped[int] = mapped_column(Integer)
    claims_paid_usd: Mapped[float] = mapped_column(Float)

    __table_args__ = (UniqueConstraint("date_id", "provider_id", "employer_id", name="uq_claims_grain"),)


class FactReferrals(Base):
    """Referrals steered to a provider, and how many were declined -- the
    healthcare-ops analog of a production line's scrap rate: referrals that
    didn't convert into completed care."""

    __tablename__ = "fact_referrals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date_id: Mapped[int] = mapped_column(ForeignKey("dim_date.date_id"))
    provider_id: Mapped[int] = mapped_column(ForeignKey("dim_provider.provider_id"))
    region_id: Mapped[int] = mapped_column(ForeignKey("dim_region.region_id"))
    referrals: Mapped[int] = mapped_column(Integer)
    avg_wait_days: Mapped[float] = mapped_column(Float)
    declined_referrals: Mapped[int] = mapped_column(Integer)

    __table_args__ = (UniqueConstraint("date_id", "provider_id", "region_id", name="uq_referrals_grain"),)


class FactNetworkCapacity(Base):
    """Open panel slots per provider per employer group's member population --
    a closed panel (no open slots) is this warehouse's stockout equivalent."""

    __tablename__ = "fact_network_capacity"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date_id: Mapped[int] = mapped_column(ForeignKey("dim_date.date_id"))
    provider_id: Mapped[int] = mapped_column(ForeignKey("dim_provider.provider_id"))
    employer_id: Mapped[int] = mapped_column(ForeignKey("dim_employer_group.employer_id"))
    open_panel_slots: Mapped[int] = mapped_column(Integer)
    panel_closed_flag: Mapped[bool] = mapped_column(Boolean)

    __table_args__ = (UniqueConstraint("date_id", "provider_id", "employer_id", name="uq_capacity_grain"),)


class FactCareCoordination(Base):
    """Cost of coordinating a member's care across regions -- e.g. a
    specialist consult routed to a different region's network."""

    __tablename__ = "fact_care_coordination"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date_id: Mapped[int] = mapped_column(ForeignKey("dim_date.date_id"))
    region_id: Mapped[int] = mapped_column(ForeignKey("dim_region.region_id"))
    employer_id: Mapped[int] = mapped_column(ForeignKey("dim_employer_group.employer_id"))
    cases: Mapped[int] = mapped_column(Integer)
    coordination_cost_usd: Mapped[float] = mapped_column(Float)

    __table_args__ = (UniqueConstraint("date_id", "region_id", "employer_id", name="uq_coordination_grain"),)
