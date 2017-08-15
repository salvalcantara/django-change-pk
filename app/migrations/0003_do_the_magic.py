# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import connection, models, migrations


cursor = connection.cursor()
fk_name, index_name = None, None


def do_the_magic(apps, schema_editor):
    global fk_name, index_name

    # Disable foreign key checks
    cursor.execute("SET foreign_key_checks = 0")

    authors = {}
    Author = apps.get_model('app', 'Author')

    for i, a in enumerate(Author.objects.all()):
        a.id = i + 1
        a.save()
        authors[a.name] = a.id

    # Schema adjustments in pivot table
    cursor.execute(
        "SELECT constraint_name FROM information_schema.table_constraints "
        "WHERE table_name='app_article_authors' AND constraint_name LIKE "
        "'app_article_author_author_id%fk_app_author_name'")
    fk_name = cursor.fetchone()[0]

    cursor.execute(
        "SELECT index_name FROM information_schema.statistics "
        "WHERE table_name='app_article_authors' AND index_name LIKE "
        "'app_article_authors_%' AND column_name='author_id'")
    index_name = cursor.fetchone()[0]

    cursor.execute(
        "ALTER TABLE app_article_authors DROP FOREIGN KEY %s" % fk_name)
    cursor.execute(
        "ALTER TABLE app_author DROP PRIMARY KEY"
    )
    cursor.execute(
        "ALTER TABLE app_author ADD PRIMARY KEY (id)"
    )
    cursor.execute(
        "ALTER TABLE app_article_authors "
        "DROP INDEX %s" % index_name)
    cursor.execute(
        "ALTER TABLE app_article_authors "
        "DROP INDEX article_id")

    cursor.execute(
        "ALTER TABLE app_article_authors "
        "CHANGE author_id author_id_old VARCHAR(30) NOT NULL")
    cursor.execute(
        "ALTER TABLE app_article_authors ADD COLUMN author_id INT(11)")

    # Data adjustments in pivot table
    cursor.execute("SELECT id, author_id_old FROM app_article_authors")
    for row in cursor:
        id, name = row[0], row[1]
        author_id = authors[name]

        inner_cursor = connection.cursor()
        inner_cursor.execute(
            "UPDATE app_article_authors SET author_id=%d WHERE id=%d" %
            (author_id, id)
        )

    # Enable foreign key checks again
    cursor.execute("SET foreign_key_checks = 1")


def make_indices(apps, schema_editor):
    # Further schema adjustments in pivot table
    cursor.execute("ALTER TABLE app_article_authors DROP COLUMN author_id_old")
    cursor.execute(
        "ALTER TABLE app_article_authors MODIFY author_id INT(11) NOT NULL")
    cursor.execute(
        "ALTER TABLE app_article_authors ADD INDEX %s (author_id)" %
        index_name)
    cursor.execute(
        "ALTER TABLE app_article_authors ADD CONSTRAINT "
        "%s FOREIGN KEY (author_id) REFERENCES app_author (id)" % fk_name)
    cursor.execute(
        "ALTER TABLE app_article_authors ADD UNIQUE KEY "
        "article_id (article_id, author_id)")


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0002_load_initial_data'),
    ]

    operations = [
        migrations.AddField(
            model_name='author',
            name='id',
            field=models.IntegerField(null=True),
            preserve_default=True,
        ),
        migrations.RunPython(do_the_magic),
        migrations.AlterField(
            model_name='author',
            name='id',
            field=models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='author',
            name='name',
            field=models.CharField(unique=True, max_length=30),
            preserve_default=True,
        ),
        migrations.RunPython(make_indices),
    ]
