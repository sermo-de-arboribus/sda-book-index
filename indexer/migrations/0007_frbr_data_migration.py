from django.db import migrations


def forward(apps, schema_editor):
    """Migrate Person→Agent, PersonName→AgentName, Work→Manifestation,
    WorkTitle→ManifestationTitle, and update Reference.manifestation."""
    Person = apps.get_model('indexer', 'Person')
    PersonName = apps.get_model('indexer', 'PersonName')
    Agent = apps.get_model('indexer', 'Agent')
    AgentName = apps.get_model('indexer', 'AgentName')
    Work = apps.get_model('indexer', 'Work')
    WorkTitle = apps.get_model('indexer', 'WorkTitle')
    Manifestation = apps.get_model('indexer', 'Manifestation')
    ManifestationTitle = apps.get_model('indexer', 'ManifestationTitle')
    Reference = apps.get_model('indexer', 'Reference')

    # 1. Migrate Person → Agent (type=person)
    person_to_agent = {}
    for person in Person.objects.all():
        agent = Agent.objects.create(
            slug=person.slug,
            agent_type='person',
            canonical_name=person.slug,
        )
        person_to_agent[person.pk] = agent

    # 2. Migrate PersonName → AgentName
    for pname in PersonName.objects.select_related('person').all():
        agent = person_to_agent.get(pname.person_id)
        if agent is not None:
            AgentName.objects.create(
                agent=agent,
                language=pname.language,
                label=pname.label,
                sort_key='',
            )

    # 3. Migrate Work → Manifestation (one-to-one initially)
    work_to_manifestation = {}
    for work in Work.objects.all():
        mf = Manifestation.objects.create(
            work=work,
            slug=work.slug,
            canonical_title=work.canonical_title,
            year=work.year,
            publisher=work.publisher,
            isbn_issn=work.isbn_issn,
        )
        work_to_manifestation[work.pk] = mf

    # 4. Migrate WorkTitle → ManifestationTitle
    for wt in WorkTitle.objects.select_related('work').all():
        mf = work_to_manifestation.get(wt.work_id)
        if mf is not None:
            ManifestationTitle.objects.create(
                manifestation=mf,
                language=wt.language,
                label=wt.label,
                sort_key=wt.sort_key,
            )

    # 5. Update Reference.manifestation from Reference.work
    for ref in Reference.objects.select_related('work').all():
        mf = work_to_manifestation.get(ref.work_id)
        if mf is not None:
            ref.manifestation = mf
            ref.save()


def backward(apps, schema_editor):
    """Reverse: clear data populated by the forward migration."""
    Agent = apps.get_model('indexer', 'Agent')
    Manifestation = apps.get_model('indexer', 'Manifestation')
    Reference = apps.get_model('indexer', 'Reference')

    Reference.objects.filter(manifestation__isnull=False).update(manifestation=None)
    Manifestation.objects.all().delete()
    Agent.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ('indexer', '0006_frbr_schema'),
    ]

    operations = [
        migrations.RunPython(forward, reverse_code=backward),
    ]
