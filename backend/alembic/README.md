# Database Migrations (Alembic)

This project uses [Alembic](https://alembic.sqlalchemy.org/) to manage schema
changes in a versioned, repeatable way instead of relying only on
`Base.metadata.create_all()` (which only ever creates missing tables - it
never alters or drops existing ones).

`alembic/env.py` reads your real `DATABASE_URL` straight from `app/core/config.py`
(i.e. your `.env` file), so you never need to edit a connection string in two
places.

## First-time setup (do this once, after configuring `.env` for MySQL)

From the `backend/` directory, with your virtual environment active and
`DATABASE_URL` in `.env` already pointing at your MySQL database:

```bash
# Generate the first migration by diffing the models against an empty DB
alembic revision --autogenerate -m "initial schema"

# Apply it - this actually creates the tables in MySQL
alembic upgrade head
```

Open the generated file under `alembic/versions/` before running `upgrade`
and skim it - autogenerate is very good but not infallible (it won't detect
some renames, for example), so it's worth a quick sanity check the first time.

## Whenever you change a model afterwards

```bash
alembic revision --autogenerate -m "add followup notes column"
alembic upgrade head
```

## Other useful commands

```bash
alembic current          # show which migration the DB is currently at
alembic history           # list all migrations
alembic downgrade -1       # roll back the most recent migration
```

## Note on SQLite (local dev default)

If you're still using the default SQLite `DATABASE_URL`, you don't need
Alembic at all - `init_db()` (called automatically on startup) will just
create the file and tables for you. Alembic becomes relevant the moment
you switch to MySQL/Postgres and want real, trackable schema history.
