# sda-book-index

A multilingual book index application built with Django and PostgreSQL.

## Overview

This application provides a Django Admin interface for managing a multilingual book index, including:

- **Books** with multilingual titles (BCP-47 language tags)
- **People** with multilingual names
- **People** with external identifiers such as GND, ISNI, and ORCID
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

## ODT Index Extraction

The repository now includes a parser for ODT index paragraphs plus a management command for exporting structured JSON from source files named `Index*.odt` and `Sachregister*.odt`.

```bash
python manage.py extract_odt_index /path/to/odt/folder --pretty --output parsed-index.json
```

To collect unparsable source paragraphs for manual correction in the ODT files:

```bash
python manage.py extract_odt_index /path/to/odt/folder --pretty --output parsed-index.json --error-output odt-parse-errors.txt
```

To extract likely legacy `s.` / `siehe` cross-references whose target lemma should be rewritten with square brackets because it contains a semicolon:

```bash
python manage.py suggest_bracketed_crossrefs odt-parse-errors.txt --output odt-crossref-bracket-suggestions.txt
```

### Export parsed references as Django fixtures

The parsed export can be converted into fixture rows for `Reference` and `ReferenceLocator` objects so it can be imported into the database as a staging dataset before manual manifestation matching:

```bash
python manage.py export_reference_fixtures parsed-index.json --output fixtures/reference-import.json --manifestation-id 42
```

Use `--manifestation-id` only for a temporary staging link. In a real review workflow you usually want to leave the manifestation unresolved until a human confirms the match.

### Generate manifestation matching suggestions

Once the parsed references are in the database, generate ranked candidate manifestations for each reference:

```bash
python manage.py suggest_manifestation_matches --limit 5 --min-score 60 --clear-existing
```

To limit the run to one specific reference:

```bash
python manage.py suggest_manifestation_matches --reference-id 123 --limit 5 --min-score 60
```

This stores scored `ManifestationSuggestion` rows with `score`, `match_type`, and `status`, which can then be reviewed and confirmed in the admin.

The parser treats the final `:\t` sequence in each paragraph as the boundary between lemma and references, distinguishes page-style locator markers `S.`, `Sp.` and `Abb.` from cross-reference markers such as `s.`, `siehe`, `siehe auch`, and `vgl.`, understands anchors like `vor S. 64(B)` and `nach S. 64(B)`, recognizes `passim` as a whole-edition page scope, removes parenthetical lemma metadata from the visible label, strips soft hyphens from normalized text, and captures page reference types such as the implicit `T` plus explicit codes like `B`, `F`, `A`, `Z`, and combinations such as `T+B`.

For page relations, the implicit default is `on`: the export only writes `page_start_relation` and `page_end_relation` when the source explicitly says `vor` or `nach`, and the Django model stores `on` as an empty value to avoid writing it redundantly.

For cross-references whose target lemma itself contains a semicolon, the preferred source format is `siehe [Lemma; Unterlemma]`. The parser treats semicolons inside square brackets as part of the target lemma instead of splitting them into separate references.

The EBNF description and parser assumptions are documented in `docs/odt-index-format.md`.
The proposed database redesign for parsed references and cross-references is documented in `docs/reference-schema-design.md`.

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

You can create objects directly in the Django Admin UI, or load fixtures.
`WorkTitle` and `WorkContribution` use externally supplied string primary keys rather than auto-incrementing integers, so imported records should include explicit IDs for those models.
The project is configured to search the top-level `fixtures/` directory automatically, so you can refer to fixture names without a path or file extension:

```bash
python manage.py loaddata Agent
python manage.py loaddata Work WorkTitle Manifestation
```

If both `Agent.json` and `Agent.xml` exist, `python manage.py loaddata Agent` is ambiguous and Django will abort the load. In that case, specify the format explicitly:

```bash
python manage.py loaddata Agent.json
python manage.py loaddata Agent.xml
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
