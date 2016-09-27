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

    #artist = tables.LinkColumn('exordium:artist', args=[tables.A('artist.pk')])
    artist = tables.TemplateColumn(
        verbose_name='Artist',
        orderable=True,
        order_by=('artist.name'),
        template_name='exordium/album_artist_column.html',
    )
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

    def render_year(self, value=0, **kwargs):
        """
        Custom formatting for year (ie: don't display anything if the
        year is zero)
        """
        if value == 0:
            return ''
        else:
            return '%d' % (value)

    class Meta:

        model = Album
        attrs = {'class': 'paleblue'}
        fields = ['img', 'artist', 'name', 'year', 'time_added']

class SongTable(tables.Table):

    #artist = tables.LinkColumn('exordium:artist', args=[tables.A('artist.pk')])
    artist = tables.TemplateColumn(
        verbose_name='Artist',
        orderable=True,
        order_by=('artist.name'),
        template_name='exordium/song_artist_column.html',
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

class SongTableWithAlbum(SongTable):

    album = tables.LinkColumn(
        'exordium:album',
        verbose_name='Album',
        args=[tables.A('album.pk')]
    )

    class Meta:
        model = Song
        attrs = {'class': 'paleblue'}
        show_footer = True
        fields = ['tracknum', 'artist', 'album', 'title', 'length', 'dl']

class SongTableNoAlbum(SongTable):

    class Meta:
        model = Song
        attrs = {'class': 'paleblue'}
        show_footer = True
        fields = ['tracknum', 'artist', 'title', 'length', 'dl']
