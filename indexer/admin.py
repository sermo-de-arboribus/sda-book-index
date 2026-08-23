from django.contrib import admin

from .models import (
    Agent,
    AgentName,
    ContributorRole,
    IndexEntry,
    IndexEntryCrossReference,
    IndexEntryLabel,
    IndexEntryReference,
    Manifestation,
    ManifestationContribution,
    ManifestationTitle,
    PersonIdentifier,
    Reference,
    ReferenceLocator,
    Subject,
    SubjectLabel,
    Work,
    WorkContribution,
    WorkTitle,
)


class WorkTitleInline(admin.TabularInline):
    model = WorkTitle
    extra = 1


class WorkContributionInline(admin.TabularInline):
    model = WorkContribution
    extra = 1
    autocomplete_fields = ['agent']


class AgentNameInline(admin.TabularInline):
    model = AgentName
    extra = 1


class PersonIdentifierInline(admin.TabularInline):
    model = PersonIdentifier
    extra = 1


class ManifestationTitleInline(admin.TabularInline):
    model = ManifestationTitle
    extra = 1


class ManifestationContributionInline(admin.TabularInline):
    model = ManifestationContribution
    extra = 1
    autocomplete_fields = ['agent']


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


class ReferenceLocatorInline(admin.TabularInline):
    model = ReferenceLocator
    extra = 0
    ordering = ['order']


class IndexEntryCrossReferenceInline(admin.TabularInline):
    model = IndexEntryCrossReference
    fk_name = 'source_entry'
    extra = 0
    autocomplete_fields = ['target_entry']
    ordering = ['order']


@admin.register(Work)
class WorkAdmin(admin.ModelAdmin):
    inlines = [WorkTitleInline, WorkContributionInline]
    list_display = ['slug', 'work_type', 'title_preview', 'created_at']
    list_filter = ['work_type']
    search_fields = ['slug', 'canonical_title', 'titles__label']
    autocomplete_fields = ['parent']
    prepopulated_fields = {'slug': ('canonical_title',)}

    @admin.display(description='Title (en)')
    def title_preview(self, obj):
        title = obj.titles.filter(language='en').first() or obj.titles.first()
        return title.label if title else obj.canonical_title or '—'


@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    inlines = [AgentNameInline, PersonIdentifierInline]
    list_display = ['slug', 'agent_type', 'name_preview', 'created_at']
    list_filter = ['agent_type']
    search_fields = ['slug', 'canonical_name', 'names__label', 'person_identifiers__value']

    @admin.display(description='Name (en)')
    def name_preview(self, obj):
        name = obj.names.filter(language='en').first() or obj.names.first()
        return name.label if name else obj.canonical_name or '—'


@admin.register(Manifestation)
class ManifestationAdmin(admin.ModelAdmin):
    inlines = [ManifestationTitleInline, ManifestationContributionInline]
    list_display = ['slug', 'work', 'title_preview', 'year', 'publisher', 'created_at']
    list_filter = ['year']
    search_fields = ['slug', 'canonical_title', 'titles__label', 'work__slug', 'work__canonical_title']
    autocomplete_fields = ['work']
    prepopulated_fields = {'slug': ('canonical_title',)}

    @admin.display(description='Title (en)')
    def title_preview(self, obj):
        title = obj.titles.filter(language='en').first() or obj.titles.first()
        return title.label if title else obj.canonical_title or '—'


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
    inlines = [ReferenceLocatorInline]
    list_display = ['__str__', 'manifestation', 'raw_document_preview', 'page_start', 'page_end']
    list_filter = ['manifestation__work']
    search_fields = [
        'manifestation__slug',
        'manifestation__canonical_title',
        'manifestation__titles__label',
        'manifestation__work__slug',
        'manifestation__work__canonical_title',
        'manifestation__work__titles__label',
        'raw_document',
        'raw_reference',
    ]
    autocomplete_fields = ['manifestation']

    @admin.display(description='Document')
    def raw_document_preview(self, obj):
        return obj.raw_document or '—'


@admin.register(IndexEntry)
class IndexEntryAdmin(admin.ModelAdmin):
    inlines = [IndexEntryLabelInline, IndexEntryReferenceInline, IndexEntryCrossReferenceInline]
    list_display = ['__str__', 'index_type', 'parent', 'label_preview', 'created_at']
    list_filter = ['index_type', 'parent']
    search_fields = ['labels__label']
    autocomplete_fields = ['parent']

    @admin.display(description='Label (en)')
    def label_preview(self, obj):
        label = obj.labels.filter(language='en').first() or obj.labels.first()
        return label.label if label else '—'
