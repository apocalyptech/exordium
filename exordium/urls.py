#!/usr/bin/env python
# vim: set expandtab tabstop=4 shiftwidth=4:

from django.urls import re_path

from . import views

app_name = 'exordium'
urlpatterns = [
    re_path(r'^$', views.IndexView.as_view(), name='index'),
    re_path(r'^updateprefs/$', views.updateprefs, name='updateprefs'),
    re_path(r'^search/$', views.SearchView.as_view(), name='search'),
    re_path(r'^browse/artist/$', views.BrowseArtistView.as_view(), name='browse_artist'),
    re_path(r'^browse/album/$', views.BrowseAlbumView.as_view(), name='browse_album'),
    re_path(r'^artist/(?P<slug>.+)/$', views.ArtistView.as_view(), name='artist'),
    re_path(r'^album/(?P<pk>[0-9]+)/$', views.AlbumView.as_view(), name='album'),
    re_path(r'^album/(?P<pk>[0-9]+)/download/$', views.AlbumDownloadView.as_view(), name='albumdownload'),
    re_path(r'^album/(?P<pk>[0-9]+)/stream.m3u$', views.AlbumM3UDownloadView.as_view(), name='m3udownload'),
    re_path(r'^album/(?P<albumid>[0-9]+)/updateart/$', views.update_album_art, name='albumartupdate'),
    re_path(r'^album/(?P<albumid>[0-9]+)/cover.(?P<extension>[a-z]+)$', views.OriginalAlbumArtView.as_view(), name='origalbumart'),
    re_path(r'^album/(?P<albumid>[0-9]+)/cover-(?P<size>[a-z]+).jpg$', views.AlbumArtView.as_view(), name='albumart'),
    re_path(r'^library/$', views.LibraryView.as_view(), name='library'),
    re_path(r'^library/update/$', views.LibraryUpdateView.as_view(), name='library_update'),
]

