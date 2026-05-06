"""
Data migration der opretter en daglig Django-Q Schedule til auto-arkivering.
"""
from django.db import migrations


def opret_arkiver_schedule(apps, schema_editor):
    Schedule = apps.get_model('django_q', 'Schedule')
    if not Schedule.objects.filter(func='events.tasks.auto_arkiver_events').exists():
        Schedule.objects.create(
            name='Daglig auto-arkivering',
            func='events.tasks.auto_arkiver_events',
            schedule_type='D',   # D = daily
            repeats=-1,          # -1 = uendeligt
            next_run=None,       # køres næste gang qcluster starter
        )


def slet_arkiver_schedule(apps, schema_editor):
    Schedule = apps.get_model('django_q', 'Schedule')
    Schedule.objects.filter(func='events.tasks.auto_arkiver_events').delete()


class Migration(migrations.Migration):
    dependencies = [
        ('events', '0016_aflysning_arkivering'),
        ('django_q', '0019_alter_task_options_alter_ormq_key_alter_ormq_lock_and_more'),
    ]

    operations = [
        migrations.RunPython(opret_arkiver_schedule, slet_arkiver_schedule),
    ]
