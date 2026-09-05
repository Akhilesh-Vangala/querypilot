from __future__ import annotations

import random
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .auth import hash_password
from .models import (
    AskLog,
    DimDate,
    DimEmployerGroup,
    DimProvider,
    DimRegion,
    FactCareCoordination,
    FactClaims,
    FactNetworkCapacity,
    FactReferrals,
    User,
)

N_WEEKS = 80
WEEK_START = date(2025, 1, 6)
RNG_SEED = 42

SPECIALTIES = ("Primary Care", "Cardiology", "Orthopedic Surgery", "Endocrinology", "Oncology")

# Specialty-level decline rate is fixed so Orthopedic Surgery remains the
# worst even after per-row noise -- referrals to ortho surgeons are
# realistically harder to convert (prior-auth, scheduling backlogs).
DECLINE_RATE = {
    "Primary Care": 0.020,
    "Cardiology": 0.025,
    "Orthopedic Surgery": 0.085,
    "Endocrinology": 0.035,
    "Oncology": 0.015,
}

AVG_CLAIM_USD = {
    "Primary Care": 145.0,
    "Cardiology": 410.0,
    "Orthopedic Surgery": 620.0,
    "Endocrinology": 260.0,
    "Oncology": 3800.0,
}

PROVIDERS = [
    (1, "1003800001", "Primary Care", "Meridian Family Health"),
    (2, "1003800002", "Primary Care", "Meridian Family Health"),
    (3, "1003800003", "Primary Care", "Lakeside Primary Care"),
    (4, "1003800004", "Cardiology", "Heartland Cardiology Group"),
    (5, "1003800005", "Cardiology", "Heartland Cardiology Group"),
    (6, "1003800006", "Orthopedic Surgery", "Summit Orthopedic Partners"),
    (7, "1003800007", "Orthopedic Surgery", "Bayview Orthopedics"),
    (8, "1003800008", "Orthopedic Surgery", "Summit Orthopedic Partners"),
    (9, "1003800009", "Endocrinology", "Metro Endocrine Associates"),
    (10, "1003800010", "Endocrinology", "Metro Endocrine Associates"),
    (11, "1003800011", "Oncology", "Riverside Oncology Center"),
    (12, "1003800012", "Oncology", "Crestview Cancer Institute"),
]

REGIONS = [
    (1, "NE", "Northeast", "US"),
    (2, "WC", "West Coast", "US"),
]

EMPLOYER_GROUPS = [
    (1, "ACME", "Acme Manufacturing", "Manufacturing"),
    (2, "NORTHWIND", "Northwind Retail", "Retail"),
    (3, "VERTEX", "Vertex Technologies", "Technology"),
]

COORDINATION_COST_PER_CASE = {
    (1, 1): 12.0,  # NE region, Acme members
    (1, 2): 55.0,  # NE region, Northwind members
    (1, 3): 80.0,  # NE region, Vertex members
    (2, 1): 70.0,  # WC region, Acme members
    (2, 2): 60.0,  # WC region, Northwind members
    (2, 3): 18.0,  # WC region, Vertex members
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
    # Q4 claims volume is lifted (deductibles met, elective care scheduled
    # before year-end) and Q1 is dampened -- a stable, realistic pattern.
    if quarter == 4:
        return 1.40
    if quarter == 1:
        return 0.75
    if quarter == 3:
        return 1.10
    return 1.00


def warehouse_is_empty(session: Session) -> bool:
    return session.scalar(select(func.count()).select_from(DimProvider)) == 0


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
    session.add_all(
        [DimProvider(provider_id=i, npi=n, specialty=s, group_name=g) for i, n, s, g in PROVIDERS]
    )
    session.add_all([DimRegion(region_id=i, region_code=c, name=n, country=co) for i, c, n, co in REGIONS])
    session.add_all(
        [DimEmployerGroup(employer_id=i, employer_code=c, name=n, industry=ind) for i, c, n, ind in EMPLOYER_GROUPS]
    )
    session.flush()

    claims: list[FactClaims] = []
    referrals: list[FactReferrals] = []
    capacity: list[FactNetworkCapacity] = []
    coordination: list[FactCareCoordination] = []

    closed_panel_by_employer: dict[int, int] = {employer_id: 0 for employer_id, *_ in EMPLOYER_GROUPS}

    for date_id in range(1, N_WEEKS + 1):
        d = WEEK_START + timedelta(weeks=date_id - 1)
        season = _seasonal(_quarter(d.month))

        for provider_id, _npi, specialty, _group in PROVIDERS:
            base = {
                "Primary Care": 48000,
                "Cardiology": 9000,
                "Orthopedic Surgery": 14000,
                "Endocrinology": 7000,
                "Oncology": 220,
            }[specialty]
            noise = rng.uniform(0.88, 1.12)

            regions_for_provider = [1, 2]
            if specialty == "Oncology":
                regions_for_provider = [1]

            for region_id in regions_for_provider:
                vol = int(base * noise * season)
                if specialty == "Primary Care":
                    # Northeast has denser primary-care networks than West Coast.
                    vol = int(vol * (1.85 if region_id == 1 else 1.00))
                elif region_id == 1:
                    vol = int(vol * 1.15)
                declined = int(vol * DECLINE_RATE[specialty] + rng.randint(-8, 8))
                declined = max(0, min(declined, max(vol - 1, 0)))
                wait_days = round(vol / 1250.0 + rng.uniform(-2.0, 2.0), 2)
                wait_days = max(wait_days, 0.5)
                referrals.append(
                    FactReferrals(
                        date_id=date_id,
                        provider_id=provider_id,
                        region_id=region_id,
                        referrals=vol,
                        avg_wait_days=wait_days,
                        declined_referrals=declined,
                    )
                )

            for employer_id, *_ in EMPLOYER_GROUPS:
                employer_share = {1: 0.48, 2: 0.32, 3: 0.20}[employer_id]
                claim_count = int(base * 0.92 * season * employer_share * rng.uniform(0.9, 1.1))
                avg_cost = AVG_CLAIM_USD[specialty] * rng.uniform(0.97, 1.03)
                claims.append(
                    FactClaims(
                        date_id=date_id,
                        provider_id=provider_id,
                        employer_id=employer_id,
                        claim_count=claim_count,
                        claims_paid_usd=round(claim_count * avg_cost, 2),
                    )
                )

                open_slots = int(claim_count * rng.uniform(0.8, 2.4))
                closed_p = {1: 0.02, 2: 0.03, 3: 0.06}[employer_id]
                if specialty == "Orthopedic Surgery":
                    closed_p += 0.04
                panel_closed = rng.random() < closed_p
                if panel_closed:
                    open_slots = 0
                    closed_panel_by_employer[employer_id] += 1
                capacity.append(
                    FactNetworkCapacity(
                        date_id=date_id,
                        provider_id=provider_id,
                        employer_id=employer_id,
                        open_panel_slots=open_slots,
                        panel_closed_flag=panel_closed,
                    )
                )

        for region_id, *_ in REGIONS:
            for employer_id, *_ in EMPLOYER_GROUPS:
                case_volume = int(18000 * rng.uniform(0.7, 1.3) * season * (1.2 if region_id == 1 else 0.9))
                rate = COORDINATION_COST_PER_CASE[(region_id, employer_id)] * rng.uniform(0.95, 1.05)
                coordination.append(
                    FactCareCoordination(
                        date_id=date_id,
                        region_id=region_id,
                        employer_id=employer_id,
                        cases=max(case_volume, 1),
                        coordination_cost_usd=round(case_volume * rate, 2),
                    )
                )

    # Guarantee every employer group has at least one closed-panel week so
    # the golden question is non-empty.
    for employer_id, count in closed_panel_by_employer.items():
        if count == 0:
            for row in capacity:
                if row.employer_id == employer_id:
                    row.panel_closed_flag = True
                    row.open_panel_slots = 0
                    break

    session.add_all(claims)
    session.add_all(referrals)
    session.add_all(capacity)
    session.add_all(coordination)
    session.commit()


def seed_all(session: Session, *, refresh_warehouse: bool = False) -> None:
    if refresh_warehouse:
        session.query(FactCareCoordination).delete()
        session.query(FactNetworkCapacity).delete()
        session.query(FactReferrals).delete()
        session.query(FactClaims).delete()
        session.query(AskLog).delete()
        session.query(DimDate).delete()
        session.query(DimProvider).delete()
        session.query(DimRegion).delete()
        session.query(DimEmployerGroup).delete()
        session.commit()
    if warehouse_is_empty(session):
        seed_warehouse(session)
    seed_users(session)
