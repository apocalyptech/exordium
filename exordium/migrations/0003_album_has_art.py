# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2016-09-26 20:08
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('exordium', '0002_image'),
    ]

    operations = [
        migrations.AddField(
            model_name='album',
            name='has_art',
            field=models.BooleanField(default=False),
        ),
    ]
