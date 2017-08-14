# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


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
    ]
