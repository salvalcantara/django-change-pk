# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import connection, models, migrations


cursor = connection.cursor()


def do_the_magic(apps, schema_editor):
    # Disable foreign key checks
    cursor.execute("SET foreign_key_checks = 0")

    # Generate values for the new id column
    Author = apps.get_model('app', 'Author')
    authors = {}
    for i, a in enumerate(Author.objects.all()):
        a.id = i + 1
        a.save()
        authors[a.name] = a.id

    # Schema adjustments in pivot table
    cursor.execute(
        "ALTER TABLE app_article_authors "
        "RENAME COLUMN author_id TO author_id_old VARCHAR(30)")
    cursor.execute(
        "ALTER TABLE app_article_authors ADD COLUMN author_id INT(11)")
    cursor.execute("ALTER TABLE app_article_authors DROP FOREIGN KEY author_id")
    cursor.execute(
        "ALTER TABLE app_article_authors ADD CONSTRAINT "
        "app_article_authors_4f331e2f FOREIGN KEY ('author_id') "
        "REFERENCES app_author ('id')"
    )

    # Data adjustments in pivot table
    rows = cursor.execute("SELECT id, author_id_old FROM app_article_authors")
    for row in rows:
        id, name = row[0], row[1]
        author_id = authors[name]

        inner_cursor = connection.cursor()
        inner_cursor.execute(
            "UPDATE app_article_authors SET author_id=%d WHERE id=%d" %
            (author_id, id)
        )

    # Remove old foreign key column in pivot table
    cursor.execute("ALTER TABLE app_article_authors DROP COLUMN author_id_old")

    # Enable foreign key checks again
    cursor.execute("SET foreign_key_checks = 1")


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0002_load_initial_data'),
    ]

    operations = [
        migrations.AddField(
            model_name='author',
            name='id',
            field=models.IntegerField(unique=True, null=True),
            preserve_default=True,
        ),
        migrations.RunPython(do_the_magic),
    ]
