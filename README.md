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

### Export parsed index data as Django fixtures

The parsed export can be converted into fixture rows for `IndexEntry`, `IndexEntryLabel`, `Reference`, `ReferenceLocator`, `IndexEntryReference`, and `IndexEntryCrossReference` objects:

```bash
python manage.py export_reference_fixtures parsed-index.json --output fixtures/reference-import.json --manifestation-id 42
```

Use `--manifestation-id` only for a temporary staging link. In a real review workflow you usually want to leave the manifestation unresolved until a human confirms the match.

Each parsed lemma level becomes an `IndexEntry` node, but persons and subjects are handled differently. For `P` entries, level 1 and level 2 are combined into one person node (`surname, given name`), and any further level becomes a subordinate node below that person. For `S` entries, the levels remain hierarchical as parsed. Identical complete paths are reused within an index type, and level metadata participates in that identity check. The parsed `P` (person) and `S` (subject) values are stored on `IndexEntry`, so otherwise identical person and subject paths stay distinct. Parsed parenthetical level metadata is retained in `parsed-index.json` and used for disambiguation, but it is not yet stored in a dedicated database field.

Page references are attached to the deepest node through `IndexEntryReference`. Parsed `see`, `see_also`, and `compare` entries become `IndexEntryCrossReference` rows. A target is linked only when an exact path with the same index type exists; unresolved targets retain their raw target text for review in Django Admin.

The parser treats the final `:\t` sequence in each paragraph as the boundary between lemma and references, distinguishes page-style locator markers `S.`, `Sp.` and `Abb.` from cross-reference markers such as `s.`, `siehe`, `siehe auch`, and `vgl.`, understands anchors like `vor S. 64(B)` and `nach S. 64(B)`, recognizes `passim` as a whole-edition page scope, removes parenthetical lemma metadata from the visible label, strips soft hyphens from normalized text, and captures page reference types such as the implicit `T` plus explicit codes like `B`, `F`, `A`, `Z`, and combinations such as `T+B`.

Each exported lemma level also contains a `sort_key`. A label without an alternative form uses itself as the key. Where alternatives exist, the extractor infers the key conservatively from up to five direct siblings before and after it in the same ODT file, using case-, accent-, punctuation-, and Unicode-insensitive comparisons. The inference considers leading German, English, and Italian articles, `St.` (`Saint` or `Sankt`), `Mc` (`Mac`), and decimal numbers from `0` through `9999` in German, English, and Italian. An uncertain key remains empty and is reported through `--error-output` without dropping the parsed entry. Source files can specify an authoritative key with an annotation such as `[Tausend] 1000 Tränen`; the visible label becomes `1000 Tränen` and the sort key becomes `Tausend Tränen`.

In person indexes, a comma-free name such as `A Fei` is split into surname and given-name levels only when its first word matches the preceding person's family-name sort key. Western names with a comma, including `García Márquez, Gabriel` and `Vaughan Williams, Ralph`, are not split.

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
