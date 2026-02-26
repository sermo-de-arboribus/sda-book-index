from django.core.exceptions import ValidationError
from django.db import models


class Book(models.Model):
    """A book that can be indexed."""

    slug = models.SlugField(max_length=200, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['slug']

    def __str__(self):
        title = self.titles.filter(language='en').first()
        if title is None:
            title = self.titles.first()
        return title.label if title else self.slug


class BookTitle(models.Model):
    """A multilingual title for a book (BCP-47 language tag)."""

    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='titles')
    language = models.CharField(max_length=35, db_index=True)
    label = models.CharField(max_length=500)

    class Meta:
        unique_together = [('book', 'language', 'label')]
        ordering = ['language']

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
    """A reference to a page range within a book."""

    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='references', db_index=True)
    page_start = models.PositiveIntegerField()
    page_end = models.PositiveIntegerField()

    class Meta:
        ordering = ['book', 'page_start', 'page_end']
        indexes = [
            models.Index(fields=['book', 'page_start']),
        ]

    def clean(self):
        if self.page_start is not None and self.page_end is not None:
            if self.page_end < self.page_start:
                raise ValidationError(
                    {'page_end': 'page_end must be greater than or equal to page_start.'}
                )

    def __str__(self):
        if self.page_start == self.page_end:
            return f'{self.book} p. {self.page_start}'
        return f'{self.book} pp. {self.page_start}–{self.page_end}'


class IndexEntry(models.Model):
    """An index entry associating a person and/or subject with references."""

    person = models.ForeignKey(
        Person,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='index_entries',
        db_index=True,
    )
    subject = models.ForeignKey(
        Subject,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='index_entries',
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
        ordering = ['person__slug', 'subject__slug']
        verbose_name_plural = 'index entries'

    def clean(self):
        if not self.person_id and not self.subject_id:
            raise ValidationError('An index entry must have at least one of person or subject.')

    def __str__(self):
        parts = []
        if self.person_id:
            parts.append(str(self.person))
        if self.subject_id:
            parts.append(str(self.subject))
        return ' / '.join(parts) if parts else f'IndexEntry #{self.pk}'


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
        ordering = ['order', 'reference__book__slug', 'reference__page_start']
        unique_together = [('index_entry', 'reference')]

    def __str__(self):
        return f'{self.index_entry} → {self.reference} (#{self.order})'
