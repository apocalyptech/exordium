#!/usr/bin/env python
# vim: set expandtab tabstop=4 shiftwidth=4:

import datetime
from django.contrib.staticfiles.templatetags.staticfiles import static
from django.db.models import Q
import django_tables2 as tables
from .models import Artist, Album, Song

class ArtistTable(tables.Table):

    name = tables.LinkColumn('exordium:artist', args=[tables.A('pk')])
    albums = tables.Column(
        verbose_name='Albums',
        orderable=False,
        empty_values=(),
    )
    tracks = tables.Column(
        verbose_name='Tracks',
        orderable=False,
        empty_values=(),
    )

    def render_albums(self, record, **kwargs):
        """
        Show the number of albums this artist has.
        """
        return Album.objects.filter(
            Q(artist=record) |
            Q(song__artist=record) |
            Q(song__group=record) |
            Q(song__conductor=record) |
            Q(song__composer=record)
        ).distinct().count()

    def render_tracks(self, record, **kwargs):
        """
        Show the number of tracks this artist has
        """
        return Song.objects.filter(
            Q(artist=record) | Q(group=record) |
            Q(conductor=record) | Q(composer=record)
        ).count()

    class Meta:

        model = Artist
        attrs = {'class': 'paleblue', 'id': 'songtable'}
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
    tracks = tables.Column(
        verbose_name='Tracks',
        orderable=False,
        empty_values=(),
    )
    time = tables.Column(
        verbose_name='Length',
        orderable=False,
        empty_values=(),
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

    def render_tracks(self, record, **kwargs):
        """
        Get a count of tracks for this album
        """
        return(record.song_set.count())

    def render_time(self, record, **kwargs):
        """
        Get a total time for this album
        """
        #delta = datetime.timedelta(seconds=record.get_total_time())
        length = record.get_total_time()
        minutes, seconds = divmod(length, 60)
        if minutes > 60:
            hours, minutes = divmod(minutes, 60)
            return('%dh%dm' % (hours, minutes))
        else:
            return('%dm' % (minutes))

    class Meta:

        model = Album
        per_page = 50
        attrs = {'class': 'paleblue', 'id': 'albumtable'}
        fields = ['img', 'artist', 'name', 'tracks', 'time', 'year', 'time_added']

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
