from django.contrib import admin

from .models import (
    Work,
    WorkTitle,
    IndexEntry,
    IndexEntryLabel,
    IndexEntryReference,
    Person,
    PersonName,
    Reference,
    Subject,
    SubjectLabel,
)


class WorkTitleInline(admin.TabularInline):
    model = WorkTitle
    extra = 1


class PersonNameInline(admin.TabularInline):
    model = PersonName
    extra = 1


class SubjectLabelInline(admin.TabularInline):
    model = SubjectLabel
    extra = 1


class IndexEntryLabelInline(admin.TabularInline):
    model = IndexEntryLabel
    extra = 1


class IndexEntryReferenceInline(admin.TabularInline):
    model = IndexEntryReference
    extra = 1
    autocomplete_fields = ['reference']
    ordering = ['order']


@admin.register(Work)
class WorkAdmin(admin.ModelAdmin):
    inlines = [WorkTitleInline]
    list_display = ['slug', 'work_type', 'title_preview', 'year', 'created_at']
    list_filter = ['work_type', 'year']
    search_fields = ['slug', 'canonical_title', 'titles__label']
    autocomplete_fields = ['parent']
    prepopulated_fields = {'slug': ('canonical_title',)}

    @admin.display(description='Title (en)')
    def title_preview(self, obj):
        title = obj.titles.filter(language='en').first() or obj.titles.first()
        return title.label if title else obj.canonical_title or '—'


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
    list_display = ['__str__', 'work', 'page_start', 'page_end']
    list_filter = ['work']
    search_fields = ['work__slug', 'work__canonical_title', 'work__titles__label']
    autocomplete_fields = ['work']


@admin.register(IndexEntry)
class IndexEntryAdmin(admin.ModelAdmin):
    inlines = [IndexEntryLabelInline, IndexEntryReferenceInline]
    list_display = ['__str__', 'parent', 'label_preview', 'created_at']
    list_filter = ['parent']
    search_fields = ['labels__label']
    autocomplete_fields = ['parent']

    @admin.display(description='Label (en)')
    def label_preview(self, obj):
        label = obj.labels.filter(language='en').first() or obj.labels.first()
        return label.label if label else '—'
