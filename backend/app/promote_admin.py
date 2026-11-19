import argparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import engine
from .models import User


def main():
    parser = argparse.ArgumentParser(description="Assign the administrator role to a Shopwise AI account")
    parser.add_argument("email")
    parser.add_argument("--confirm-owner", action="store_true", help="Confirm you independently checked the account owner's identity")
    arguments = parser.parse_args()
    with Session(engine) as db:
        user = db.scalar(select(User).where(User.email == arguments.email.strip().lower()))
        if user is None:
            parser.error("No user has this email")
        if not user.verified and not arguments.confirm_owner:
            parser.error("Check the account owner's identity independently, then pass --confirm-owner")
        user.role = "admin"
        db.commit()
    print("Administrator role assigned.")


if __name__ == "__main__":
    main()
