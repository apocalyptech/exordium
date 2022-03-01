from .base import ExordiumTests

from django.utils import html
from django.urls import reverse

from exordium.models import Artist, Album, Song, App, AlbumArt

class SearchViewTests(ExordiumTests):
    """
    Tests for our search page.
    """

    def test_empty_search_string(self):
        """
        Test what happens with an empty search string.
        """

        response = self.client.get(reverse('exordium:search'), {'q': ''})
        self.assertEqual(response.status_code, 200)
        self.assertIn('length_error', response.context)
        self.assertNotIn('song_results', response.context)
        self.assertNotIn('album_results', response.context)
        self.assertNotIn('artist_results', response.context)
        self.assertNotIn('found_results', response.context)
        self.assertContains(response, 'Search strings must be at least three characters')

    def test_short_search_string(self):
        """
        Test what happens with a short search string.  Shoul be the same
        results as for no search string, really.
        """

        response = self.client.get(reverse('exordium:search'), {'q': 'qu'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('length_error', response.context)
        self.assertNotIn('song_results', response.context)
        self.assertNotIn('album_results', response.context)
        self.assertNotIn('artist_results', response.context)
        self.assertNotIn('found_results', response.context)
        self.assertContains(response, 'Search strings must be at least three characters')

    def test_no_results(self):
        """
        Test what happens when there are literally no results.
        """

        response = self.client.get(reverse('exordium:search'), {'q': 'que'})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('length_error', response.context)
        self.assertNotIn('song_results', response.context)
        self.assertNotIn('album_results', response.context)
        self.assertNotIn('artist_results', response.context)
        self.assertIn('found_results', response.context)
        self.assertEqual(response.context['found_results'], False)
        self.assertContains(response, 'No results found!')

    def test_find_artist(self):
        """
        Test a successful search for an artist
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3')
        self.run_add()

        artist = Artist.objects.get(name='Artist')

        response = self.client.get(reverse('exordium:search'), {'q': 'artist'})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('song_results', response.context)
        self.assertNotIn('album_results', response.context)
        self.assertIn('artist_results', response.context)
        self.assertIn('found_results', response.context)
        self.assertEqual(response.context['found_results'], True)
        self.assertNotContains(response, 'No results found!')

        self.assertQuerysetEqual(response.context['artist_results'].data, [repr(artist)])
        self.assertContains(response, 'Artists')
        self.assertContains(response, '%s<' % (artist))
        self.assertContains(response, reverse('exordium:artist', args=(artist.normname,)))
        self.assertContains(response, '1 artist')

    def test_with_linefeed(self):
        """
        Test a search with a linefeed in the search string - should only
        search for the bit before the newline
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3')
        self.run_add()

        artist = Artist.objects.get(name='Artist')

        response = self.client.get(reverse('exordium:search'), {'q': "artist\nname"})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('song_results', response.context)
        self.assertNotIn('album_results', response.context)
        self.assertIn('artist_results', response.context)
        self.assertIn('found_results', response.context)
        self.assertEqual(response.context['found_results'], True)
        self.assertNotContains(response, 'No results found!')

        self.assertQuerysetEqual(response.context['artist_results'].data, [repr(artist)])
        self.assertContains(response, 'Artists')
        self.assertContains(response, '%s<' % (artist))
        self.assertContains(response, reverse('exordium:artist', args=(artist.normname,)))
        self.assertContains(response, '1 artist')

    def test_with_carriagereturn(self):
        """
        Test a search with a carriage return in the search string - should only
        search for the bit before the newline
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3')
        self.run_add()

        artist = Artist.objects.get(name='Artist')

        response = self.client.get(reverse('exordium:search'), {'q': "artist\rname"})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('song_results', response.context)
        self.assertNotIn('album_results', response.context)
        self.assertIn('artist_results', response.context)
        self.assertIn('found_results', response.context)
        self.assertEqual(response.context['found_results'], True)
        self.assertNotContains(response, 'No results found!')

        self.assertQuerysetEqual(response.context['artist_results'].data, [repr(artist)])
        self.assertContains(response, 'Artists')
        self.assertContains(response, '%s<' % (artist))
        self.assertContains(response, reverse('exordium:artist', args=(artist.normname,)))
        self.assertContains(response, '1 artist')

    def test_with_very_long_search(self):
        """
        We limit searches to 80 characters - anything more than that
        will get truncated.  I'm... not exactly sure why I'm doing that?
        I guess it does seem like a good idea to put some kind of a cap
        on that, lest the database complain or something, but I rather
        doubt it would actually be a problem.  Whatever, we'll test for
        it anyway.
        """
        self.add_mp3(artist='here is a very long artist name whose name exceeds eighty characters and we will search on it',
            title='Title 1', album='Album', filename='song1.mp3')
        self.run_add()

        artist = Artist.objects.get(name__startswith='here is a very')

        response = self.client.get(reverse('exordium:search'),
            {'q': 'here is a very long artist name whose name exceeds eighty characters and we will search xyzzy'})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('song_results', response.context)
        self.assertNotIn('album_results', response.context)
        self.assertIn('artist_results', response.context)
        self.assertIn('found_results', response.context)
        self.assertEqual(response.context['found_results'], True)
        self.assertNotContains(response, 'No results found!')

        self.assertQuerysetEqual(response.context['artist_results'].data, [repr(artist)])
        self.assertContains(response, 'Artists')
        self.assertContains(response, '%s<' % (artist))
        self.assertContains(response, reverse('exordium:artist', args=(artist.normname,)))
        self.assertContains(response, '1 artist')

    def test_find_album(self):
        """
        Test a successful search for an album
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3')
        self.run_add()

        album = Album.objects.get()

        response = self.client.get(reverse('exordium:search'), {'q': 'album'})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('song_results', response.context)
        self.assertIn('album_results', response.context)
        self.assertNotIn('artist_results', response.context)
        self.assertIn('found_results', response.context)
        self.assertEqual(response.context['found_results'], True)
        self.assertNotContains(response, 'No results found!')

        self.assertQuerysetEqual(response.context['album_results'].data, [repr(album)])
        self.assertContains(response, 'Albums')
        self.assertContains(response, '%s<' % (album))
        self.assertContains(response, reverse('exordium:album', args=(album.pk,)))
        self.assertContains(response, reverse('exordium:artist', args=(album.artist.normname,)))
        self.assertContains(response, '1 album')

    def test_find_song(self):
        """
        Test a successful search for a song
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3')
        self.run_add()

        song = Song.objects.get()

        response = self.client.get(reverse('exordium:search'), {'q': 'title'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('song_results', response.context)
        self.assertNotIn('album_results', response.context)
        self.assertNotIn('artist_results', response.context)
        self.assertIn('found_results', response.context)
        self.assertEqual(response.context['found_results'], True)
        self.assertNotContains(response, 'No results found!')

        self.assertQuerysetEqual(response.context['song_results'].data, [repr(song)])
        self.assertContains(response, 'Songs')
        self.assertContains(response, '%s<' % (song.title))
        self.assertContains(response, reverse('exordium:album', args=(song.album.pk,)))
        self.assertContains(response, reverse('exordium:artist', args=(song.artist.normname,)))
        self.assertContains(response, '1 song')

    def test_find_all(self):
        """
        Test a successful search which finds one of each type
        """
        self.add_mp3(artist='Artist Ocelot', title='Title Ocelot',
            album='Album Ocelot', filename='song1.mp3')
        self.run_add()

        song = Song.objects.get()
        album = Album.objects.get()
        artist = Artist.objects.get(name='Artist Ocelot')

        response = self.client.get(reverse('exordium:search'), {'q': 'ocelot'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('song_results', response.context)
        self.assertIn('album_results', response.context)
        self.assertIn('artist_results', response.context)
        self.assertIn('found_results', response.context)
        self.assertEqual(response.context['found_results'], True)
        self.assertNotContains(response, 'No results found!')

        self.assertQuerysetEqual(response.context['artist_results'].data, [repr(artist)])
        self.assertContains(response, 'Artists')
        self.assertContains(response, '%s<' % (artist))
        self.assertContains(response, reverse('exordium:artist', args=(artist.normname,)))
        self.assertContains(response, '1 artist')

        self.assertQuerysetEqual(response.context['album_results'].data, [repr(album)])
        self.assertContains(response, 'Albums')
        self.assertContains(response, '%s<' % (album))
        self.assertContains(response, reverse('exordium:album', args=(album.pk,)))
        self.assertContains(response, reverse('exordium:artist', args=(album.artist.normname,)))
        self.assertContains(response, '1 album')

        self.assertQuerysetEqual(response.context['song_results'].data, [repr(song)])
        self.assertContains(response, 'Songs')
        self.assertContains(response, '%s<' % (song.title))
        self.assertContains(response, reverse('exordium:album', args=(song.album.pk,)))
        self.assertContains(response, reverse('exordium:artist', args=(song.artist.normname,)))
        self.assertContains(response, '1 song')

    def run_normalization_test(self, query):
        """
        Base function to use for queries which make use of our normalization
        functions.  Sets up a track with various characters and then runs the
        specified query against it, hoping to find a match.

        Don't ask me where I got that name from.
        """
        self.add_mp3(artist='Artist Æthër & Stràuß', title='Title Æthër & Stràuß',
            album='Album Æthër & Stràuß', filename='song1.mp3')
        self.run_add()

        song = Song.objects.get()
        album = Album.objects.get()
        artist = Artist.objects.get(name='Artist Æthër & Stràuß')

        response = self.client.get(reverse('exordium:search'), {'q': query})
        self.assertEqual(response.status_code, 200)
        self.assertIn('song_results', response.context)
        self.assertIn('album_results', response.context)
        self.assertIn('artist_results', response.context)
        self.assertIn('found_results', response.context)
        self.assertEqual(response.context['found_results'], True)
        self.assertNotContains(response, 'No results found!')

        self.assertQuerysetEqual(response.context['artist_results'].data, [repr(artist)])
        self.assertContains(response, 'Artists')
        self.assertContains(response, '%s<' % (html.escape(artist)))
        self.assertContains(response, reverse('exordium:artist', args=(artist.normname,)))
        self.assertContains(response, '1 artist')

        self.assertQuerysetEqual(response.context['album_results'].data, [repr(album)])
        self.assertContains(response, 'Albums')
        self.assertContains(response, '%s<' % (html.escape(album)))
        self.assertContains(response, reverse('exordium:album', args=(album.pk,)))
        self.assertContains(response, reverse('exordium:artist', args=(album.artist.normname,)))
        self.assertContains(response, '1 album')

        self.assertQuerysetEqual(response.context['song_results'].data, [repr(song)])
        self.assertContains(response, 'Songs')
        self.assertContains(response, '%s<' % (html.escape(song.title)))
        self.assertContains(response, reverse('exordium:album', args=(song.album.pk,)))
        self.assertContains(response, reverse('exordium:artist', args=(song.artist.normname,)))
        self.assertContains(response, '1 song')

    def test_normalized_full(self):
        """
        Test a search against normalized data using the original strings.
        """
        self.run_normalization_test('Æthër & Stràuß')

    def test_normalized_plain(self):
        """
        Test a search against normalized data using plain ascii
        """
        self.run_normalization_test('aether and strauss')

    def test_normalized_mixed(self):
        """
        Test a search against normalized data using a mixed query
        """
        self.run_normalization_test('aether & Stràuß')

    def test_classical_album(self):
        """
        Search for a classical album by its title - just to make sure that
        we're displaying all the relevant artists in the artist column.
        """
        self.add_mp3(artist='Main Artist', title='Title 1',
            group='Group', conductor='Conductor', composer='Composer',
            album='Main Album', filename='song1.mp3')
        self.run_add()

        album = Album.objects.get()
        artists = [
            Artist.objects.get(name='Main Artist'),
            Artist.objects.get(name='Group'),
            Artist.objects.get(name='Conductor'),
            Artist.objects.get(name='Composer'),
        ]

        response = self.client.get(reverse('exordium:search'), {'q': 'main album'})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('song_results', response.context)
        self.assertIn('album_results', response.context)
        self.assertNotIn('artist_results', response.context)
        self.assertIn('found_results', response.context)
        self.assertEqual(response.context['found_results'], True)
        self.assertNotContains(response, 'No results found!')

        self.assertQuerysetEqual(response.context['album_results'].data, [repr(album)])
        self.assertContains(response, 'Albums')
        self.assertContains(response, '%s<' % (album))
        self.assertContains(response, reverse('exordium:album', args=(album.pk,)))
        for artist in artists:
            self.assertContains(response, reverse('exordium:artist', args=(artist.normname,)))
            self.assertContains(response, str(artist))
        self.assertContains(response, '1 album')

    def test_classical_song(self):
        """
        Search for a classical song by its title - just to make sure that
        we're displaying all the relevant artists in the artist column.
        """
        self.add_mp3(artist='Main Artist', title='Title 1',
            group='Group', conductor='Conductor', composer='Composer',
            album='Main Album', filename='song1.mp3')
        self.run_add()

        song = Song.objects.get()
        artists = [
            Artist.objects.get(name='Main Artist'),
            Artist.objects.get(name='Group'),
            Artist.objects.get(name='Conductor'),
            Artist.objects.get(name='Composer'),
        ]

        response = self.client.get(reverse('exordium:search'), {'q': 'title'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('song_results', response.context)
        self.assertNotIn('album_results', response.context)
        self.assertNotIn('artist_results', response.context)
        self.assertIn('found_results', response.context)
        self.assertEqual(response.context['found_results'], True)
        self.assertNotContains(response, 'No results found!')

        self.assertQuerysetEqual(response.context['song_results'].data, [repr(song)])
        self.assertContains(response, 'Songs')
        self.assertContains(response, '%s<' % (song.title))
        self.assertContains(response, reverse('exordium:album', args=(song.album.pk,)))
        for artist in artists:
            self.assertContains(response, reverse('exordium:artist', args=(artist.normname,)))
            self.assertContains(response, str(artist))
        self.assertContains(response, '1 song')

    def test_pagination_artist(self):
        """
        Test pagination on our artist results.  Will show a total of 25 artists.
        Will fake our data by inserting directly into the DB, to save on testing
        time.
        """
        artists = {}
        for num in range(35):
            artists[num] = Artist.objects.create(
                name='Artist %02d' % (num+1),
                normname='artist %02d' % (num+1),
            )

        # Page 1
        response = self.client.get(reverse('exordium:search'), {'q': 'artist'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '25 of 35 artists')
        self.assertContains(response, 'artist-page=2')
        self.assertEqual(len(response.context['artist_results'].data), 35)
        for num in range(25):
            self.assertContains(response, '%s<' % (artists[num]))
            self.assertContains(response, reverse('exordium:artist', args=(artists[num].normname,)))
        for num in range(25, 35):
            self.assertNotContains(response, '%s<' % (artists[num]))
            self.assertNotContains(response, reverse('exordium:artist', args=(artists[num].normname,)))

        # Page 2
        response = self.client.get(reverse('exordium:search'), {'q': 'artist', 'artist-page': 2})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '10 of 35 artists')
        self.assertContains(response, 'artist-page=1')
        self.assertEqual(len(response.context['artist_results'].data), 35)
        for num in range(25):
            self.assertNotContains(response, '%s<' % (artists[num]))
            self.assertNotContains(response, reverse('exordium:artist', args=(artists[num].normname,)))
        for num in range(25, 35):
            self.assertContains(response, '%s<' % (artists[num]))
            self.assertContains(response, reverse('exordium:artist', args=(artists[num].normname,)))

    def test_pagination_album(self):
        """
        Test pagination on our album results.  Will show a total of 25 albums.
        Will fake our data by inserting directly into the DB, to save on testing
        time.
        """
        artist = Artist.objects.create(name='Artist', normname='artist')
        albums = {}
        for num in range(35):
            albums[num] = Album.objects.create(
                name='Album %02d' % (num+1),
                normname='album %02d' % (num+1),
                artist=artist,
            )
            Song.objects.create(
                artist=artist,
                album=albums[num],
                title='Title %03d' % (num+1),
                year=0,
                tracknum=0,
                normtitle='title %03d' % (num+1),
                raw_artist='artist',
                filetype=Song.MP3,
                bitrate=128000,
                mode=Song.CBR,
                size=123000,
                length=90,
                sha256sum='0cf31fc7d968ec16c69758f9b0ebb2355471d5694a151b40e5e4f8641b061092',
            )

        # Page 1
        response = self.client.get(reverse('exordium:search'), {'q': 'album'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '25 of 35 albums')
        self.assertContains(response, 'album-page=2')
        self.assertEqual(len(response.context['album_results'].data), 35)
        self.assertContains(response, reverse('exordium:artist', args=(artist.normname,)))
        for num in range(25):
            self.assertContains(response, '%s<' % (albums[num]))
            self.assertContains(response, reverse('exordium:album', args=(albums[num].pk,)))
        for num in range(25, 35):
            self.assertNotContains(response, '%s<' % (albums[num]))
            self.assertNotContains(response, reverse('exordium:album', args=(albums[num].pk,)))

        # Page 2
        response = self.client.get(reverse('exordium:search'), {'q': 'album', 'album-page': 2})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '10 of 35 albums')
        self.assertContains(response, 'album-page=1')
        self.assertEqual(len(response.context['album_results'].data), 35)
        self.assertContains(response, reverse('exordium:artist', args=(artist.normname,)))
        for num in range(25):
            self.assertNotContains(response, '%s<' % (albums[num]))
            self.assertNotContains(response, reverse('exordium:album', args=(albums[num].pk,)))
        for num in range(25, 35):
            self.assertContains(response, '%s<' % (albums[num]))
            self.assertContains(response, reverse('exordium:album', args=(albums[num].pk,)))

    def test_pagination_song(self):
        """
        Test pagination on our song results.  Will show a total of 25 songs.
        Will fake our data by inserting directly into the DB, to save on testing
        time.
        """
        artist = Artist.objects.create(name='Artist', normname='artist')
        album = Album.objects.create(name='Album', normname='album', artist=artist)
        songs = {}
        for num in range(35):
            songs[num] = Song.objects.create(
                artist=artist,
                album=album,
                title='Title %03d' % (num+1),
                year=0,
                tracknum=0,
                normtitle='title %03d' % (num+1),
                raw_artist='artist',
                filetype=Song.MP3,
                bitrate=128000,
                mode=Song.CBR,
                size=123000,
                length=90,
                sha256sum='0cf31fc7d968ec16c69758f9b0ebb2355471d5694a151b40e5e4f8641b061092',
            )

        # Page 1
        response = self.client.get(reverse('exordium:search'), {'q': 'title'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '25 of 35 songs')
        self.assertContains(response, 'song-page=2')
        self.assertEqual(len(response.context['song_results'].data), 35)
        self.assertContains(response, reverse('exordium:artist', args=(artist.normname,)))
        self.assertContains(response, reverse('exordium:album', args=(album.pk,)))
        for num in range(25):
            self.assertContains(response, '%s<' % (songs[num].title))
        for num in range(25, 35):
            self.assertNotContains(response, '%s<' % (songs[num].title))

        # Page 2
        response = self.client.get(reverse('exordium:search'), {'q': 'title', 'song-page': 2})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '10 of 35 songs')
        self.assertContains(response, 'song-page=1')
        self.assertEqual(len(response.context['song_results'].data), 35)
        self.assertContains(response, reverse('exordium:artist', args=(artist.normname,)))
        self.assertContains(response, reverse('exordium:album', args=(album.pk,)))
        for num in range(25):
            self.assertNotContains(response, '%s<' % (songs[num].title))
        for num in range(25, 35):
            self.assertContains(response, '%s<' % (songs[num].title))

    def test_sorting_artist(self):
        """
        Test at least one case of artist sorting.
        """
        self.add_mp3(artist='Artist 1', title='Title 1',
            album='Album', year=2016, filename='song1.mp3')
        self.add_mp3(artist='Artist 2', title='Title 2',
            album='Album', year=2006, filename='song2.mp3')
        self.add_mp3(artist='Artist 3', title='Title 3',
            album='Album', year=1996, filename='song3.mp3')
        self.run_add()
        self.assertEqual(Artist.objects.count(), 4)

        artists = [
            Artist.objects.get(name='Artist 1'),
            Artist.objects.get(name='Artist 2'),
            Artist.objects.get(name='Artist 3'),
        ]

        response = self.client.get(reverse('exordium:search'), {'q': 'artist'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['artist_results'].data), 3)
        self.assertQuerysetEqual(response.context['artist_results'].data, [repr(ar) for ar in artists])
        self.assertContains(response, 'artist-sort=-name')
        self.assertContains(response, '3 artists')

        # test the sorting button
        response = self.client.get(reverse('exordium:search'), {'q': 'artist', 'artist-sort': '-name'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['artist_results'].data), 3)
        self.assertQuerysetEqual(response.context['artist_results'].data, [repr(ar) for ar in reversed(artists)])
        self.assertContains(response, 'artist-sort=name')
        self.assertContains(response, '3 artists')

    def test_sorting_album(self):
        """
        Test at least one case of album sorting.
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album 1', year=2016, filename='song1.mp3')
        self.add_mp3(artist='Artist', title='Title 2',
            album='Album 2', year=2006, filename='song2.mp3')
        self.add_mp3(artist='Artist', title='Title 3',
            album='Album 3', year=1996, filename='song3.mp3')
        self.run_add()
        self.assertEqual(Album.objects.count(), 3)

        albums = [
            Album.objects.get(name='Album 1'),
            Album.objects.get(name='Album 2'),
            Album.objects.get(name='Album 3'),
        ]

        response = self.client.get(reverse('exordium:search'), {'q': 'album'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['album_results'].data), 3)
        self.assertQuerysetEqual(response.context['album_results'].data, [repr(al) for al in albums])
        self.assertContains(response, 'album-sort=year')
        self.assertContains(response, '3 albums')

        # test the sorting button
        response = self.client.get(reverse('exordium:search'), {'q': 'album', 'album-sort': 'year'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['album_results'].data), 3)
        self.assertQuerysetEqual(response.context['album_results'].data, [repr(al) for al in reversed(albums)])
        self.assertContains(response, 'album-sort=-year')
        self.assertContains(response, '3 albums')

    def test_sorting_album_year_time_added(self):
        """
        Test album sorting by year when two albums are in the same year; should
        use time_added as the secondary sorting field.
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album 1', year=2017, filename='song1.mp3')
        self.add_mp3(artist='Artist', title='Title 2',
            album='Album 2', year=2017, filename='song2.mp3')
        self.run_add()
        al2 = self.age_album('Artist', 'Album 2', 10)
        self.assertEqual(Album.objects.count(), 2)

        albums = [
            al2,
            Album.objects.get(name='Album 1'),
        ]

        response = self.client.get(reverse('exordium:search'), {'q': 'album', 'album-sort': 'year'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['album_results'].data), 2)
        self.assertQuerysetEqual(response.context['album_results'].data, [repr(al) for al in albums])
        self.assertContains(response, 'album-sort=-year')
        self.assertContains(response, '2 albums')

        # test reverse sort
        response = self.client.get(reverse('exordium:search'), {'q': 'album', 'album-sort': '-year'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['album_results'].data), 2)
        self.assertQuerysetEqual(response.context['album_results'].data, [repr(al) for al in reversed(albums)])
        self.assertContains(response, 'album-sort=year')
        self.assertContains(response, '2 albums')

    def test_sorting_song(self):
        """
        Test at least one case of song sorting.  Default sorting is by track name
        """
        self.add_mp3(artist='Artist', title='Title 1', tracknum=1,
            album='Album 3', filename='song1.mp3')
        self.add_mp3(artist='Artist', title='Title 2', tracknum=2,
            album='Album 2', filename='song2.mp3')
        self.add_mp3(artist='Artist', title='Title 3', tracknum=3,
            album='Album 1', filename='song3.mp3')
        self.run_add()

        songs = [
            Song.objects.get(filename='song1.mp3'),
            Song.objects.get(filename='song2.mp3'),
            Song.objects.get(filename='song3.mp3'),
        ]

        response = self.client.get(reverse('exordium:search'), {'q': 'title'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['song_results'].data), 3)
        self.assertQuerysetEqual(response.context['song_results'].data, [repr(song) for song in songs])
        self.assertContains(response, 'song-sort=album')
        self.assertContains(response, '3 songs')

        # test the sorting button
        response = self.client.get(reverse('exordium:search'), {'q': 'title', 'song-sort': 'album'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['song_results'].data), 3)
        self.assertQuerysetEqual(response.context['song_results'].data, [repr(song) for song in reversed(songs)])
        self.assertContains(response, 'song-sort=-album')
        self.assertContains(response, '3 songs')

