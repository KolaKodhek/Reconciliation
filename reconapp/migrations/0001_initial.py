# Generated by Django 5.2 on 2025-04-06 18:05

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='UploadedFile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.FileField(upload_to='reconciliation_uploads/')),
                ('upload_timestamp', models.DateTimeField(default=django.utils.timezone.now)),
                ('original_filename', models.CharField(max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name='ReconciliationReport',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reconciliation_timestamp', models.DateTimeField(default=django.utils.timezone.now)),
                ('join_columns', models.CharField(max_length=255)),
                ('ignore_columns', models.CharField(blank=True, max_length=255, null=True)),
                ('summary_json', models.JSONField()),
                ('missing_in_source_json', models.JSONField(blank=True, null=True)),
                ('missing_in_target_json', models.JSONField(blank=True, null=True)),
                ('discrepancies_json', models.JSONField(blank=True, null=True)),
                ('source_file', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='source_reports', to='reconapp.uploadedfile')),
                ('target_file', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='target_reports', to='reconapp.uploadedfile')),
            ],
        ),
    ]
