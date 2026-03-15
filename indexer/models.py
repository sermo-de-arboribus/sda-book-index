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

    manifestation = models.ForeignKey(
        Manifestation, on_delete=models.CASCADE, related_name='references', db_index=True
    )
    page_start = models.PositiveIntegerField()
    page_end = models.PositiveIntegerField()

    class Meta:
        ordering = ['manifestation', 'page_start', 'page_end']
        indexes = [
            models.Index(fields=['manifestation', 'page_start'], name='indexer_ref_mf_start_idx'),
        ]

    def clean(self):
        if self.page_start is not None and self.page_end is not None:
            if self.page_end < self.page_start:
                raise ValidationError(
                    {'page_end': 'page_end must be greater than or equal to page_start.'}
                )

    def __str__(self):
        if self.page_start == self.page_end:
            return f'{self.manifestation} p. {self.page_start}'
        return f'{self.manifestation} pp. {self.page_start}–{self.page_end}'


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
