"""Lock every table against direct client access (Supabase Data API).

On Supabase, tables in `public` are exposed through the auto-generated REST/GraphQL API to
the `anon` and `authenticated` roles (i.e. anyone holding the publishable key). This app
never uses that API: the FastAPI backend connects to Postgres directly as the table owner.
So we:

1. enable row level security with *no* policies on every table - the API roles can read and
   write nothing, while the owner (the backend) is unaffected;
2. revoke those roles' privileges on the tables and sequences;
3. stop Supabase's default privileges from granting them anything on future tables.

Steps 2-3 only run where those roles exist (Supabase); on plain Postgres they're skipped.
Any future migration that creates a table must also `ENABLE ROW LEVEL SECURITY` on it.

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-24
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = (
    "users",
    "auth_sessions",
    "categories",
    "transactions",
    "recurring_rules",
    "alembic_version",
)

_API_ROLES_EXIST = (
    "EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') "
    "AND EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated')"
)


def upgrade() -> None:
    for table in TABLES:
        op.execute(f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY")

    op.execute(
        f"""
        DO $$
        BEGIN
          IF {_API_ROLES_EXIST} THEN
            REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon, authenticated;
            REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM anon, authenticated;
            ALTER DEFAULT PRIVILEGES IN SCHEMA public
              REVOKE ALL ON TABLES FROM anon, authenticated;
            ALTER DEFAULT PRIVILEGES IN SCHEMA public
              REVOKE ALL ON SEQUENCES FROM anon, authenticated;
            ALTER DEFAULT PRIVILEGES IN SCHEMA public
              REVOKE ALL ON FUNCTIONS FROM anon, authenticated;
          END IF;
        END
        $$;
        """
    )


def downgrade() -> None:
    # Privileges are not re-granted: exposing tables to the Data API was never intended.
    for table in TABLES:
        op.execute(f"ALTER TABLE public.{table} DISABLE ROW LEVEL SECURITY")
