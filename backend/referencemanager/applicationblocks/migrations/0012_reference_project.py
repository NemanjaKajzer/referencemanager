# Generated by Django 3.0.8 on 2020-08-29 17:06

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('applicationblocks', '0011_auto_20200829_1840'),
    ]

    operations = [
        migrations.AddField(
            model_name='reference',
            name='project',
            field=models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='project_id', related_query_name='project_id', to='applicationblocks.Project'),
        ),
    ]
