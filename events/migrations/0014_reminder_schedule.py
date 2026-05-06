"""
Data migration der opretter en daglig Django-Q Schedule til reminder-opgaven.
"""
from django.db import migrations


def opret_reminder_schedule(apps, schema_editor):
    Schedule = apps.get_model('django_q', 'Schedule')
    if not Schedule.objects.filter(func='events.tasks.send_maaske_reminders').exists():
        Schedule.objects.create(
            name='Daglig måske-reminder',
            func='events.tasks.send_maaske_reminders',
            schedule_type='D',   # D = daily
            repeats=-1,          # -1 = uendeligt
            next_run=None,       # køres næste gang qcluster starter
        )


def slet_reminder_schedule(apps, schema_editor):
    Schedule = apps.get_model('django_q', 'Schedule')
    Schedule.objects.filter(func='events.tasks.send_maaske_reminders').delete()


class Migration(migrations.Migration):
    dependencies = [
        ('events', '0013_reminder_felter'),
        ('django_q', '0019_alter_task_options_alter_ormq_key_alter_ormq_lock_and_more'),
    ]

    operations = [
        migrations.RunPython(opret_reminder_schedule, slet_reminder_schedule),
    ]
