# Generated by Django 3.0.8 on 2020-08-27 12:59

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('applicationblocks', '0005_auto_20200721_2208'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='reference',
            name='author',
        ),
        migrations.RemoveField(
            model_name='team',
            name='author',
        ),
        migrations.AddField(
            model_name='reference',
            name='uploadedBy',
            field=models.ManyToManyField(related_name='user_id', related_query_name='user_id', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='team',
            name='user',
            field=models.ManyToManyField(to=settings.AUTH_USER_MODEL),
        ),
        migrations.RemoveField(
            model_name='reference',
            name='editor',
        ),
        migrations.AddField(
            model_name='reference',
            name='editor',
            field=models.CharField(default='', max_length=300, unique=True),
        ),
        migrations.DeleteModel(
            name='Author',
        ),
    ]
