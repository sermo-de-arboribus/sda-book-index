# Reference Schema Design

## Goal

The current `Reference` model is still page-range-centric, while the parser now recognizes:

- page references via `S.`
- column references via `Sp.`
- figure references via `Abb.`
- anchored locators such as `vor S. 64(B)` and `nach S. 64(B)`
- whole-work locators such as `passim`
- per-locator reference types `T`, `B`, `F`, `A`, `Z`
- cross-references between index entries (`s.`, `siehe`, `siehe auch`, `vgl.`)

The schema should represent these cases without forcing everything into `page_start` / `page_end`.

## Design Principles

- `Reference` should represent one bibliographic reference block to one manifestation.
- Individual locators should move into a child table.
- Cross-references between index entries should be modeled separately from document references.
- Implicit defaults should be stored compactly:
  - empty string means `page`
  - empty string means relation `on`
  - empty string means normal numeric locator scope
  - empty string means implicit reference type `T`
- Raw source text should be preserved so import remains reversible.

## Target Schema

### 1. Reference

Represents one normalized bibliographic reference block to a manifestation.

Example:

```text
Ewing, W. A.: "Blumenfeld. A Fetish for Beauty", S. 97, 103; Abb. 135
```

This should become one `Reference` row, with multiple child locators.

Proposed fields:

```python
class Reference(models.Model):
    manifestation = models.ForeignKey(
        Manifestation,
        on_delete=models.CASCADE,
        related_name='references',
        db_index=True,
    )
    raw_reference = models.TextField(blank=True)
    raw_document = models.CharField(max_length=1000, blank=True)
    source_file = models.CharField(max_length=255, blank=True)
    source_paragraph_number = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

Notes:

- `raw_reference` stores the full reference chunk as exported by the parser.
- `raw_document` stores the normalized document part before the locator marker.
- `source_file` and `source_paragraph_number` are optional but useful during import/debugging.
- The current `page_start`, `page_end`, `page_start_relation`, `page_end_relation` should be retired after migration.

Recommended indexes:

- `(manifestation)`
- `(manifestation, raw_document)` if document-matching workflows need it

### 2. ReferenceLocator

Represents one locator inside one `Reference` block.

Examples:

- `S. 64(B)`
- `nach S. 64(B)`
- `Sp. 1/2`
- `Abb. 135`
- `passim`

Proposed fields:

```python
class ReferenceLocator(models.Model):
    UNIT_PAGE = ''
    UNIT_COLUMN = 'column'
    UNIT_FIGURE = 'figure'
    UNIT_CHOICES = [
        (UNIT_PAGE, 'page'),
        (UNIT_COLUMN, 'column'),
        (UNIT_FIGURE, 'figure'),
    ]

    RELATION_ON = ''
    RELATION_BEFORE = 'before'
    RELATION_AFTER = 'after'
    RELATION_CHOICES = [
        (RELATION_ON, 'on'),
        (RELATION_BEFORE, 'before'),
        (RELATION_AFTER, 'after'),
    ]

    SCOPE_NORMAL = ''
    SCOPE_PASSIM = 'passim'
    SCOPE_CHOICES = [
        (SCOPE_NORMAL, 'normal'),
        (SCOPE_PASSIM, 'passim'),
    ]

    reference = models.ForeignKey(
        Reference,
        on_delete=models.CASCADE,
        related_name='locators',
    )
    order = models.PositiveIntegerField(default=0, db_index=True)
    locator_unit = models.CharField(max_length=10, choices=UNIT_CHOICES, blank=True, default='')
    locator_start = models.PositiveIntegerField(null=True, blank=True)
    locator_end = models.PositiveIntegerField(null=True, blank=True)
    start_relation = models.CharField(max_length=6, choices=RELATION_CHOICES, blank=True, default='')
    end_relation = models.CharField(max_length=6, choices=RELATION_CHOICES, blank=True, default='')
    locator_scope = models.CharField(max_length=12, choices=SCOPE_CHOICES, blank=True, default='')
    raw_locator = models.CharField(max_length=255)
    reference_type_codes = models.CharField(max_length=16, blank=True, default='')
```

Compact storage rules:

- `locator_unit=''` means normal page locator
- `start_relation=''` and `end_relation=''` mean implicit `on`
- `locator_scope=''` means numeric locator, not `passim`
- `reference_type_codes=''` means implicit `T`

Recommended normalization for `reference_type_codes`:

- store sorted explicit codes without separators
- examples:
  - `''` => implicit `T`
  - `'B'` => only `B`
  - `'A'` => only `A`
  - `'TZ'` => `T+Z`
  - `'BF'` => `B+F`

This is more storage-efficient than a join table or PostgreSQL array while remaining easy to validate.

Validation rules:

- if `locator_scope='passim'`, both `locator_start` and `locator_end` must be null
- if `locator_start` and `locator_end` are both present, `locator_end >= locator_start`
- if one of `start_relation` / `end_relation` is set, the corresponding locator boundary must be numeric
- `reference_type_codes` must only contain `T`, `B`, `F`, `A`, `Z` with no duplicates

Recommended indexes:

- `(reference, order)`
- `(locator_unit, locator_start)`
- `(locator_scope)` if `passim` queries matter

### 3. IndexEntryCrossReference

Represents lemma-to-lemma cross-references, separate from document references.

Examples:

- `s. [Andromeda; Perseus und]`
- `siehe Albertus Magnus`
- `siehe auch Alliacus`
- `vgl. Aphros`

Proposed fields:

```python
class IndexEntryCrossReference(models.Model):
    KIND_SEE = 'see'
    KIND_SEE_ALSO = 'see_also'
    KIND_COMPARE = 'compare'
    KIND_CHOICES = [
        (KIND_SEE, 'See'),
        (KIND_SEE_ALSO, 'See also'),
        (KIND_COMPARE, 'Compare'),
    ]

    source_entry = models.ForeignKey(
        IndexEntry,
        on_delete=models.CASCADE,
        related_name='cross_references',
    )
    target_entry = models.ForeignKey(
        IndexEntry,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='incoming_cross_references',
    )
    kind = models.CharField(max_length=12, choices=KIND_CHOICES)
    marker = models.CharField(max_length=20)
    target_raw = models.CharField(max_length=1000)
    order = models.PositiveIntegerField(default=0, db_index=True)
```

Notes:

- `target_entry` should remain nullable until import resolution is reliable.
- `target_raw` preserves the source target for later reconciliation.
- `marker` preserves whether the source used `s.`, `siehe`, `siehe auch`, or `vgl.`.

Recommended indexes:

- `(source_entry, order)`
- `(target_entry)`
- `(kind)`

### 4. Optional: ManifestationAlias

The parser normalizes a document string, but matching it to a `Manifestation` may require aliases.

```python
class ManifestationAlias(models.Model):
    manifestation = models.ForeignKey(
        Manifestation,
        on_delete=models.CASCADE,
        related_name='aliases',
    )
    label = models.CharField(max_length=1000, db_index=True)
    normalized_label = models.CharField(max_length=1000, db_index=True)
```

This is optional but likely useful for import quality.

## How Current Parser Output Maps to the Target Schema

### Example 1

```text
Ewing, W. A.: "Blumenfeld. A Fetish for Beauty", Abb. 125
```

- `Reference.raw_document = 'Ewing, W. A.: "Blumenfeld. A Fetish for Beauty"'`
- one `ReferenceLocator`
  - `locator_unit='figure'`
  - `locator_start=125`
  - `locator_end=125`
  - `reference_type_codes=''` only if you treat bare figure refs as implicit `T`

### Example 2

```text
Habermas, J.: "...", Sp. 1/2
```

- `Reference.raw_document = 'Habermas, J.: "..."'`
- one `ReferenceLocator`
  - `locator_unit='column'`
  - `locator_start=1`
  - `locator_end=2`

### Example 3

```text
Meerwald, A.: "Das Schloß B.-Krumau", nach S. 64(B)
```

- `Reference.raw_document = 'Meerwald, A.: "Das Schloß B.-Krumau"'`
- one `ReferenceLocator`
  - `locator_unit=''`
  - `locator_start=64`
  - `locator_end=64`
  - `start_relation='after'`
  - `end_relation='after'`
  - `reference_type_codes='B'`

### Example 4

```text
Plautus: "Amphitruo", passim
```

- `Reference.raw_document = 'Plautus: "Amphitruo"'`
- one `ReferenceLocator`
  - `locator_scope='passim'`
  - `locator_start=null`
  - `locator_end=null`

### Example 5

```text
Andromeda; Befreiung durch Perseus:	s. [Andromeda; Perseus und]
```

- `IndexEntryCrossReference`
  - `source_entry = current lemma`
  - `target_entry = resolved later if possible`
  - `kind='see'`
  - `marker='s.'`
  - `target_raw='Andromeda; Perseus und'`

## Migration Strategy

### Phase 1: additive migration

- add `raw_reference`, `raw_document`, `source_file`, `source_paragraph_number` to `Reference`
- add new `ReferenceLocator`
- add new `IndexEntryCrossReference`
- keep current `Reference.page_start` / `page_end` fields temporarily

### Phase 2: backfill

- create one `ReferenceLocator` for every existing `Reference`
- map current `page_start` / `page_end` / relation fields into locator rows
- set `locator_unit=''`, `locator_scope=''`, `reference_type_codes=''`

### Phase 3: importer switch

- update import logic to write child locators instead of flattening into `Reference`
- update admin and display helpers to show locators from `Reference.locators`

### Phase 4: cleanup

- remove legacy `page_start`, `page_end`, `page_start_relation`, `page_end_relation` from `Reference`
- update any ordering that still depends on those fields

## Recommended Admin/UI behavior

- `ReferenceAdmin` should display a compact rendered locator summary derived from child locators
- `IndexEntryAdmin` should surface both document references and cross-references
- cross-references should be editable independently from manifestation-based references

## Summary

The central design decision is:

- `Reference` = one bibliographic reference block to a manifestation
- `ReferenceLocator` = one concrete locator inside that block
- `IndexEntryCrossReference` = one lemma-to-lemma cross-reference

This matches the parser's current knowledge without forcing non-page locators, `passim`, or cross-references into a page-range-only schema.