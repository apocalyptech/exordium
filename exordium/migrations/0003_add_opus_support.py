# Generated by Django 2.0.8 on 2020-05-28 20:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('exordium', '0002_add_m4a_support'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='album',
            options={'ordering': ['artist', 'name']},
        ),
        migrations.AlterModelOptions(
            name='albumart',
            options={'ordering': ['album__artist__name', 'album__name', 'size'], 'verbose_name_plural': 'Album Art'},
        ),
        migrations.AlterModelOptions(
            name='artist',
            options={'ordering': ['name']},
        ),
        migrations.AlterModelOptions(
            name='song',
            options={'ordering': ['artist', 'album', 'tracknum', 'title']},
        ),
        migrations.AlterField(
            model_name='album',
            name='art_ext',
            field=models.CharField(blank=True, default=None, max_length=4, null=True),
        ),
        migrations.AlterField(
            model_name='album',
            name='art_filename',
            field=models.CharField(blank=True, default=None, max_length=4096, null=True),
        ),
        migrations.AlterField(
            model_name='album',
            name='art_mime',
            field=models.CharField(blank=True, default=None, max_length=64, null=True),
        ),
        migrations.AlterField(
            model_name='album',
            name='art_mtime',
            field=models.IntegerField(blank=True, default=0, null=True),
        ),
        migrations.AlterField(
            model_name='artist',
            name='prefix',
            field=models.CharField(blank=True, max_length=32),
        ),
        migrations.AlterField(
            model_name='song',
            name='filetype',
            field=models.CharField(choices=[('mp3', 'mp3'), ('ogg', 'ogg'), ('m4a', 'm4a'), ('opus', 'opus')], max_length=4),
        ),
        migrations.AlterField(
            model_name='song',
            name='raw_composer',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AlterField(
            model_name='song',
            name='raw_conductor',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AlterField(
            model_name='song',
            name='raw_group',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
    ]