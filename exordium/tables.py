#!/usr/bin/env python
# vim: set expandtab tabstop=4 shiftwidth=4:

from django.contrib.staticfiles.templatetags.staticfiles import static
import django_tables2 as tables
from .models import Artist, Album, Song

class ArtistTable(tables.Table):

    name = tables.LinkColumn('exordium:artist', args=[tables.A('pk')])

    class Meta:

        model = Artist
        attrs = {'class': 'paleblue'}
        fields = ['name']

class AlbumTable(tables.Table):

    artist = tables.LinkColumn('exordium:artist', args=[tables.A('artist.pk')])
    name = tables.LinkColumn('exordium:album', args=[tables.A('pk')])
    time_added = tables.DateTimeColumn(
        verbose_name = 'Date Added',
        format='F j, Y',
        #format='F j, Y g:i A',
    )
    img = tables.TemplateColumn(
        verbose_name='',
        orderable=False,
        template_name='exordium/album_image_list.html',
    )

    class Meta:

        model = Album
        attrs = {'class': 'paleblue'}
        fields = ['img', 'artist', 'name', 'year', 'time_added']

class SongTable(tables.Table):

    artist = tables.LinkColumn('exordium:artist', args=[tables.A('artist.pk')])
    album = tables.LinkColumn(
        'exordium:album',
        verbose_name='Album',
        args=[tables.A('album.pk')]
    )
    length = tables.Column(
        footer=lambda table: table.render_length(sum(x.length for x in table.data))
    )
    # TODO: This template currently hardcodes our direct URL path
    dl = tables.TemplateColumn(
        verbose_name='',
        orderable=False,
        template_name='exordium/download_link.html'
    )

    def render_length(self, value):
        return '%d:%02d' % (value/60, value%60)

    class Meta:

        model = Song
        attrs = {'class': 'paleblue'}
        fields = ['tracknum', 'artist', 'album', 'title', 'length', 'dl']
        show_footer = True
