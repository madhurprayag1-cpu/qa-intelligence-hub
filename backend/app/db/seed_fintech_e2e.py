"""Seed deterministic FinTech accounts for the isolated Playwright E2E database."""

import argparse
from decimal import Decimal

from sqlalchemy import select

from app.core.auth import DEMO_USERS
from app.db.database import SessionLocal
from app.models.fintech import FinTechAccountModel


E2E_ACCOUNT_COUNT = 2
E2E_PASSENGER_EMAIL = "passenger@qahub.io"
E2E_ACCOUNTS = (
    {
        "account_id": "ACC-FT-E2E-001",
        "iban": "US00QAHUB0000000000000001",
        "bic_swift": "QAHBUS00XXX",
        "account_holder": "Alice Passenger E2E Checking",
        "email": E2E_PASSENGER_EMAIL,
        "account_type": "CHECKING",
        "currency": "USD",
        "balance": Decimal("10000.00"),
        "kyc_tier": "TIER_2_VERIFIED",
        "is_active": True,
    },
    {
        "account_id": "ACC-FT-E2E-002",
        "iban": "US00QAHUB0000000000000002",
        "bic_swift": "QAHBUS00XXX",
        "account_holder": "Alice Passenger E2E Savings",
        "email": E2E_PASSENGER_EMAIL,
        "account_type": "SAVINGS",
        "currency": "USD",
        "balance": Decimal("25000.00"),
        "kyc_tier": "TIER_2_VERIFIED",
        "is_active": True,
    },
)


def seed_fintech_e2e_accounts() -> int:
    """Ensure the demo passenger owns at least two active persistent accounts.

    Existing records are preserved. The fixed identifiers make repeated runs
    idempotent, while ownership and activity checks prevent a stale or
    misassigned row from being silently treated as valid E2E setup.

    The E2E database must already have been migrated before invoking this
    function. Do not use it to initialize production or demo environments.
    """
    passenger_id = int(DEMO_USERS[E2E_PASSENGER_EMAIL]["id"])
    db = SessionLocal()
    try:
        owned_account_ids = db.execute(
            select(FinTechAccountModel.account_id).where(
                FinTechAccountModel.owner_user_id == passenger_id,
                FinTechAccountModel.is_active.is_(True),
            )
        ).scalars().all()

        for account_data in E2E_ACCOUNTS:
            if len(owned_account_ids) >= E2E_ACCOUNT_COUNT:
                break

            existing = db.get(FinTechAccountModel, account_data["account_id"])
            if existing is not None:
                if existing.owner_user_id != passenger_id:
                    raise RuntimeError(
                        f"E2E account {existing.account_id} exists with unexpected ownership"
                    )
                if not existing.is_active:
                    existing.is_active = True
            else:
                db.add(
                    FinTechAccountModel(
                        **account_data,
                        owner_user_id=passenger_id,
                    )
                )

            owned_account_ids.append(account_data["account_id"])

        db.commit()

        final_count = db.execute(
            select(FinTechAccountModel.account_id).where(
                FinTechAccountModel.owner_user_id == passenger_id,
                FinTechAccountModel.is_active.is_(True),
            )
        ).scalars().all()
        if len(final_count) < E2E_ACCOUNT_COUNT:
            raise RuntimeError(
                f"FinTech E2E seed expected at least {E2E_ACCOUNT_COUNT} active passenger accounts; "
                f"found {len(final_count)}"
            )

        print(
            f"FinTech E2E seed verified {len(final_count)} active accounts "
            f"for {E2E_PASSENGER_EMAIL} (user_id={passenger_id})."
        )
        return len(final_count)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed deterministic FinTech accounts in the Playwright E2E database."
    )
    parser.add_argument(
        "--e2e",
        action="store_true",
        help="explicitly confirm this command is being run for an E2E environment",
    )
    args = parser.parse_args()
    if not args.e2e:
        parser.error("refusing to seed without the explicit --e2e confirmation")
    seed_fintech_e2e_accounts()


if __name__ == "__main__":
    main()