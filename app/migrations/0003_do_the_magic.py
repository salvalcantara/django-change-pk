# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import connection, models, migrations

# ------------------------------------------------------------------------------
# --------------- Input parameters: change to adapt to your case ---------------
# ------------------------------------------------------------------------------

dependencies = [
    ('app', '0002_load_initial_data'),
]

# The model with the pk column to be replaced with the default auto field (id)
model_name = 'author'

# Info for the current pk column
pk_name = 'name'
pk_sql_type = 'VARCHAR(30)'
pk_final_django_field = models.CharField(max_length=30, unique=True)
#                       This is the column definition as it appears in
#                       models.py after replacing primary_key=True with
#                       unique=True

# The other model being part of the many-to-many relationship
related_model_name = 'article'
related_model_owns_m2m = True  # Set to False if m2m rel. is defined in model

# ------------------------------------------------------------------------------

# Set the name of the Django app from the 1st dependency
app_name = dependencies[0][0]

# The model table name
model_table = '%s_%s' % (app_name, model_name)

# Pivot table global variables
if related_model_owns_m2m:
    pivot_table = '%s_%s_%ss' % (app_name, related_model_name, model_name)
else:
    pivot_table = '%s_%s_%ss' % (app_name, model_name, related_model_name)
fk_name, index_name = None, None

# Global db cursor
cursor = connection.cursor()


def drop_constraints_and_indices_in_pivot_table():
    global fk_name, index_name

    fk_postfix = '%%_fk_%s_%s_%s' % (app_name, model_name, pk_name)
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


def do_most_of_the_surgery(apps, schema_editor):
    models = {}
    Model = apps.get_model(app_name, model_name)

    # Generate values for the new id column
    for i, o in enumerate(Model.objects.all()):
        o.id = i + 1
        o.save()
        models[getattr(o, pk_name)] = o.id

    # Work on the pivot table before going on
    drop_constraints_and_indices_in_pivot_table()

    # Drop current pk index and create the new one
    cursor.execute(
        "ALTER TABLE %s DROP PRIMARY KEY" % model_table
    )
    cursor.execute(
        "ALTER TABLE %s ADD PRIMARY KEY (id)" % model_table
    )

    # Rename the fk column in the pivot table
    cursor.execute(
        "ALTER TABLE %s "
        "CHANGE %s_id %s_id_old %s NOT NULL" %
        (pivot_table, model_name, model_name, pk_sql_type))
    # ... and create a new one for the new id
    cursor.execute(
        "ALTER TABLE %s ADD COLUMN %s_id INT(11)" %
        (pivot_table, model_name))

    # Fill in the new column in the pivot table
    cursor.execute("SELECT id, %s_id_old FROM %s" % (model_name, pivot_table))
    for row in cursor:
        id, key = row[0], row[1]
        model_id = models[key]

        inner_cursor = connection.cursor()
        inner_cursor.execute(
            "UPDATE %s SET %s_id=%d WHERE id=%d" %
            (pivot_table, model_name, model_id, id))

    # Drop the old (renamed) column in pivot table, no longer needed
    cursor.execute(
        "ALTER TABLE %s DROP COLUMN %s_id_old" %
        (pivot_table, model_name))


def recreate_constraints_and_indices_in_pivot_table():
    cursor.execute(
        "ALTER TABLE %s MODIFY %s_id INT(11) NOT NULL" %
        (pivot_table, model_name))
    cursor.execute(
        "ALTER TABLE %s ADD INDEX %s (%s_id)" %
        (pivot_table, index_name, model_name))

    fk_postfix = '_fk_%s_%s_%s' % (app_name, model_name, pk_name)
    new_fk_postfix = '_fk_%s_%s_%s' % (app_name, model_name, 'id')
    new_fk_name = fk_name.replace(fk_postfix, new_fk_postfix)

    cursor.execute(
        "ALTER TABLE %s ADD CONSTRAINT "
        "%s FOREIGN KEY (%s_id) REFERENCES %s (id)" %
        (pivot_table, new_fk_name, model_name, model_table))
    cursor.execute(
        "ALTER TABLE %s ADD UNIQUE KEY %s_id (%s_id, %s_id)" %
        (pivot_table, related_model_name, related_model_name, model_name))


def do_the_final_lifting(apps, schema_editor):
    """
    Don't know why but this operation:

        migrations.AlterField(
            model_name=model_name,
            name='id',
            field=models.AutoField(
                verbose_name='ID', serialize=False, auto_created=True,
                primary_key=True),
            preserve_default=True,
        ),

    creates a unique key in the database which is not needed since the id
    field is also marked as primary key. We do not want the redundant index,
    so we will just drop it.
    """

    # Get name of the redundant index
    cursor.execute(
        "SELECT index_name FROM information_schema.statistics "
        "WHERE table_name='%s' AND index_name LIKE "
        "'%s_id%%' AND column_name='id'" %
        (model_table, model_table))
    row = cursor.fetchone()

    # Drop the redundant index
    if row:
        index_name = row[0]
        cursor.execute(
            "ALTER TABLE %s DROP INDEX %s" % (model_table, index_name))
    else:
        index_name = '%s_id_3458ba9aebc47455_uniq' % model_table

    # Create a new unique index for the old pk column
    index_prefix = '%s_id' % model_table
    new_index_prefix = '%s_%s' % (model_table, pk_name)
    new_index_name = index_name.replace(index_prefix, new_index_prefix)

    cursor.execute(
        "ALTER TABLE %s ADD UNIQUE KEY %s (%s)" %
        (model_table, new_index_name, pk_name))

    # Finally, work on the pivot table
    recreate_constraints_and_indices_in_pivot_table()


class Migration(migrations.Migration):

    dependencies = dependencies

    operations = [
        migrations.AddField(
            model_name=model_name,
            name='id',
            field=models.IntegerField(null=True),
            preserve_default=True,
        ),
        migrations.RunPython(do_most_of_the_surgery),
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
            field=pk_final_django_field,
            preserve_default=True,
        ),
        migrations.RunPython(do_the_final_lifting),
    ]
