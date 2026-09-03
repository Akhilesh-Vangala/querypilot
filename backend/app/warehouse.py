from __future__ import annotations

import random
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .auth import hash_password
from .models import (
    AskLog,
    DimDate,
    DimDc,
    DimPlant,
    DimSku,
    FactFreight,
    FactInventory,
    FactProduction,
    FactSales,
    User,
)

N_WEEKS = 80
WEEK_START = date(2025, 1, 6)
RNG_SEED = 42

FAMILIES = ("Daily Disposable", "Monthly", "Toric", "Multifocal", "IOL")

# Family-level scrap is fixed so Toric remains the worst even after per-row noise.
SCRAP_RATE = {
    "Daily Disposable": 0.020,
    "Monthly": 0.025,
    "Toric": 0.085,
    "Multifocal": 0.035,
    "IOL": 0.015,
}

UNIT_PRICE = {
    "Daily Disposable": 0.85,
    "Monthly": 2.40,
    "Toric": 1.55,
    "Multifocal": 1.90,
    "IOL": 420.0,
}

SKUS = [
    (1, "DT1-90", "Daily Disposable", "Dailies Total1"),
    (2, "DT1-30", "Daily Disposable", "Dailies Total1"),
    (3, "P1-90", "Daily Disposable", "Precision1"),
    (4, "AO-M30", "Monthly", "Air Optix"),
    (5, "AO-HYDRA", "Monthly", "Air Optix"),
    (6, "AO-TORIC", "Toric", "Air Optix"),
    (7, "P1-TORIC", "Toric", "Precision1"),
    (8, "DT1-TORIC", "Toric", "Dailies Total1"),
    (9, "DT1-MF", "Multifocal", "Dailies Total1"),
    (10, "AO-MF", "Multifocal", "Air Optix"),
    (11, "CLAREON", "IOL", "Clareon"),
    (12, "VIVITY", "IOL", "Vivity"),
]

PLANTS = [
    (1, "FTW", "Fort Worth", "US"),
    (2, "SGP", "Singapore", "SG"),
]

DCS = [
    (1, "DFW", "Dallas", "Americas"),
    (2, "RTM", "Rotterdam", "EMEA"),
    (3, "SHA", "Shanghai", "APAC"),
]

LANE_COST_PER_UNIT = {
    (1, 1): 0.12,  # FTW -> DFW
    (1, 2): 0.55,  # FTW -> RTM
    (1, 3): 0.80,  # FTW -> SHA
    (2, 1): 0.70,  # SGP -> DFW
    (2, 2): 0.60,  # SGP -> RTM
    (2, 3): 0.18,  # SGP -> SHA
}

DEMO_USERS = [
    ("analyst@querypilot.example.com", "analyst-password", "Ops Analyst", "analyst"),
    ("admin@querypilot.example.com", "admin-password", "Analytics Admin", "admin"),
]

_PASSWORD_HASHES: dict[str, str] = {}


def _cached_hash(password: str) -> str:
    hashed = _PASSWORD_HASHES.get(password)
    if hashed is None:
        hashed = hash_password(password)
        _PASSWORD_HASHES[password] = hashed
    return hashed


def _quarter(month: int) -> int:
    return (month - 1) // 3 + 1


def _seasonal(quarter: int) -> float:
    # Q4 demand is lifted and Q1 is dampened so Q4 revenue > Q1 is a stable pattern.
    if quarter == 4:
        return 1.40
    if quarter == 1:
        return 0.75
    if quarter == 3:
        return 1.10
    return 1.00


def warehouse_is_empty(session: Session) -> bool:
    return session.scalar(select(func.count()).select_from(DimSku)) == 0


def seed_users(session: Session) -> None:
    for email, password, full_name, role in DEMO_USERS:
        existing = session.scalar(select(User).where(User.email == email))
        if existing is None:
            session.add(
                User(
                    email=email,
                    hashed_password=_cached_hash(password),
                    full_name=full_name,
                    role=role,
                )
            )
        else:
            existing.hashed_password = _cached_hash(password)
            existing.full_name = full_name
            existing.role = role
    session.commit()


def seed_warehouse(session: Session) -> None:
    rng = random.Random(RNG_SEED)

    dates = []
    for i in range(N_WEEKS):
        d = WEEK_START + timedelta(weeks=i)
        dates.append(
            DimDate(
                date_id=i + 1,
                date=d,
                year=d.year,
                quarter=_quarter(d.month),
                month=d.month,
                week=d.isocalendar()[1],
            )
        )
    session.add_all(dates)
    session.add_all([DimSku(sku_id=i, sku_code=c, family=f, brand=b) for i, c, f, b in SKUS])
    session.add_all([DimPlant(plant_id=i, plant_code=c, name=n, country=co) for i, c, n, co in PLANTS])
    session.add_all([DimDc(dc_id=i, dc_code=c, name=n, region=r) for i, c, n, r in DCS])
    session.flush()

    sales: list[FactSales] = []
    production: list[FactProduction] = []
    inventory: list[FactInventory] = []
    freight: list[FactFreight] = []

    stockout_by_dc: dict[int, int] = {dc_id: 0 for dc_id, *_ in DCS}

    for date_id in range(1, N_WEEKS + 1):
        d = WEEK_START + timedelta(weeks=date_id - 1)
        season = _seasonal(_quarter(d.month))

        for sku_id, _code, family, _brand in SKUS:
            base = {
                "Daily Disposable": 48000,
                "Monthly": 9000,
                "Toric": 14000,
                "Multifocal": 7000,
                "IOL": 220,
            }[family]
            noise = rng.uniform(0.88, 1.12)

            plants_for_sku = [1, 2]
            if family == "IOL":
                plants_for_sku = [1]

            for plant_id in plants_for_sku:
                units = int(base * noise * season)
                if family == "Daily Disposable":
                    # Fort Worth produces more dailies than Singapore.
                    units = int(units * (1.85 if plant_id == 1 else 1.00))
                elif plant_id == 1:
                    units = int(units * 1.15)
                scrap = int(units * SCRAP_RATE[family] + rng.randint(-8, 8))
                scrap = max(0, min(scrap, max(units - 1, 0)))
                hours = round(units / 1250.0 + rng.uniform(-2.0, 2.0), 2)
                hours = max(hours, 0.5)
                production.append(
                    FactProduction(
                        date_id=date_id,
                        sku_id=sku_id,
                        plant_id=plant_id,
                        units=units,
                        hours=hours,
                        scrap_units=scrap,
                    )
                )

            for dc_id, *_ in DCS:
                dc_share = {1: 0.48, 2: 0.32, 3: 0.20}[dc_id]
                sold = int(base * 0.92 * season * dc_share * rng.uniform(0.9, 1.1))
                price = UNIT_PRICE[family] * rng.uniform(0.97, 1.03)
                sales.append(
                    FactSales(
                        date_id=date_id,
                        sku_id=sku_id,
                        dc_id=dc_id,
                        units=sold,
                        revenue_usd=round(sold * price, 2),
                    )
                )

                closing = int(sold * rng.uniform(0.8, 2.4))
                stockout_p = {1: 0.02, 2: 0.03, 3: 0.06}[dc_id]
                if family == "Toric":
                    stockout_p += 0.04
                stockout = rng.random() < stockout_p
                if stockout:
                    closing = 0
                    stockout_by_dc[dc_id] += 1
                inventory.append(
                    FactInventory(
                        date_id=date_id,
                        sku_id=sku_id,
                        dc_id=dc_id,
                        closing_units=closing,
                        stockout_flag=stockout,
                    )
                )

        for plant_id, *_ in PLANTS:
            for dc_id, *_ in DCS:
                shipped = int(18000 * rng.uniform(0.7, 1.3) * season * (1.2 if plant_id == 1 else 0.9))
                rate = LANE_COST_PER_UNIT[(plant_id, dc_id)] * rng.uniform(0.95, 1.05)
                freight.append(
                    FactFreight(
                        date_id=date_id,
                        plant_id=plant_id,
                        dc_id=dc_id,
                        units=max(shipped, 1),
                        cost_usd=round(shipped * rate, 2),
                    )
                )

    # Guarantee every DC has at least one stockout week so the golden question is non-empty.
    for dc_id, count in stockout_by_dc.items():
        if count == 0:
            for row in inventory:
                if row.dc_id == dc_id:
                    row.stockout_flag = True
                    row.closing_units = 0
                    break

    session.add_all(sales)
    session.add_all(production)
    session.add_all(inventory)
    session.add_all(freight)
    session.commit()


def seed_all(session: Session, *, refresh_warehouse: bool = False) -> None:
    if refresh_warehouse:
        session.query(FactFreight).delete()
        session.query(FactInventory).delete()
        session.query(FactProduction).delete()
        session.query(FactSales).delete()
        session.query(AskLog).delete()
        session.query(DimDate).delete()
        session.query(DimSku).delete()
        session.query(DimPlant).delete()
        session.query(DimDc).delete()
        session.commit()
    if warehouse_is_empty(session):
        seed_warehouse(session)
    seed_users(session)
