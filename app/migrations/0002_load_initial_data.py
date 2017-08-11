# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import connection, migrations
from django.core.management import call_command


def load_fixture(apps, schema_editor):
    call_command('loaddata', 'initial_data.yml', app_label='app')

def unload_fixture(apps, schema_editor):
    "Brutally deleting all entries for the tables at hand..."

    cursor = connection.cursor()
    cursor.execute("SET foreign_key_checks = 0")
    cursor.execute("TRUNCATE TABLE app_author")
    cursor.execute("TRUNCATE TABLE app_article")
    cursor.execute("TRUNCATE TABLE app_article_authors")
    cursor.execute("SET foreign_key_checks = 1")

class Migration(migrations.Migration):

    dependencies = [
        ('app', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(load_fixture, reverse_code=unload_fixture),
    ]
