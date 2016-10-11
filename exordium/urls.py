#!/usr/bin/env python
# vim: set expandtab tabstop=4 shiftwidth=4:

from django.conf.urls import url

from . import views

app_name = 'exordium'
urlpatterns = [
    url(r'^$', views.IndexView.as_view(), name='index'),
    url(r'^updateprefs/$', views.updateprefs, name='updateprefs'),
    url(r'^search/$', views.SearchView.as_view(), name='search'),
    url(r'^browse/artist/$', views.BrowseArtistView.as_view(), name='browse_artist'),
    url(r'^browse/album/$', views.BrowseAlbumView.as_view(), name='browse_album'),
    url(r'^artist/(?P<slug>.+)/$', views.ArtistView.as_view(), name='artist'),
    url(r'^album/(?P<pk>[0-9]+)/$', views.AlbumView.as_view(), name='album'),
    url(r'^album/(?P<pk>[0-9]+)/download/$', views.AlbumDownloadView.as_view(), name='albumdownload'),
    url(r'^album/(?P<pk>[0-9]+)/stream.m3u$', views.AlbumM3UDownloadView.as_view(), name='m3udownload'),
    url(r'^album/(?P<albumid>[0-9]+)/updateart/$', views.update_album_art, name='albumartupdate'),
    url(r'^album/(?P<albumid>[0-9]+)/cover.(?P<extension>[a-z]+)$', views.OriginalAlbumArtView.as_view(), name='origalbumart'),
    url(r'^album/(?P<albumid>[0-9]+)/cover-(?P<size>[a-z]+).jpg$', views.AlbumArtView.as_view(), name='albumart'),
    url(r'^library/$', views.LibraryView.as_view(), name='library'),
    url(r'^library/update/$', views.LibraryUpdateView.as_view(), name='library_update'),
]

