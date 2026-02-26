# sda-book-index

A multilingual book index application built with Django and PostgreSQL.

## Overview

This application provides a Django Admin interface for managing a multilingual book index, including:

- **Books** with multilingual titles (BCP-47 language tags)
- **People** with multilingual names
- **Subjects** with hierarchical parent/child relationships and multilingual labels
- **References** pointing to page ranges within books
- **Index entries** — hierarchical headings (up to 3 levels deep) with multilingual labels and attached references

---

## Data Model

### Index entries

`IndexEntry` represents a hierarchical index heading with up to 3 levels:

- **Level 1** — root entry (no parent), e.g. a family name or main subject
- **Level 2** — child of a level-1 entry, e.g. a given name or secondary subject
- **Level 3** — grandchild of a level-1 entry, e.g. a subject heading under a person or a tertiary subject

References can be attached to entries at any level via `IndexEntryReference`.

Multilingual labels are stored in `IndexEntryLabel` (BCP-47 language tag, optional sort key).

---

## Local Development Setup

### 1. Start PostgreSQL via Docker Compose

```bash
docker compose up -d
```

This starts a PostgreSQL 16 container with the credentials defined in `docker-compose.yml`.

### 2. Create and activate a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Copy the example file and adjust values if needed:

```bash
cp .env.example .env
```

To load the `.env` file into your shell session you can use:

```bash
export $(grep -v '^#' .env | xargs)
```

Or use a tool like [python-dotenv](https://pypi.org/project/python-dotenv/) in your workflow.

### 5. Run migrations

```bash
python manage.py migrate
```

### 6. Create a superuser

```bash
python manage.py createsuperuser
```

### 7. Start the development server

```bash
python manage.py runserver
```

Then open <http://127.0.0.1:8000/admin/> in your browser and log in with the superuser credentials.

---

## Environment Variables

| Variable        | Default                          | Description                           |
|-----------------|----------------------------------|---------------------------------------|
| `SECRET_KEY`    | insecure dev key                 | Django secret key (change in prod)    |
| `DEBUG`         | `true`                           | Enable debug mode (`true`/`false`)    |
| `ALLOWED_HOSTS` | `127.0.0.1,localhost`            | Comma-separated list of allowed hosts |
| `DB_NAME`       | `sda_book_index`                 | PostgreSQL database name              |
| `DB_USER`       | `sda`                            | PostgreSQL user                       |
| `DB_PASSWORD`   | `sda`                            | PostgreSQL password                   |
| `DB_HOST`       | `127.0.0.1`                      | PostgreSQL host                       |
| `DB_PORT`       | `5432`                           | PostgreSQL port                       |

See `.env.example` for a template.

---

## Loading Sample Data (Optional)

You can create objects directly in the Django Admin UI, or load fixtures:

```bash
python manage.py loaddata <fixture_file>.json
```

---

## Project Structure

```
sda_book_index/   Django project settings, urls, wsgi, asgi
indexer/          Core app: models, admin, migrations
docker-compose.yml  PostgreSQL service for development
requirements.txt    Python dependencies
.env.example        Environment variable template
```
