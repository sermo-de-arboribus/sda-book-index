from django.core.exceptions import ValidationError
from django.db import models


class ContributorRole(models.TextChoices):
    AUTHOR = 'author', 'Author'
    EDITOR = 'editor', 'Editor'
    ADVISOR = 'advisor', 'Advisor'
    COMPOSER = 'composer', 'Composer'
    COPY_EDITOR = 'copy-editor', 'Copy-editor'
    ILLUSTRATOR = 'illustrator', 'Illustrator'
    TRANSLATOR = 'translator', 'Translator'


class Work(models.Model):
    """A conceptual work (book, chapter, article, etc.)."""

    BOOK = 'book'
    CHAPTER = 'chapter'
    ARTICLE = 'article'
    OTHER = 'other'
    WORK_TYPE_CHOICES = [
        (BOOK, 'Book'),
        (CHAPTER, 'Chapter'),
        (ARTICLE, 'Article'),
        (OTHER, 'Other'),
    ]

    work_type = models.CharField(
        max_length=20, choices=WORK_TYPE_CHOICES, default=BOOK, db_index=True
    )
    parent = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='parts',
        db_index=True,
    )
    canonical_title = models.CharField(max_length=500, blank=True)
    slug = models.SlugField(max_length=200, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['slug']

    def __str__(self):
        title = self.titles.filter(language='en').first()
        if title is None:
            title = self.titles.first()
        return title.label if title else self.canonical_title or self.slug


class WorkTitle(models.Model):
    """A multilingual title for a work (BCP-47 language tag)."""

    id = models.CharField(max_length=255, primary_key=True)
    work = models.ForeignKey(Work, on_delete=models.CASCADE, related_name='titles')
    language = models.CharField(max_length=35, db_index=True)
    label = models.CharField(max_length=500)
    sort_key = models.CharField(max_length=500, blank=True)

    class Meta:
        unique_together = [('work', 'language', 'label')]
        ordering = ['language']
        indexes = [
            models.Index(fields=['work', 'language'], name='indexer_wt_work_lang_idx'),
            models.Index(fields=['language', 'label'], name='indexer_wt_lang_label_idx'),
        ]

    def __str__(self):
        return f'{self.label} ({self.language})'


class Agent(models.Model):
    """A person or corporation that can contribute to a work."""

    PERSON = 'person'
    CORPORATION = 'corporation'
    AGENT_TYPE_CHOICES = [
        (PERSON, 'Person'),
        (CORPORATION, 'Corporation'),
    ]

    agent_type = models.CharField(
        max_length=20, choices=AGENT_TYPE_CHOICES, default=PERSON, db_index=True
    )
    canonical_name = models.CharField(max_length=500, blank=True)
    slug = models.SlugField(max_length=200, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['slug']

    def __str__(self):
        name = self.names.filter(language='en').first()
        if name is None:
            name = self.names.first()
        return name.label if name else self.canonical_name or self.slug


class AgentName(models.Model):
    """A multilingual name for an agent (BCP-47 language tag)."""

    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name='names')
    language = models.CharField(max_length=35, db_index=True)
    label = models.CharField(max_length=500)
    sort_key = models.CharField(max_length=500, blank=True)

    class Meta:
        unique_together = [('agent', 'language', 'label')]
        ordering = ['language']
        indexes = [
            models.Index(fields=['agent', 'language'], name='indexer_an_agent_lang_idx'),
            models.Index(fields=['language', 'label'], name='indexer_an_lang_label_idx'),
        ]

    def __str__(self):
        return f'{self.label} ({self.language})'


class PersonIdentifier(models.Model):
    """An external identifier for a person agent."""

    GND = 'gnd'
    ISNI = 'isni'
    ORCID = 'orcid'
    IDENTIFIER_TYPE_CHOICES = [
        (GND, 'GND'),
        (ISNI, 'ISNI'),
        (ORCID, 'ORCID'),
    ]

    agent = models.ForeignKey(
        Agent,
        on_delete=models.CASCADE,
        related_name='person_identifiers',
    )
    identifier_type = models.CharField(max_length=20, choices=IDENTIFIER_TYPE_CHOICES, db_index=True)
    value = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['identifier_type', 'value']
        unique_together = [('agent', 'identifier_type'), ('identifier_type', 'value')]
        indexes = [
            models.Index(
                fields=['agent', 'identifier_type'],
                name='indexer_pi_agent_type_idx',
            ),
            models.Index(
                fields=['identifier_type', 'value'],
                name='indexer_pi_type_value_idx',
            ),
        ]

    def clean(self):
        if self.agent_id and self.agent.agent_type != Agent.PERSON:
            raise ValidationError({'agent': 'Person identifiers can only be attached to person agents.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.get_identifier_type_display()}: {self.value}'


class WorkContribution(models.Model):
    """A contributor's role in creating a work."""

    id = models.CharField(max_length=255, primary_key=True)
    work = models.ForeignKey(Work, on_delete=models.CASCADE, related_name='contributions')
    agent = models.ForeignKey(Agent, on_delete=models.PROTECT, related_name='work_contributions')
    role = models.CharField(max_length=20, choices=ContributorRole.choices)
    sort_order = models.PositiveIntegerField(default=0, db_index=True)

    class Meta:
        unique_together = [('work', 'agent', 'role')]
        ordering = ['sort_order', 'agent__slug']

    def __str__(self):
        return f'{self.agent} ({self.role}) → {self.work}'


class Manifestation(models.Model):
    """A physical or digital manifestation of a work."""

    work = models.ForeignKey(Work, on_delete=models.PROTECT, related_name='manifestations')
    canonical_title = models.CharField(max_length=500, blank=True)
    slug = models.SlugField(max_length=200, unique=True, db_index=True)
    year = models.PositiveSmallIntegerField(null=True, blank=True, db_index=True)
    publisher = models.CharField(max_length=500, blank=True)
    isbn_issn = models.CharField(max_length=30, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['slug']

    def __str__(self):
        title = self.titles.filter(language='en').first()
        if title is None:
            title = self.titles.first()
        return title.label if title else self.canonical_title or self.slug

    def effective_contributions(self):
        """Return the effective union of work-level and manifestation-level contributions.

        Work-level contributions take precedence: if the same (agent, role) pair exists
        at both levels, the manifestation-level entry is ignored (not a duplicate override).
        """
        from django.db.models import Q

        work_contribs = list(
            self.work.contributions.select_related('agent').order_by('sort_order', 'agent__slug')
        )
        # Build exclusion filter for (agent, role) pairs already present at work level
        work_keys = [(c.agent_id, c.role) for c in work_contribs]
        exclude_filter = Q()
        for agent_id, role in work_keys:
            exclude_filter |= Q(agent_id=agent_id, role=role)
        mf_qs = self.contributions.select_related('agent').order_by('sort_order', 'agent__slug')
        if exclude_filter:
            mf_qs = mf_qs.exclude(exclude_filter)
        return work_contribs + list(mf_qs)


class ManifestationSuggestion(models.Model):
    """A scored candidate mapping from a parsed reference to a manifestation."""

    STATUS_SUGGESTED = 'suggested'
    STATUS_CONFIRMED = 'confirmed'
    STATUS_REJECTED = 'rejected'
    STATUS_CHOICES = [
        (STATUS_SUGGESTED, 'Suggested'),
        (STATUS_CONFIRMED, 'Confirmed'),
        (STATUS_REJECTED, 'Rejected'),
    ]

    MATCH_TYPE_TITLE = 'title'
    MATCH_TYPE_ISBN = 'isbn'
    MATCH_TYPE_YEAR = 'year'
    MATCH_TYPE_MANUAL = 'manual'
    MATCH_TYPE_CHOICES = [
        (MATCH_TYPE_TITLE, 'Title'),
        (MATCH_TYPE_ISBN, 'ISBN'),
        (MATCH_TYPE_YEAR, 'Year'),
        (MATCH_TYPE_MANUAL, 'Manual'),
    ]

    reference = models.ForeignKey(
        'Reference',
        on_delete=models.CASCADE,
        related_name='manifestation_suggestions',
        db_index=True,
    )
    manifestation = models.ForeignKey(
        Manifestation,
        on_delete=models.CASCADE,
        related_name='suggestions',
        db_index=True,
    )
    score = models.PositiveSmallIntegerField(default=0)
    match_type = models.CharField(max_length=20, choices=MATCH_TYPE_CHOICES, default=MATCH_TYPE_TITLE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_SUGGESTED)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-score', 'manifestation__slug']
        unique_together = [('reference', 'manifestation')]
        indexes = [
            models.Index(fields=['reference', 'status'], name='indexer_ms_ref_status_idx'),
            models.Index(fields=['manifestation', 'score'], name='indexer_ms_mf_score_idx'),
        ]

    def __str__(self):
        return f'{self.reference} → {self.manifestation} ({self.score}%)'


class ManifestationTitle(models.Model):
    """A multilingual title for a manifestation (BCP-47 language tag)."""

    manifestation = models.ForeignKey(Manifestation, on_delete=models.CASCADE, related_name='titles')
    language = models.CharField(max_length=35, db_index=True)
    label = models.CharField(max_length=500)
    sort_key = models.CharField(max_length=500, blank=True)

    class Meta:
        unique_together = [('manifestation', 'language', 'label')]
        ordering = ['language']
        indexes = [
            models.Index(fields=['manifestation', 'language'], name='indexer_mt_mf_lang_idx'),
            models.Index(fields=['language', 'label'], name='indexer_mt_lang_label_idx'),
        ]

    def __str__(self):
        return f'{self.label} ({self.language})'


class ManifestationContribution(models.Model):
    """A contributor's role specific to a manifestation (adds to work-level contributions)."""

    manifestation = models.ForeignKey(Manifestation, on_delete=models.CASCADE, related_name='contributions')
    agent = models.ForeignKey(Agent, on_delete=models.PROTECT, related_name='manifestation_contributions')
    role = models.CharField(max_length=20, choices=ContributorRole.choices)
    sort_order = models.PositiveIntegerField(default=0, db_index=True)

    class Meta:
        unique_together = [('manifestation', 'agent', 'role')]
        ordering = ['sort_order', 'agent__slug']

    def __str__(self):
        return f'{self.agent} ({self.role}) → {self.manifestation}'


class Subject(models.Model):
    """A hierarchical subject used in the index."""

    slug = models.SlugField(max_length=200, unique=True, db_index=True)
    parent = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='children',
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['slug']

    def __str__(self):
        label = self.labels.filter(language='en').first()
        if label is None:
            label = self.labels.first()
        return label.label if label else self.slug


class SubjectLabel(models.Model):
    """A multilingual label for a subject (BCP-47 language tag)."""

    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='labels')
    language = models.CharField(max_length=35, db_index=True)
    label = models.CharField(max_length=500)

    class Meta:
        unique_together = [('subject', 'language', 'label')]
        ordering = ['language']

    def __str__(self):
        return f'{self.label} ({self.language})'


class Reference(models.Model):
    """A reference to a page range within a manifestation."""

    RELATION_ON = 'on'
    RELATION_BEFORE = 'before'
    RELATION_AFTER = 'after'
    RELATION_CHOICES = [
        ('', RELATION_ON),
        (RELATION_BEFORE, RELATION_BEFORE),
        (RELATION_AFTER, RELATION_AFTER),
    ]

    manifestation = models.ForeignKey(
        Manifestation, on_delete=models.CASCADE, related_name='references', db_index=True
    )
    raw_reference = models.TextField(blank=True)
    raw_document = models.CharField(max_length=1000, blank=True)
    raw_document_part_of = models.CharField(max_length=1000, blank=True)
    source_file = models.CharField(max_length=255, blank=True)
    source_paragraph_number = models.PositiveIntegerField(null=True, blank=True)
    page_start = models.PositiveIntegerField()
    page_start_relation = models.CharField(max_length=6, choices=RELATION_CHOICES, blank=True, default='')
    page_end = models.PositiveIntegerField()
    page_end_relation = models.CharField(max_length=6, choices=RELATION_CHOICES, blank=True, default='')

    class Meta:
        ordering = ['manifestation', 'page_start', 'page_end']
        indexes = [
            models.Index(fields=['manifestation', 'page_start'], name='indexer_ref_mf_start_idx'),
            models.Index(fields=['manifestation', 'raw_document'], name='indexer_ref_mf_doc_idx'),
        ]

    def clean(self):
        if self.page_start is not None and self.page_end is not None:
            if self.page_end < self.page_start:
                raise ValidationError(
                    {'page_end': 'page_end must be greater than or equal to page_start.'}
                )

    @property
    def effective_page_start_relation(self):
        return self.page_start_relation or self.RELATION_ON

    @property
    def effective_page_end_relation(self):
        return self.page_end_relation or self.RELATION_ON

    def __str__(self):
        if self.page_start == self.page_end and self.page_start_relation == self.page_end_relation:
            relation_prefix = self._relation_prefix(self.page_start_relation)
            if relation_prefix:
                return f'{self.manifestation} {relation_prefix} p. {self.page_start}'
            return f'{self.manifestation} p. {self.page_start}'
        start = self._format_page_boundary(self.page_start, self.page_start_relation)
        end = self._format_page_boundary(self.page_end, self.page_end_relation)
        return f'{self.manifestation} pp. {start}–{end}'

    def _format_page_boundary(self, page, relation):
        relation_prefix = self._relation_prefix(relation)
        if relation_prefix:
            return f'{relation_prefix} {page}'
        return str(page)

    def _relation_prefix(self, relation):
        if relation == self.RELATION_BEFORE:
            return 'before'
        if relation == self.RELATION_AFTER:
            return 'after'
        return ''


class ReferenceLocator(models.Model):
    """A single locator inside a bibliographic reference block."""

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

    ALLOWED_REFERENCE_TYPE_CODES = {'T', 'B', 'F', 'A', 'Z'}

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

    class Meta:
        ordering = ['order', 'locator_start', 'locator_end']
        indexes = [
            models.Index(fields=['reference', 'order'], name='indexer_rl_ref_order_idx'),
            models.Index(fields=['locator_unit', 'locator_start'], name='indexer_rl_unit_start_idx'),
            models.Index(fields=['locator_scope'], name='indexer_rl_scope_idx'),
        ]

    @property
    def effective_locator_unit(self):
        return self.locator_unit or 'page'

    @property
    def effective_start_relation(self):
        return self.start_relation or 'on'

    @property
    def effective_end_relation(self):
        return self.end_relation or 'on'

    @property
    def effective_reference_type_codes(self):
        if not self.reference_type_codes:
            return ('T',)
        return tuple(self.reference_type_codes)

    def clean(self):
        if self.locator_scope == self.SCOPE_PASSIM:
            if self.locator_start is not None or self.locator_end is not None:
                raise ValidationError(
                    {'locator_scope': 'passim locators cannot store numeric start/end values.'}
                )
            if self.start_relation or self.end_relation:
                raise ValidationError(
                    {'locator_scope': 'passim locators cannot store before/after relations.'}
                )

        if self.locator_start is not None and self.locator_end is not None:
            if self.locator_end < self.locator_start:
                raise ValidationError(
                    {'locator_end': 'locator_end must be greater than or equal to locator_start.'}
                )

        if self.start_relation and self.locator_start is None:
            raise ValidationError(
                {'start_relation': 'start_relation requires a numeric locator_start.'}
            )
        if self.end_relation and self.locator_end is None:
            raise ValidationError(
                {'end_relation': 'end_relation requires a numeric locator_end.'}
            )

        if self.reference_type_codes:
            if any(code not in self.ALLOWED_REFERENCE_TYPE_CODES for code in self.reference_type_codes):
                raise ValidationError(
                    {'reference_type_codes': 'reference_type_codes may only contain T, B, F, A, Z.'}
                )
            if len(set(self.reference_type_codes)) != len(self.reference_type_codes):
                raise ValidationError(
                    {'reference_type_codes': 'reference_type_codes may not contain duplicates.'}
                )
            normalized = ''.join(sorted(self.reference_type_codes))
            if self.reference_type_codes != normalized:
                raise ValidationError(
                    {'reference_type_codes': 'reference_type_codes must be stored in sorted order.'}
                )

    def __str__(self):
        if self.locator_scope == self.SCOPE_PASSIM:
            return self.raw_locator or 'passim'
        return self.raw_locator


class IndexEntry(models.Model):
    """A hierarchical index heading (up to 3 levels deep)."""

    parent = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='children',
        db_index=True,
    )
    references = models.ManyToManyField(
        Reference,
        through='IndexEntryReference',
        related_name='index_entries',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'index entries'

    def clean(self):
        if self.parent_id is None:
            return

        # Prevent self-parenting
        if self.pk and self.parent_id == self.pk:
            raise ValidationError(
                {'parent': 'An index entry cannot be its own parent.'}
            )

        # Walk the ancestor chain to enforce max depth of 3 and detect cycles
        depth = 1  # depth of this entry
        seen = {self.pk} if self.pk else set()
        node = self.parent
        while node is not None:
            depth += 1
            if depth > 3:
                raise ValidationError(
                    {'parent': 'Index entries cannot be more than 3 levels deep.'}
                )
            if node.pk in seen:
                raise ValidationError(
                    {'parent': 'Circular parent relationship detected.'}
                )
            seen.add(node.pk)
            node = node.parent

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        label = self.labels.filter(language='en').first()
        if label is None:
            label = self.labels.first()
        return label.label if label else f'IndexEntry #{self.pk}'


class IndexEntryCrossReference(models.Model):
    """A cross-reference from one index entry to another index entry."""

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

    class Meta:
        ordering = ['order', 'kind', 'target_raw']
        indexes = [
            models.Index(fields=['source_entry', 'order'], name='indexer_ixcr_src_order_idx'),
            models.Index(fields=['target_entry'], name='indexer_ixcr_target_idx'),
            models.Index(fields=['kind'], name='indexer_ixcr_kind_idx'),
        ]

    def __str__(self):
        target = self.target_entry or self.target_raw
        return f'{self.source_entry} {self.kind} {target}'


class IndexEntryLabel(models.Model):
    """A multilingual label for an index entry (BCP-47 language tag)."""

    index_entry = models.ForeignKey(
        IndexEntry,
        on_delete=models.CASCADE,
        related_name='labels',
    )
    language = models.CharField(max_length=35, db_index=True)
    label = models.CharField(max_length=500)
    sort_key = models.CharField(max_length=500, blank=True)

    class Meta:
        unique_together = [('index_entry', 'language', 'label')]
        ordering = ['language']
        indexes = [
            models.Index(fields=['index_entry', 'language']),
            models.Index(fields=['language', 'label']),
        ]

    def __str__(self):
        return f'{self.label} ({self.language})'


class IndexEntryReference(models.Model):
    """Through model linking an IndexEntry to a Reference, with ordering."""

    index_entry = models.ForeignKey(
        IndexEntry,
        on_delete=models.CASCADE,
        related_name='entry_references',
    )
    reference = models.ForeignKey(
        Reference,
        on_delete=models.CASCADE,
        related_name='entry_references',
    )
    order = models.PositiveIntegerField(default=0, db_index=True)

    class Meta:
        ordering = ['order', 'reference__manifestation__slug', 'reference__page_start']
        unique_together = [('index_entry', 'reference')]

    def __str__(self):
        return f'{self.index_entry} → {self.reference} (#{self.order})'
