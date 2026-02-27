from django.contrib import admin

from .models import (
    Agent,
    AgentName,
    ContributorRole,
    IndexEntry,
    IndexEntryLabel,
    IndexEntryReference,
    Manifestation,
    ManifestationContribution,
    ManifestationTitle,
    Reference,
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
    inlines = [AgentNameInline]
    list_display = ['slug', 'agent_type', 'name_preview', 'created_at']
    list_filter = ['agent_type']
    search_fields = ['slug', 'canonical_name', 'names__label']

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
    list_display = ['__str__', 'manifestation', 'page_start', 'page_end']
    list_filter = ['manifestation__work']
    search_fields = [
        'manifestation__slug',
        'manifestation__canonical_title',
        'manifestation__titles__label',
        'manifestation__work__slug',
        'manifestation__work__canonical_title',
        'manifestation__work__titles__label',
    ]
    autocomplete_fields = ['manifestation']


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
