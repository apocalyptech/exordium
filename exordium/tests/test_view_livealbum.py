from .base import ExordiumUserTests

from django.urls import reverse

from exordium.models import Artist, Album, Song, App, AlbumArt

class LiveAlbumViewTestsAnonymous(ExordiumUserTests):
    """
    Tests of our live album viewing functionality.  They can be either
    hidden or shown based on user preference, so there'll basically just
    be one test in here per view where this preference applies.
    """

    def set_show_live(self, show_live=True):
        """
        Sets our ``show_live`` preference as specified, by submitting our
        user preference form.  (That way we don't need a request object.)
        """
        if show_live:
            post_data = {'show_live': 'yes'}
        else:
            post_data = {}
        self.client.post(reverse('exordium:updateprefs'), post_data)

    def test_index(self):
        """
        Tests our index page display
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='2016.01.01 - Live at City Name', filename='song1.mp3')
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        album = Album.objects.get()
        self.assertEqual(album.live, True)

        # Default is off
        response = self.client.get(reverse('exordium:index'))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['album_list'].data, [])
        self.assertNotContains(response, reverse('exordium:album', args=(album.pk,)))
        self.assertNotContains(response, reverse('exordium:artist', args=(album.artist.normname,)))

        # Now flip it on
        self.set_show_live()
        response = self.client.get(reverse('exordium:index'))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['album_list'].data, [repr(album)])
        self.assertContains(response, reverse('exordium:album', args=(album.pk,)))
        self.assertContains(response, reverse('exordium:artist', args=(album.artist.normname,)))
        self.assertContains(response, '1 album')

    def test_album_browse(self):
        """
        Tests our Browse Album page
        """

        self.add_mp3(artist='Artist', title='Title 1',
            album='2016.01.01 - Live at City Name', filename='song1.mp3')
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        album = Album.objects.get()
        self.assertEqual(album.live, True)

        # Default is off
        response = self.client.get(reverse('exordium:browse_album'))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['table'].data, [])
        self.assertNotContains(response, reverse('exordium:album', args=(album.pk,)))
        self.assertNotContains(response, reverse('exordium:artist', args=(album.artist.normname,)))

        # Now flip it on
        self.set_show_live()
        response = self.client.get(reverse('exordium:browse_album'))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['table'].data, [repr(album)])
        self.assertContains(response, reverse('exordium:album', args=(album.pk,)))
        self.assertContains(response, reverse('exordium:artist', args=(album.artist.normname,)))
        self.assertContains(response, '1 album')

    def test_artist(self):
        """
        Tests our Artist info page
        """

        self.add_mp3(artist='Artist', title='Title 1',
            album='2016.01.01 - Live at City Name', filename='song1.mp3')
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        album = Album.objects.get()
        self.assertEqual(album.live, True)

        self.assertEqual(Artist.objects.count(), 2)
        artist = Artist.objects.get(name='Artist')

        self.assertEqual(Song.objects.count(), 1)
        song = Song.objects.get()

        # Default is off
        response = self.client.get(reverse('exordium:artist', args=(artist.normname,)))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['have_songs'], True)
        self.assertQuerysetEqual(response.context['albums'].data, [])
        self.assertQuerysetEqual(response.context['songs'].data, [])
        self.assertNotContains(response, reverse('exordium:album', args=(album.pk,)))
        self.assertNotContains(response, '"%s"' % (reverse('exordium:artist', args=(album.artist.normname,))))

        # Now flip it on
        self.set_show_live()
        response = self.client.get(reverse('exordium:artist', args=(artist.normname,)))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['have_songs'], True)
        self.assertQuerysetEqual(response.context['albums'].data, [repr(album)])
        self.assertQuerysetEqual(response.context['songs'].data, [repr(song)])
        self.assertContains(response, reverse('exordium:album', args=(album.pk,)))
        self.assertContains(response, '"%s"' % (reverse('exordium:artist', args=(album.artist.normname,))))
        self.assertContains(response, '1 album')
        self.assertContains(response, '1 song')

    def test_search_album(self):
        """
        Tests our search page, searching for albums
        """

        self.add_mp3(artist='Artist', title='Title 1',
            album='2016.01.01 - Live at City Name', filename='song1.mp3')
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        album = Album.objects.get()
        self.assertEqual(album.live, True)

        self.assertEqual(Artist.objects.count(), 2)
        artist = Artist.objects.get(name='Artist')

        self.assertEqual(Song.objects.count(), 1)
        song = Song.objects.get()

        # Default is off
        response = self.client.get(reverse('exordium:search'), {'q': 'city name'})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('length_error', response.context)
        self.assertNotIn('song_results', response.context)
        self.assertNotIn('album_results', response.context)
        self.assertNotIn('artist_results', response.context)
        self.assertIn('found_results', response.context)
        self.assertEqual(response.context['found_results'], False)
        self.assertContains(response, 'No results found!')
        self.assertNotContains(response, reverse('exordium:album', args=(album.pk,)))
        self.assertNotContains(response, reverse('exordium:artist', args=(artist.normname,)))

        # Now flip it on
        self.set_show_live()
        response = self.client.get(reverse('exordium:search'), {'q': 'city name'})
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

    def test_search_song(self):
        """
        Tests our search page, searching for songs
        """

        self.add_mp3(artist='Artist', title='Title 1',
            album='2016.01.01 - Live at City Name', filename='song1.mp3')
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        album = Album.objects.get()
        self.assertEqual(album.live, True)

        self.assertEqual(Artist.objects.count(), 2)
        artist = Artist.objects.get(name='Artist')

        self.assertEqual(Song.objects.count(), 1)
        song = Song.objects.get()

        # Default is off
        response = self.client.get(reverse('exordium:search'), {'q': 'title'})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('length_error', response.context)
        self.assertNotIn('song_results', response.context)
        self.assertNotIn('album_results', response.context)
        self.assertNotIn('artist_results', response.context)
        self.assertIn('found_results', response.context)
        self.assertEqual(response.context['found_results'], False)
        self.assertContains(response, 'No results found!')
        self.assertNotContains(response, reverse('exordium:album', args=(album.pk,)))
        self.assertNotContains(response, reverse('exordium:artist', args=(artist.normname,)))
        self.assertNotContains(response, song.title)

        # Now flip it on
        self.set_show_live()
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

class LiveAlbumViewTestsUser(LiveAlbumViewTestsAnonymous):
    """
    Some nonsense along the lines of BasicAddAsUpdateTests.  Basically,
    all of our tests in LiveAlbumViewTestsAnonymous should work just
    as well if the user is logged in as when the user is anonymous.  So,
    we have a custom setUp() function here which will do that prior to
    every test.
    """

    def setUp(self):
        super(LiveAlbumViewTestsUser, self).setUp()
        self.login()

    def tearDown(self):
        """
        Ensure that we revert back to the default of not showing live
        albums inbetween tests - this won't automatically happen for
        logged-in users because changes to the user database persists.
        """
        super(LiveAlbumViewTestsUser, self).tearDown()
        self.set_show_live(False)

