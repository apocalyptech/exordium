#!/usr/bin/env python
# vim: set expandtab tabstop=4 shiftwidth=4:

from django.conf.urls import url

from . import views

app_name = 'exordium'
urlpatterns = [
    url(r'^$', views.IndexView.as_view(), name='index'),
    url(r'^search/$', views.SearchView.as_view(), name='search'),
    url(r'^browse/artist/$', views.BrowseArtistView.as_view(), name='browse_artist'),
    url(r'^browse/album/$', views.BrowseAlbumView.as_view(), name='browse_album'),
    url(r'^artist/(?P<pk>[0-9]+)/$', views.ArtistView.as_view(), name='artist'),
    url(r'^album/(?P<pk>[0-9]+)/$', views.AlbumView.as_view(), name='album'),
    url(r'^album/(?P<albumid>[0-9]+)/cover.(?P<extension>[a-z]+)$', views.OriginalAlbumArtView.as_view(), name='origalbumart'),
    url(r'^album/(?P<albumid>[0-9]+)/cover-(?P<size>[a-z]+).jpg$', views.AlbumArtView.as_view(), name='albumart'),
    url(r'^library/$', views.LibraryView.as_view(), name='library'),
    url(r'^library/add/$', views.LibraryAddView.as_view(), name='library_add'),
    url(r'^library/update/$', views.LibraryUpdateView.as_view(), name='library_update'),
]

