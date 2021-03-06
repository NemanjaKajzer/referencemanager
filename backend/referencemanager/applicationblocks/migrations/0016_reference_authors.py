# Generated by Django 3.0.8 on 2020-09-01 16:53

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('applicationblocks', '0015_remove_reference_authors'),
    ]

    operations = [
        migrations.AddField(
            model_name='reference',
            name='authors',
            field=models.ManyToManyField(related_name='user_id', related_query_name='user_id', to=settings.AUTH_USER_MODEL),
        ),
    ]
