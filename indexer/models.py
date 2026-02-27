from django.core.exceptions import ValidationError
from django.db import models


class Work(models.Model):
    """A citable unit of work (book, chapter, article, etc.)."""

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


class Person(models.Model):
    """A person who can appear in the index."""

    slug = models.SlugField(max_length=200, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['slug']
        verbose_name_plural = 'people'

    def __str__(self):
        name = self.names.filter(language='en').first()
        if name is None:
            name = self.names.first()
        return name.label if name else self.slug


class PersonName(models.Model):
    """A multilingual name for a person (BCP-47 language tag)."""

    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name='names')
    language = models.CharField(max_length=35, db_index=True)
    label = models.CharField(max_length=500)

    class Meta:
        unique_together = [('person', 'language', 'label')]
        ordering = ['language']

    def __str__(self):
        return f'{self.label} ({self.language})'


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
    """A reference to a page range within a work."""

    work = models.ForeignKey(Work, on_delete=models.CASCADE, related_name='references', db_index=True)
    page_start = models.PositiveIntegerField()
    page_end = models.PositiveIntegerField()

    class Meta:
        ordering = ['work', 'page_start', 'page_end']
        indexes = [
            models.Index(fields=['work', 'page_start'], name='indexer_ref_work_start_idx'),
        ]

    def clean(self):
        if self.page_start is not None and self.page_end is not None:
            if self.page_end < self.page_start:
                raise ValidationError(
                    {'page_end': 'page_end must be greater than or equal to page_start.'}
                )

    def __str__(self):
        if self.page_start == self.page_end:
            return f'{self.work} p. {self.page_start}'
        return f'{self.work} pp. {self.page_start}–{self.page_end}'


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
        ordering = ['order', 'reference__work__slug', 'reference__page_start']
        unique_together = [('index_entry', 'reference')]

    def __str__(self):
        return f'{self.index_entry} → {self.reference} (#{self.order})'
