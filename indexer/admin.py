from django.contrib import admin

from .models import (
    Book,
    BookTitle,
    IndexEntry,
    IndexEntryReference,
    Person,
    PersonName,
    Reference,
    Subject,
    SubjectLabel,
)


class BookTitleInline(admin.TabularInline):
    model = BookTitle
    extra = 1


class PersonNameInline(admin.TabularInline):
    model = PersonName
    extra = 1


class SubjectLabelInline(admin.TabularInline):
    model = SubjectLabel
    extra = 1


class IndexEntryReferenceInline(admin.TabularInline):
    model = IndexEntryReference
    extra = 1
    autocomplete_fields = ['reference']
    ordering = ['order']


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    inlines = [BookTitleInline]
    list_display = ['slug', 'title_preview', 'created_at']
    search_fields = ['slug', 'titles__label']
    prepopulated_fields = {'slug': ()}

    @admin.display(description='Title (en)')
    def title_preview(self, obj):
        title = obj.titles.filter(language='en').first() or obj.titles.first()
        return title.label if title else '—'


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    inlines = [PersonNameInline]
    list_display = ['slug', 'name_preview', 'created_at']
    search_fields = ['slug', 'names__label']

    @admin.display(description='Name (en)')
    def name_preview(self, obj):
        name = obj.names.filter(language='en').first() or obj.names.first()
        return name.label if name else '—'


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    inlines = [SubjectLabelInline]
    list_display = ['slug', 'label_preview', 'parent', 'created_at']
    search_fields = ['slug', 'labels__label']
    list_filter = ['parent']
    autocomplete_fields = ['parent']

    @admin.display(description='Label (en)')
    def label_preview(self, obj):
        label = obj.labels.filter(language='en').first() or obj.labels.first()
        return label.label if label else '—'


@admin.register(Reference)
class ReferenceAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'book', 'page_start', 'page_end']
    list_filter = ['book']
    search_fields = ['book__slug', 'book__titles__label']
    autocomplete_fields = ['book']


@admin.register(IndexEntry)
class IndexEntryAdmin(admin.ModelAdmin):
    inlines = [IndexEntryReferenceInline]
    list_display = ['__str__', 'person', 'subject', 'created_at']
    list_filter = ['person', 'subject']
    search_fields = [
        'person__slug',
        'person__names__label',
        'subject__slug',
        'subject__labels__label',
    ]
    autocomplete_fields = ['person', 'subject']
