# -*- coding: utf-8 -*-
# Generated by Django 1.10.2 on 2016-12-28 17:31
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('exordium', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='song',
            name='filetype',
            field=models.CharField(choices=[('mp3', 'mp3'), ('ogg', 'ogg'), ('m4a', 'm4a')], max_length=3),
        ),
    ]
