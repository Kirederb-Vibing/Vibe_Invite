from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0008_gaestebog_husstand'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='gaesteboghusstand',
            name='tags',
            field=models.CharField(
                blank=True,
                help_text='Kommaseparerede tags, fx "familie, venner"',
                max_length=255,
            ),
        ),
        migrations.AddField(
            model_name='gaesteboghusstand',
            name='shared_with',
            field=models.ManyToManyField(
                blank=True,
                related_name='delte_husstande',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
