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
level-text      = label, [sort-annotation], {metadata} ;
sort-annotation = space, "[", sort-token, "]" ;
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
- `sort_key`: the inferred or explicitly supplied key for an individual lemma level. An empty value means that the extractor could not determine an unambiguous key.
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

## Sort keys

The extractor derives a `sort_key` for every lemma level from the order of entries in a single ODT file. It compares only direct siblings: top-level lemmas are compared within the file, and nested lemmas only with entries under the same visible parent label. Up to five preceding and five following successfully parsed siblings are considered. ODT file boundaries and unparsable paragraphs never supply sorting context.

Candidate comparisons ignore case, accents, Unicode normalization differences, punctuation, and repeated whitespace. The extractor considers the visible label itself and, where applicable, these alternatives:

- removal of one initial German, English, or Italian article
- `St.` expanded to `Saint` or `Sankt`
- an initial `Mc` expanded to `Mac`
- an initial decimal number from `0` through `9999` written as a German, English, or Italian number word

For person indexes, a comma-free name can be split into surname and given-name levels when its first word matches the preceding person's family-name sort key. This rule is intentionally limited to names without any comma. Names such as `García Márquez, Gabriel` and `Vaughan Williams, Ralph` therefore remain unchanged, while `A Fei` can become the levels `A` and `Fei` after `A., Dominique`.

The candidate lists do not encode language detection. If the visible label is the only candidate, it is used directly. Where alternatives exist, a key is emitted only if precisely one candidate fits the local sibling order. If none or several alternatives fit, the lemma remains in JSON with an empty `sort_key` and the extractor reports a sort-key inference error.

Use an explicit annotation when the source must decide the form unambiguously. The annotation immediately follows the source token and is omitted from the visible label:

```text
1000 [Tausend] Tränen
```

This produces `label: "1000 Tränen"` and `sort_key: "Tausend Tränen"`; `raw_lemma` preserves the annotation. The annotation is valid on every lemma level. It is distinct from the brackets used for a cross-reference target such as `siehe [Lemma; Unterlemma]`.

## Error export

The extractor can also write every unparsable paragraph into a separate text file:

```bash
python manage.py extract_odt_index /path/to/odt/folder --output parsed-index.json --error-output odt-parse-errors.txt
```

Each error block contains:

- source file name and paragraph number
- parser or sort-key inference message
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
- Nodes are deduplicated by `(index_type, complete fixture path, per-level metadata)`. The parser's `P` and `S` values are stored in `IndexEntry.index_type`, so identically labelled person and subject paths remain separate.
- Each node receives a German `IndexEntryLabel` from the parsed `label` and its `sort_key`. For a person node built from the first two levels, the fixture joins both resolved keys with `, `; the person key is empty when either component is unresolved. The parser's level `metadata` has no dedicated database field, but it is still used to disambiguate node identity and cross-reference target resolution.
- Only `page` items create `Reference` and `ReferenceLocator` rows. The deepest level receives each of these through an ordered `IndexEntryReference` row.
- `see`, `see_also`, and `compare` items create `IndexEntryCrossReference` rows. Target resolution requires an exact full target path in the same index type; otherwise `target_entry` is empty and `target_raw` remains available for manual review.

The Django `Reference` model can represent `vor` and `nach` without storing `on` explicitly:

- empty `page_start_relation` / `page_end_relation` in the database means implicit `on`
- `before` means the reference points to an unpaginated position before the numbered page
- `after` means the reference points to an unpaginated position after the numbered page

The ODT data still contains locators that fall outside the current numeric model entirely, such as `12.9`, and whole-work locators such as `passim`. The extractor therefore continues to preserve raw locator text alongside the parsed numeric representation.