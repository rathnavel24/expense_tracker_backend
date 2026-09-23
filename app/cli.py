"""Account management. There is no public sign-up; create your user from the terminal:

uv run python -m app.cli create-user --email you@example.com --name "Your Name"
uv run python -m app.cli set-password --email you@example.com
"""

import argparse
import getpass
import sys

from app.db.session import SessionLocal
from app.services import auth

MIN_PASSWORD_LENGTH = 10


def _prompt_password() -> str:
    password = getpass.getpass("Password: ")
    if len(password) < MIN_PASSWORD_LENGTH:
        sys.exit(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
    if getpass.getpass("Confirm password: ") != password:
        sys.exit("Passwords do not match.")
    return password


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    commands = parser.add_subparsers(dest="command", required=True)

    create = commands.add_parser("create-user", help="Create a user account")
    create.add_argument("--email", required=True)
    create.add_argument("--name", required=True)

    reset = commands.add_parser("set-password", help="Change a password (signs out everywhere)")
    reset.add_argument("--email", required=True)

    args = parser.parse_args()
    password = _prompt_password()
    with SessionLocal() as db:
        try:
            if args.command == "create-user":
                user = auth.create_user(db, email=args.email, name=args.name, password=password)
                print(f"Created user {user.email}.")
            else:
                auth.set_password(db, email=args.email, password=password)
                print("Password updated. All sessions have been signed out.")
        except ValueError as exc:
            sys.exit(str(exc))


if __name__ == "__main__":
    main()
