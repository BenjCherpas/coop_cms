# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('coop_cms', '0012_auto_20170502_1125'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='fragment',
            unique_together=set([('type', 'name')]),
        ),
    ]
