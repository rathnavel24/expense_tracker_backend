"""
Standalone PostgreSQL connectivity check.

Run from the application root (backend/app/, next to alembic.ini and .env) with the
virtualenv active:

    source ../myenv/bin/activate
    python test_db_connection.py

It reads DATABASE_URL exactly as the app does (app.core.config, i.e. from .env), so a pass
here means the app can connect too. It never prints the password.
"""

import sys

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError, ProgrammingError

from app.core.config import get_settings

HINTS = {
    "password authentication failed": "Wrong username or password in DATABASE_URL.",
    "does not exist": "The database or role doesn't exist. Create it (e.g. `createdb`).",
    "Connection refused": "Nothing is listening on that host/port. Is PostgreSQL running?",
    "could not translate host name": "The host name in DATABASE_URL can't be resolved.",
    "timeout": "The server didn't answer. Check host, port and firewall rules.",
}


def main() -> int:
    settings = get_settings()
    url = make_url(settings.sqlalchemy_url)
    print(f"Connecting to {url.render_as_string(hide_password=True)}")

    engine = create_engine(url, pool_pre_ping=True, connect_args={"connect_timeout": 5})
    try:
        with engine.connect() as conn:
            version = conn.scalar(text("SELECT version()"))
            database = conn.scalar(text("SELECT current_database()"))
            print(f"OK  connected to database {database!r}")
            print(f"    {version}")
            try:
                revision = conn.scalar(text("SELECT version_num FROM alembic_version"))
                print(f"    schema at migration {revision}")
            except ProgrammingError:
                print("    no migrations applied yet - run `alembic upgrade head`")
    except OperationalError as exc:
        message = str(exc.orig) if exc.orig else str(exc)
        print(f"FAIL {message.strip().splitlines()[0]}")
        for needle, hint in HINTS.items():
            if needle.lower() in message.lower():
                print(f"     Hint: {hint}")
                break
        return 1
    finally:
        engine.dispose()
    return 0


if __name__ == "__main__":
    sys.exit(main())
