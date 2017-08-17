# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import connection, models, migrations

# Required parameters, change to adapt to your case
app_name = 'app'
model_name, pk_name = 'author', 'name'
related_model_name = 'article'

# Pivot table global variables, do not touch
pivot_table = '%s_%s_%ss' % (app_name, related_model_name, model_name)
fk_name, index_name = None, None

# Global db cursor
cursor = connection.cursor()


def drop_constraints_and_indices_in_pivot_table():
    global fk_name, index_name

    fk_postfix = '%%fk_%s_%s_%s' % (app_name, model_name, pk_name)
    cursor.execute(
        "SELECT constraint_name FROM information_schema.table_constraints "
        "WHERE table_name='%s' AND constraint_name LIKE "
        "'%s'" % (pivot_table, fk_postfix))
    fk_name = cursor.fetchone()[0]

    cursor.execute(
        "SELECT index_name FROM information_schema.statistics "
        "WHERE table_name='%s' AND index_name LIKE "
        "'%s_%%' AND column_name='%s_id'" %
        (pivot_table, pivot_table, model_name))
    index_name = cursor.fetchone()[0]

    cursor.execute(
        "ALTER TABLE %s DROP FOREIGN KEY %s" % (pivot_table, fk_name))
    cursor.execute(
        "ALTER TABLE %s DROP INDEX %s" % (pivot_table, index_name))
    cursor.execute(
        "ALTER TABLE %s DROP INDEX %s_id" % (pivot_table, related_model_name))


def recreate_constraints_and_indices_in_pivot_table(apps, schema_editor):
    cursor.execute(
        "ALTER TABLE %s MODIFY %s_id INT(11) NOT NULL" %
        (pivot_table, model_name))
    cursor.execute(
        "ALTER TABLE %s ADD INDEX %s (%s_id)" %
        (pivot_table, index_name, model_name))
    model_table = '%s_%s' % (app_name, model_name)
    cursor.execute(
        "ALTER TABLE %s ADD CONSTRAINT "
        "%s FOREIGN KEY (%s_id) REFERENCES %s (id)" %
        (pivot_table, fk_name, model_name, model_table))
    cursor.execute(
        "ALTER TABLE %s ADD UNIQUE KEY %s_id (%s_id, %s_id)" %
        (pivot_table, related_model_name, related_model_name, model_name))


def do_the_magic(apps, schema_editor):
    models = {}
    Model = apps.get_model(app_name, model_name)

    for i, o in enumerate(Model.objects.all()):
        o.id = i + 1
        o.save()
        models[getattr(o, pk_name)] = o.id

    drop_constraints_and_indices_in_pivot_table()

    model_table = '%s_%s' % (app_name, model_name)
    cursor.execute(
        "ALTER TABLE %s DROP PRIMARY KEY" % model_table
    )
    cursor.execute(
        "ALTER TABLE %s ADD PRIMARY KEY (id)" % model_table
    )

    cursor.execute(
        "ALTER TABLE %s "
        "CHANGE %s_id %s_id_old VARCHAR(30) NOT NULL" %
        (pivot_table, model_name, model_name))
    cursor.execute(
        "ALTER TABLE %s ADD COLUMN %s_id INT(11)" %
        (pivot_table, model_name))

    # Data adjustments in pivot table
    cursor.execute("SELECT id, %s_id_old FROM %s" % (model_name, pivot_table))
    for row in cursor:
        id, key = row[0], row[1]
        model_id = models[key]

        inner_cursor = connection.cursor()
        inner_cursor.execute(
            "UPDATE %s SET %s_id=%d WHERE id=%d" %
            (pivot_table, model_name, model_id, id))

    cursor.execute(
        "ALTER TABLE %s DROP COLUMN %s_id_old" %
        (pivot_table, model_name))


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0002_load_initial_data'),
    ]

    operations = [
        migrations.AddField(
            model_name=model_name,
            name='id',
            field=models.IntegerField(null=True),
            preserve_default=True,
        ),
        migrations.RunPython(do_the_magic),
        migrations.AlterField(
            model_name=model_name,
            name='id',
            field=models.AutoField(
                verbose_name='ID', serialize=False, auto_created=True,
                primary_key=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name=model_name,
            name=pk_name,
            field=models.CharField(unique=True, max_length=30),
            preserve_default=True,
        ),
        migrations.RunPython(recreate_constraints_and_indices_in_pivot_table),
    ]
