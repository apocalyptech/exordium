from django.shortcuts import render, get_object_or_404
from django.views import generic
from django.utils.decorators import method_decorator
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Q
from django.urls import reverse
from django.template import loader, Context
from django.http import HttpResponse, StreamingHttpResponse, Http404, HttpResponseRedirect

from django_tables2 import RequestConfig

from dynamic_preferences.registries import global_preferences_registry

from .models import Artist, Album, Song, App, AlbumArt
from .tables import ArtistTable, AlbumTable, SongTableNoAlbum, SongTableWithAlbumNoTracknum, SongTableNoAlbumNoTracknum
from . import __version__

# Create your views here.

def add_session_msg(request, message, level):
    """
    Adds a message to our session var which will get shown on
    the next page view.  Only 'success' and 'fail' are valid
    for ``level``, but values other than that will be silently
    ignored.
    """
    if level != 'success' and level != 'fail':
        return
    varname = 'exordium_msg_%s' % (level)
    if varname not in request.session:
        request.session[varname] = []
    request.session[varname].append(message)
    request.session.modified = True

def add_session_success(request, message):
    """
    Adds a success message to our session var which will get shown
    on the next page view.
    """
    add_session_msg(request, message, 'success')

def add_session_fail(request, message):
    """
    Adds a fail message to our session var which will get shown
    on the next page view.
    """
    add_session_msg(request, message, 'fail')

def populate_session_msg_context(request, context):
    """
    Takes an existing ``context`` object (as constructed in
    ``get_context_data()`` and populates any session messages
    we may have.
    """
    for varname in ['success', 'fail']:
        session_var = 'exordium_msg_%s' % (varname)
        ctx_var = 'messages_%s' % (varname)
        if session_var in request.session:
            if len(request.session[session_var]) > 0:
                context[ctx_var] = request.session[session_var]
                del request.session[session_var]

class UserAwareView(object):
    """
    Class to support our user preferences, basically.  Provides some
    functions to allow us to store user preferences if the user is
    logged in, or otherwise just log the value to the current
    session.
    """

    def get_preference(self, prefname):
        """
        Get a preference, or None
        """
        return UserAwareView.get_preference_static(self.request, prefname)

    def set_preference(self, prefname, value):
        """
        Sets a perference value
        """
        return UserAwareView.set_preference_static(self.request, prefname, value)

    @staticmethod
    def get_preference_static(request, prefname):
        """
        Get a preference, or None
        """
        full_name = 'exordium__%s' % (prefname)
        if request.user.is_authenticated():
            return request.user.preferences[full_name]
        else:
            if full_name in request.session:
                return request.session[full_name]
            else:
                return None

    @staticmethod
    def set_preference_static(request, prefname, value):
        """
        Sets a perference value
        """
        full_name = 'exordium__%s' % (prefname)
        if request.user.is_authenticated():
            request.user.preferences[full_name] = value
        else:
            request.session[full_name] = value

class TitleListView(generic.ListView, UserAwareView):
    """
    Simple extension to django.views.generic.ListView which
    allows us to set exordium_title as part of our object,
    which will then get added to the context and passed to our
    template.
    """

    exordium_title = 'Sub-Page'

    def get_context_data(self, **kwargs):
        context = super(TitleListView, self).get_context_data(**kwargs)
        context['exordium_title'] = self.exordium_title
        context['exordium_version'] = __version__
        populate_session_msg_context(self.request, context)
        return context

class TitleDetailView(generic.DetailView, UserAwareView):
    """
    Simple extension to django.views.generic.DetailView which
    allows us to set exordium_title as part of our object,
    which will then get added to the context and passed to our
    template.
    """

    exordium_title = 'Sub-Page'

    def get_context_data(self, **kwargs):
        context = super(TitleDetailView, self).get_context_data(**kwargs)
        context['exordium_title'] = self.exordium_title
        context['exordium_version'] = __version__
        populate_session_msg_context(self.request, context)
        return context

class TitleTemplateView(generic.TemplateView, UserAwareView):
    """
    Simple extension to django.views.generic.TemplateView which
    allows us to set exordium_title as part of our object,
    which will then get added to the context and passed to our
    template.
    """

    exordium_title = 'Sub-Page'

    def get_context_data(self, **kwargs):
        context = super(TitleTemplateView, self).get_context_data(**kwargs)
        context['exordium_title'] = self.exordium_title
        context['exordium_version'] = __version__
        populate_session_msg_context(self.request, context)
        return context

class IndexView(TitleTemplateView):
    template_name = 'exordium/index.html'
    exordium_title = 'Exordium Main Page'

    def get_context_data(self, **kwargs):
        context = super(IndexView, self).get_context_data(**kwargs)
        if self.get_preference('show_live'):
            albums = Album.objects.all().order_by('-time_added')
        else:
            albums = Album.objects.filter(live=False).order_by('-time_added')
        table = AlbumTable(albums)
        RequestConfig(self.request, paginate={'per_page': 20}).configure(table)
        context['album_list'] = table
        return context

class SearchView(TitleTemplateView):
    template_name = 'exordium/search.html'
    exordium_title = 'Search Results'

    def get_context_data(self, **kwargs):
        context = super(SearchView, self).get_context_data(**kwargs)

        # Grab and sanitize our search string a bit
        search = self.request.GET['q']
        if "\n" in search:
            search = search.split("\n")[0]
        if "\r" in search:
            search = search.split("\r")[0]
        if len(search) > 80:
            search = search[:80]

        # Add our query to the context
        context['q'] = search

        # Require at least three characters in the search string
        if len(search) < 3:
            context['length_error'] = True
            return context

        # Now do some searching
        show_artists = False
        show_albums = False
        show_songs = False

        artists = Artist.objects.filter(
            Q(name__icontains=search) |
            Q(normname__icontains=App.norm_name(search))
        ).order_by('name')
        if artists.count() > 0:
            show_artists = True
            table = ArtistTable(artists, view=self, prefix='artist-')
            RequestConfig(self.request).configure(table)
            context['artist_results'] = table

        album_filter = [(Q(name__icontains=search) | Q(normname__icontains=App.norm_name(search)))]
        if not self.get_preference('show_live'):
            album_filter.append(Q(live=False))
        albums = Album.objects.filter(*album_filter).order_by('name')
        if albums.count() > 0:
            show_albums = True
            table = AlbumTable(albums, prefix='album-')
            RequestConfig(self.request, paginate={'per_page': 25}).configure(table)
            context['album_results'] = table

        song_filter = [(Q(title__icontains=search) | Q(normtitle__icontains=App.norm_name(search)))]
        if not self.get_preference('show_live'):
            song_filter.append(Q(album__live=False))
        songs = Song.objects.filter(*song_filter).order_by('title')
        if songs.count() > 0:
            show_songs = True
            table = SongTableWithAlbumNoTracknum(songs, prefix='song-')
            RequestConfig(self.request).configure(table)
            context['song_results'] = table

        context['found_results'] = (show_artists or show_albums or show_songs)

        return context

class ArtistView(TitleDetailView):
    model = Artist
    slug_field = 'normname'
    template_name = 'exordium/artist.html'

    def get_context_data(self, **kwargs):
        context = super(ArtistView, self).get_context_data(**kwargs)

        album_filter=[(Q(artist=self.object) |
            Q(song__artist=self.object) |
            Q(song__group=self.object) |
            Q(song__conductor=self.object) |
            Q(song__composer=self.object))]
        if not self.get_preference('show_live'):
            album_filter.append(Q(live=False))
        albums = Album.objects.filter(*album_filter).distinct().order_by(
            'artist__various', 'miscellaneous', 'name')
        table = AlbumTable(albums, prefix='album-')
        RequestConfig(self.request).configure(table)
        context['albums'] = table

        # If the artist has too many songs, this query takes forever.
        # Only show songs if we've got <= 500 tracks.
        song_filter=[(Q(artist=self.object) |
            Q(group=self.object) |
            Q(conductor=self.object) |
            Q(composer=self.object))]
        if not self.get_preference('show_live'):
            song_filter.append(Q(album__live=False))
        song_query = Song.objects.filter(*song_filter)
        num_songs = song_query.count()
        if num_songs <= 500:
            songs = song_query.order_by('title')
            song_table = SongTableWithAlbumNoTracknum(songs, prefix='song-')
            RequestConfig(self.request).configure(song_table)
            context['songs'] = song_table
            context['have_songs'] = True
        else:
            context['have_songs'] = False

        context['exordium_title'] = 'Albums by %s' % (self.object)
        return context

class AlbumView(TitleDetailView):
    model = Album
    template_name = 'exordium/album_info.html'

    def get_context_data(self, **kwargs):
        context = super(AlbumView, self).get_context_data(**kwargs)
        songs = Song.objects.filter(album=self.object).order_by('tracknum')
        (groups, have_empty_group, conductors, have_empty_conductor,
            composers, have_empty_composer) = self.object.get_secondary_artists_tuple()
        data = []
        len_groups = len(groups)
        len_conductors = len(conductors)
        len_composers = len(composers)
        if have_empty_group:
            len_groups += 1
        if have_empty_conductor:
            len_conductors += 1
        if have_empty_composer:
            len_composers += 1
        for song in songs:
            song.set_album_secondary_artist_counts(num_groups=len_groups,
                num_conductors=len_conductors,
                num_composers=len_composers)
            data.append(song)
        if self.object.miscellaneous:
            table = SongTableNoAlbumNoTracknum(data)
        else:
            table = SongTableNoAlbum(data)
        RequestConfig(self.request).configure(table)
        if App.support_zipfile():
            context['show_download_button'] = True
        context['songs'] = table
        context['exordium_title'] = '%s / %s' % (self.object.artist, self.object)
        context['groups'] = groups
        context['conductors'] = conductors
        context['composers'] = composers
        context['have_empty_group'] = have_empty_group
        context['have_empty_conductor'] = have_empty_conductor
        context['have_empty_composer'] = have_empty_composer
        return context

class AlbumDownloadView(TitleDetailView):
    model = Album
    template_name = 'exordium/album_download.html'

    def get_context_data(self, **kwargs):
        context = super(AlbumDownloadView, self).get_context_data(**kwargs)
        context['show_download_button'] = False
        (groups, have_empty_group, conductors, have_empty_conductor,
            composers, have_empty_composer) = self.object.get_secondary_artists_tuple()
        if App.support_zipfile():
            try:
                (filenames, zipfile) = self.object.create_zip()
                context['filenames'] = filenames
                context['zip_file'] = zipfile
            except App.AlbumZipfileError as e:  # pragma: no cover
                context['error'] = 'There was a problem generating the zipfile: %s' % (e.orig_exception)
            except App.AlbumZipfileNotSupported: # pragma: no cover
                # There's actually no way to get here, since we test for App.support_zipfile()
                # before we even try to create a zipfile.  Still, I'll keep it here just in
                # case there's ever some weird bug which allows us to keep going even though
                # we don't support it.
                context['error'] = 'Exordium is not currently configured to allow zipfile creation'
            except App.AlbumZipfileAlreadyExists as e:
                context['error'] = 'Zipfile already exists.  You should be able to download with the link below.'
                context['zip_file'] = e.filename
                context['zip_mtime'] = e.timestamp
            finally:
                if 'zip_file' in context:
                    context['zip_url'] = '%s/%s' % (App.prefs['exordium__zipfile_url'], context['zip_file'])
        else:
            context['error'] = 'Exordium is not currently configured to allow zipfile creation'
        context['exordium_title'] = '%s / %s' % (self.object.artist, self.object)
        context['groups'] = groups
        context['conductors'] = conductors
        context['composers'] = composers
        context['have_empty_group'] = have_empty_group
        context['have_empty_conductor'] = have_empty_conductor
        context['have_empty_composer'] = have_empty_composer
        return context

class BrowseArtistView(TitleListView):
    model = Artist
    template_name = 'exordium/browse.html'
    exordium_title = 'Browsing Artists'

    def get_context_data(self, **kwargs):
        context = super(BrowseArtistView, self).get_context_data(**kwargs)
        artists = Artist.objects.all().order_by('name')
        table = ArtistTable(artists, view=self)
        RequestConfig(self.request).configure(table)
        context['table'] = table
        return context

class BrowseAlbumView(TitleListView):
    model = Album
    template_name = 'exordium/browse.html'
    exordium_title = 'Browsing Albums'

    def get_context_data(self, **kwargs):
        context = super(BrowseAlbumView, self).get_context_data(**kwargs)
        if self.get_preference('show_live'):
            albums = Album.objects.all().order_by('miscellaneous', 'name', 'artist__name')
        else:
            albums = Album.objects.filter(live=False).order_by('miscellaneous', 'name', 'artist__name')
        table = AlbumTable(albums)
        RequestConfig(self.request).configure(table)
        context['table'] = table
        return context

@method_decorator(staff_member_required, name='dispatch')
class LibraryView(TitleTemplateView):
    template_name = 'exordium/library.html'
    exordium_title = 'Library Management'

    def get_context_data(self, **kwargs):
        context = super(LibraryView, self).get_context_data(**kwargs)
        App.ensure_prefs()
        context['base_path'] = App.prefs['exordium__base_path']
        context['media_url'] = App.prefs['exordium__media_url']
        context['support_zipfile'] = App.support_zipfile()
        context['zipfile_url'] = App.prefs['exordium__zipfile_url']
        context['zipfile_path'] = App.prefs['exordium__zipfile_path']
        context['count_artists'] = Artist.objects.count()
        context['count_albums'] = Album.objects.count()
        context['count_songs'] = Song.objects.count()
        return context

@method_decorator(staff_member_required, name='dispatch')
class LibraryUpdateView(generic.View, UserAwareView):

    def get(self, request, *args, **kwargs):
        """
        We support GET
        """
        update_type = None
        if 'type' in request.GET:
            if request.GET['type'] == 'add':
                update_type = 'add'
            elif request.GET['type'] == 'update':
                update_type = 'update'
            else:
                add_session_fail(request, 'Invalid update type specified: "%s"' % (request.GET['type']))
                return HttpResponseRedirect(reverse('exordium:library'))
        else:
            add_session_fail(request, 'No update type specified!')
            return HttpResponseRedirect(reverse('exordium:library'))
        
        debug = 'debug' in request.GET

        return StreamingHttpResponse((line for line in self.update_generator(update_type, debug)))

    def update_generator(self, update_type, debug=False):
        template_page = loader.get_template('exordium/library_update.html')
        template_line = loader.get_template('exordium/library_update_line.html')
        if update_type == 'add':
            title = 'Add Music to Library'
            update_func = App.add
        else:
            title = 'Add/Update/Clean Library'
            update_func = App.update
        context = Context({
            'request': self.request,
            'exordium_title': title,
            'exordium_version': __version__,
            'update_type': update_type,
            'debug': debug,
        })
        populate_session_msg_context(self.request, context)
        page = template_page.render(context)
        for line in page.split("\n"):
            if line == '@__LIBRARY_UPDATE_AREA__@':
                for (status, line) in update_func():
                    yield template_line.render(Context({
                        'status': status,
                        'line': line,
                        'debug': debug,
                    }))
            else:
                yield "%s\n" % (line)

class OriginalAlbumArtView(generic.View):
    """
    Class to handle showing the original album art for an
    album.  Just a weird passthrough to the filesystem.
    Not Django-approved!
    """

    def get(self, request, *args, **kwargs):
        """
        The main request!
        """

        # We don't actually care about the extension
        extension = kwargs['extension']

        # Grab the album.  Send a 404 if it doesn't exist.
        try:
            albumid = int(kwargs['albumid'])
        except ValueError:  # pragma: no cover
            # Shouldn't be able to get here since our urls.py will
            # only accept digits for albumid
            albumid = -1
        album = get_object_or_404(Album, pk=albumid)

        filename = album.get_original_art_filename()
        if filename:
            with open(filename, 'rb') as df:
                return HttpResponse(df.read(), content_type=album.art_mime)
        else:
            raise Http404('Album art not found for album "%s / %s"' % (album.artist, album))

class AlbumArtView(generic.View, UserAwareView):
    """
    Class to handle showing album art.
    """

    def get(self, request, *args, **kwargs):
        """
        The main request!
        """

        # What size have we been requested
        size = kwargs['size']
        if size not in [t[0] for t in AlbumArt.SIZE_CHOICES]:
            # TODO: this should do something more intelligent
            raise Http404('Invalid size choice: %s' % (size))

        # Grab the album.  Send a 404 if it doesn't exist.
        try:
            albumid = int(kwargs['albumid'])
        except ValueError:  # pragma: no cover
            # Shouldn't be able to get here since our urls.py will
            # only accept digits for albumid
            albumid = -1
        album = get_object_or_404(Album, pk=albumid)

        # Try to grab the album art and display it
        art = AlbumArt.get_or_create(album, size)
        if art:
            return HttpResponse(art.image, content_type='image/jpeg')
        else:
            raise Http404('Album art not found for album "%s / %s"' % (album.artist, album))

def updateprefs(request):
    """
    Handler to update our preferences.  Will redirect back to the page we were just on.
    """
    if 'show_live' in request.POST:
        UserAwareView.set_preference_static(request, 'show_live', True)
    else:
        UserAwareView.set_preference_static(request, 'show_live', False)
    add_session_success(request, 'Set user preferences')

    # Redirect back to our previous page
    if 'HTTP_REFERER' in request.META:
        return HttpResponseRedirect(request.META['HTTP_REFERER'])
    else:
        return HttpResponseRedirect(reverse('exordium:index'))

class AlbumM3UDownloadView(generic.DetailView, UserAwareView):
    """
    View to download an M3U playlist from our album.  Useful?  Maybe?
    """
    model = Album
    template_name = 'exordium/album_stream.m3u'
    content_type = 'audio/mpegurl'

    def render_to_response(self, context, **kwargs):
        """
        Override to set a custom headers
        """
        response = super(AlbumM3UDownloadView, self).render_to_response(context, **kwargs)
        response['Content-Disposition'] = 'attachment; filename=%s_-_%s.m3u' % (
            App.norm_filename(str(context['album'].artist)),
            App.norm_filename(str(context['album'])))
        return response

@staff_member_required
def update_album_art(request, albumid):
    """
    Handler to force a full album art update on an album.  Useful if album
    art has already been associated but "better" art has been put in place.
    """
    album = get_object_or_404(Album, pk=albumid)
    retlines = album.update_album_art(full_refresh=True)
    for (status, line) in retlines:
        if status == App.STATUS_INFO or status == App.STATUS_SUCCESS:
            add_session_success(request, line)
        elif status == App.STATUS_ERROR:
            add_session_fail(request, line)

    # Now redirect back to the album
    return HttpResponseRedirect(reverse('exordium:album', args=(albumid,)))
