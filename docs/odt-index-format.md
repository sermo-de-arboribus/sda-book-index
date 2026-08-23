# ODT Index Extraction Grammar

The ODT source files in the index workflow store one candidate index entry per paragraph. The parser first flattens `content.xml` into plain text with these rules:

- `text:tab` becomes a literal tab character.
- `text:s` becomes one or more spaces.
- nested spans contribute text only; styling is ignored.
- soft page breaks are ignored.

After flattening, the parser uses the final `:\t` sequence in a paragraph as the split between lemma and references. The final split is important because references regularly contain additional colons.

Reference parsing is case-sensitive:

- `S.` introduces page references.
- `Sp.` introduces column references.
- `Abb.` introduces figure references.
- `s.`, `siehe`, and `siehe auch` introduce cross-references to other index lemmas.
- `vgl.` introduces a compare-reference to another lemma.
- For cross-references whose target lemma contains a semicolon, the preferred source format is `siehe [Lemma; Unterlemma]` so the semicolon remains part of the target instead of acting as a reference separator.

## EBNF

```ebnf
entry           = lemma, ":", TAB, reference-list, [";"] ;
lemma           = level-1, [",", level-2, [";", level-3]] ;
level-1         = level-text ;
level-2         = level-text ;
level-3         = level-text ;
level-text      = label, {metadata} ;
metadata        = "(", metadata-text, ")" ;
label           = { character - "(" - ")" } ;

reference-list  = reference, {";", reference} ;
reference       = page-reference | cross-reference ;
page-reference  = document, ",", space, [page-relation, space], locator-marker, space, page-list ;
cross-reference = ("s." | "siehe" | "siehe auch" | "vgl."), space, cross-reference-target ;
cross-reference-target = lemma | "[", lemma, "]" ;
page-relation   = "vor" | "nach" ;
locator-marker  = "S." | "Sp." | "Abb." ;
document        = { character } ;
page-list       = page-locator, {",", space, page-locator} ;
page-locator    = integer
                | integer, "-", integer
                | integer, "/", integer
                | integer, type-note
                | "passim"
                | raw-locator ;
type-note       = "(", reference-type, {"+", reference-type}, ")" ;
reference-type  = "T" | "B" | "F" | "A" | "Z" ;
raw-locator     = { character } ;
```

## Parser output

The management command exports JSON with:

- `levels`: up to three normalized lemma levels.
- `metadata`: parenthetical qualifiers removed from the visible lemma text.
- `kind`: `page` for `S.` references, `see` for `s.` and `siehe`, `see_also` for `siehe auch`, and `compare` for `vgl.`.
- `marker`: the original cross-reference marker, for example `s.`, `siehe`, `siehe auch`, or `vgl.`.
- `target_raw`: for bracketed cross-references such as `siehe [Andromeda; Perseus und]`, the surrounding brackets are removed and the full inner lemma text is preserved.
- `document`: the reference text before the last `, S. ` marker for page references.
- `pages_raw`: the raw locator list after `S.` for page references.
- `page_locators`: normalized numeric spans where possible, with raw fallback preserved.
- `locator_unit`: per locator, omitted for the implicit default `page`, set to `column` for `Sp.` locators and `figure` for `Abb.` locators.
- `reference_types`: per page locator, either the implicit default `T` or the explicit type set parsed from `(T)`, `(B)`, `(F)`, `(A)`, `(Z)`, and `+` combinations such as `(T+B)`.
- `page_start_relation` and `page_end_relation`: only present when the locator is explicitly anchored `vor` or `nach` a numbered page. Missing relation fields mean the implicit default `on`.
- `page_scope`: set to `passim` when the reference applies to the referenced edition as a whole instead of a numeric page span.
- `target_raw` and `target_levels`: normalized lemma target for `s.` cross-references.

For repeated references to the same document, a later semicolon-delimited chunk may omit the document title and consist only of a new locator marker, for example `..., S. 97, 103; Abb. 135`. In that case the parser reuses the document from the preceding page reference.

## Error export

The extractor can also write every unparsable paragraph into a separate text file:

```bash
python manage.py extract_odt_index /path/to/odt/folder --output parsed-index.json --error-output odt-parse-errors.txt
```

Each error block contains:

- source file name and paragraph number
- parser error message
- the normalized paragraph text that should be corrected in the ODT source

## Legacy cross-reference suggestions

To find old `s.` / `siehe` cross-references whose target lemma probably needs square brackets because it contains a semicolon, use:

```bash
python manage.py suggest_bracketed_crossrefs odt-parse-errors.txt --output odt-crossref-bracket-suggestions.txt
```

The report lists:

- the original parse-error block
- the detected cross-reference marker
- the unbracketed target lemma
- a suggested replacement paragraph in the preferred form `s. [Lemma; Unterlemma]`

## Text normalization

During extraction, the parser removes Unicode soft hyphens (`U+00AD`) from normalized text. This affects exported fields such as `raw_paragraph`, page-reference `raw`, and page-reference `document`.

## Reference model mapping

## Fixture import mapping

`export_reference_fixtures` produces one Django JSON fixture containing the complete parsed index:

- Every lemma level becomes an `IndexEntry`, but `P` and `S` are handled differently.
- For `P` entries, the first two parsed levels are combined into one person node (`surname, given name`), and only further levels become children below that person.
- For `S` entries, the parsed levels remain hierarchical and each level becomes its own `IndexEntry` parent/child step.
- Nodes are deduplicated by `(index_type, complete fixture path)`. The parser's `P` and `S` values are stored in `IndexEntry.index_type`, so identically labelled person and subject paths remain separate.
- Each node receives a German `IndexEntryLabel` from the parsed `label`. The parser's level `metadata` has no dedicated database field and is therefore not imported yet.
- Only `page` items create `Reference` and `ReferenceLocator` rows. The deepest level receives each of these through an ordered `IndexEntryReference` row.
- `see`, `see_also`, and `compare` items create `IndexEntryCrossReference` rows. Target resolution requires an exact full target path in the same index type; otherwise `target_entry` is empty and `target_raw` remains available for manual review.

The Django `Reference` model can represent `vor` and `nach` without storing `on` explicitly:

- empty `page_start_relation` / `page_end_relation` in the database means implicit `on`
- `before` means the reference points to an unpaginated position before the numbered page
- `after` means the reference points to an unpaginated position after the numbered page

The ODT data still contains locators that fall outside the current numeric model entirely, such as `12.9`, and whole-work locators such as `passim`. The extractor therefore continues to preserve raw locator text alongside the parsed numeric representation.