from .base import ExordiumUserTests

from django.urls import reverse
from django.db.models import Q

from django.templatetags.static import static

from exordium.models import Artist, Album, Song, App, AlbumArt

class IndexViewTests(ExordiumUserTests):
    """
    Tests of our main index view.  (Not a whole lot going on, really)
    """

    def test_no_albums(self):
        """
        Test what happens if there are no albums defined.  (No albums should
        be found in the view's context.)  This test also tests for the various
        links which are supposed to be present on the main page.
        """
        response = self.client.get(reverse('exordium:index'))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['album_list'].data, [])

        self.assertContains(response, 'AnonymousUser')
        self.assertContains(response, reverse('exordium:browse_artist'))
        self.assertContains(response, reverse('exordium:browse_album'))
        self.assertContains(response, reverse('exordium:updateprefs'))

        # We are not authenticated, so we should NOT see any of the admin
        # links anywhere.
        self.assertNotContains(response, reverse('exordium:library'))
        self.assertNotContains(response, reverse('admin:dynamic_preferences_globalpreferencemodel_changelist'))
        self.assertNotContains(response, '%s"' % (reverse('admin:index')))

        # But we SHOULD see a login link
        self.assertContains(response, reverse('admin:login'))

    def test_no_albums_admin(self):
        """
        Test what happens if there are no albums defined.  (No albums should
        be found in the view's context.)  This test also tests for the various
        links which are supposed to be present on the main page.  This time,
        request as if we're an admin.
        """
        self.login()
        response = self.client.get(reverse('exordium:index'))
        self.assertContains(response, 'mainuser')
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['album_list'].data, [])

        self.assertContains(response, 'mainuser')
        self.assertContains(response, reverse('exordium:browse_artist'))
        self.assertContains(response, reverse('exordium:browse_album'))
        self.assertContains(response, reverse('exordium:updateprefs'))

        # We are authenticated, so we should see the admin links.
        self.assertContains(response, reverse('exordium:library'))
        self.assertContains(response, reverse('admin:dynamic_preferences_globalpreferencemodel_changelist'))
        self.assertContains(response, reverse('admin:index'))

        # But we should NOT see a login link
        self.assertNotContains(response, reverse('admin:login'))

    def test_single_album(self):
        """
        Test what happens when there's a single album.  We should see that
        album!
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Test Album', filename='song1.mp3')
        self.run_add()
        self.assertEqual(Album.objects.count(), 1)
        album = Album.objects.get()

        response = self.client.get(reverse('exordium:index'))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['album_list'].data, [repr(album)])
        self.assertContains(response, 'Test Album')
        self.assertContains(response, reverse('exordium:album', args=(album.pk,)))
        self.assertContains(response, reverse('exordium:artist', args=(album.artist.normname,)))
        self.assertContains(response, '1 album')

        # May as well verify that we're seeing the no-album-art cover, as well
        self.assertContains(response, '"%s"' % (static('exordium/no_album_art_small.png')))

    def test_album_art(self):
        """
        Make sure that an album with album art has its art showing in the table.
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Test Album', filename='song1.mp3')
        self.add_art()
        self.run_add()
        self.assertEqual(Album.objects.count(), 1)
        album = Album.objects.get()

        response = self.client.get(reverse('exordium:index'))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['album_list'].data, [repr(album)])
        self.assertContains(response, 'Test Album')
        self.assertContains(response, reverse('exordium:album', args=(album.pk,)))
        self.assertContains(response, reverse('exordium:artist', args=(album.artist.normname,)))
        self.assertContains(response, reverse('exordium:albumart', args=(album.pk, 'list',)))

    def test_four_albums(self):
        """
        Test what happens when there's four albums.  Ensure that they are
        sorted properly.
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album 1', filename='song1.mp3')
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album 2', filename='song2.mp3')
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album 3', filename='song3.mp3')
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album 4', filename='song4.mp3')
        self.run_add()
        album_2 = self.age_album('Artist', 'Album 2', 2)
        album_3 = self.age_album('Artist', 'Album 3', 4)
        album_4 = self.age_album('Artist', 'Album 4', 6)
        self.assertEqual(Album.objects.count(), 4)
        album_1 = Album.objects.get(name='Album 1')

        response = self.client.get(reverse('exordium:index'))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['album_list'].data,
            [repr(al) for al in [album_1, album_2, album_3, album_4]])
        self.assertContains(response, 'Album 1')
        self.assertContains(response, 'Album 2')
        self.assertContains(response, 'Album 3')
        self.assertContains(response, 'Album 4')
        self.assertContains(response, '4 albums')

    def test_classical_album(self):
        """
        Test the display of an album with classical tags
        """
        self.add_mp3(artist='Artist', title='Title 1',
            group='Group', conductor='Conductor', composer='Composer',
            album='Album 1', filename='song1.mp3')
        self.run_add()

        self.assertEqual(Artist.objects.count(), 5)
        self.assertEqual(Album.objects.count(), 1)

        album = Album.objects.get()
        artists = []

        response = self.client.get(reverse('exordium:index'))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['album_list'].data, [repr(album)])
        self.assertContains(response, 'Album 1')
        self.assertContains(response, reverse('exordium:album', args=(album.pk,)))
        self.assertContains(response, reverse('exordium:artist', args=(album.artist.normname,)))
        for artist in Artist.objects.exclude(name='Various'):
            self.assertContains(response, str(artist))
            self.assertContains(response, reverse('exordium:artist', args=(artist.normname,)))

    def test_classical_album_two_tracks(self):
        """
        Test the display of an album with classical tags.  Two tracks, where
        the artist stays the same but the other classical tags differ.
        """
        self.add_mp3(artist='Artist', title='Title 1',
            group='Group', conductor='Conductor', composer='Composer',
            album='Album 1', filename='song1.mp3')
        self.add_mp3(artist='Artist', title='Title 2',
            group='Group 2', conductor='Conductor 2', composer='Composer 2',
            album='Album 1', filename='song2.mp3')
        self.run_add()

        self.assertEqual(Artist.objects.count(), 8)
        self.assertEqual(Album.objects.count(), 1)

        album = Album.objects.get()
        artists = []

        response = self.client.get(reverse('exordium:index'))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['album_list'].data, [repr(album)])
        self.assertContains(response, 'Album 1')
        self.assertContains(response, reverse('exordium:album', args=(album.pk,)))
        self.assertContains(response, reverse('exordium:artist', args=(album.artist.normname,)))
        for artist in Artist.objects.exclude(name='Various'):
            self.assertContains(response, str(artist))
            self.assertContains(response, reverse('exordium:artist', args=(artist.normname,)))

    def test_various_album(self):
        """
        Test display of a Various Artists album
        """
        self.add_mp3(artist='Artist 1', title='Title 1',
            album='Album', filename='song1.mp3')
        self.add_mp3(artist='Artist 2', title='Title 2',
            album='Album', filename='song2.mp3')
        self.run_add()

        self.assertEqual(Artist.objects.count(), 3)
        self.assertEqual(Album.objects.count(), 1)
        artist_1 = Artist.objects.get(name='Artist 1')
        artist_2 = Artist.objects.get(name='Artist 2')
        various = Artist.objects.get(name='Various')
        album = Album.objects.get()

        response = self.client.get(reverse('exordium:index'))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['album_list'].data, [repr(album)])
        self.assertContains(response, 'Album')
        self.assertContains(response, reverse('exordium:album', args=(album.pk,)))
        self.assertContains(response, reverse('exordium:artist', args=(album.artist.normname,)))
        self.assertContains(response, reverse('exordium:artist', args=(various.normname,)))
        for artist in [artist_1, artist_2]:
            self.assertNotContains(response, str(artist_1))
            self.assertNotContains(response, reverse('exordium:artist', args=(artist.normname,)))

    def test_classical_album_two_tracks_various(self):
        """
        Test the display of an album with classical tags.  Two tracks, where
        all artist fields change, so it's a Various Artists album.
        """
        self.add_mp3(artist='Artist 1', title='Title 1',
            group='Group', conductor='Conductor', composer='Composer',
            album='Album 1', filename='song1.mp3')
        self.add_mp3(artist='Artist 2', title='Title 2',
            group='Group 2', conductor='Conductor 2', composer='Composer 2',
            album='Album 1', filename='song2.mp3')
        self.run_add()

        self.assertEqual(Artist.objects.count(), 9)
        self.assertEqual(Album.objects.count(), 1)

        album = Album.objects.get()
        artists = []

        various = Artist.objects.get(name='Various')

        response = self.client.get(reverse('exordium:index'))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['album_list'].data, [repr(album)])
        self.assertContains(response, 'Album 1')
        self.assertContains(response, reverse('exordium:album', args=(album.pk,)))
        self.assertContains(response, reverse('exordium:artist', args=(album.artist.normname,)))
        self.assertContains(response, reverse('exordium:artist', args=(various.normname,)))
        for artist in Artist.objects.exclude(Q(name='Artist 1') | Q(name='Artist 2')):
            self.assertContains(response, str(artist))
            self.assertContains(response, reverse('exordium:artist', args=(artist.normname,)))
        for artist in Artist.objects.filter(Q(name='Artist 1') | Q(name='Artist 2')):
            self.assertNotContains(response, str(artist))
            self.assertNotContains(response, reverse('exordium:artist', args=(artist.normname,)))

    def test_pagination(self):
        """
        Test to make sure that our pagination is working properly.
        The index page will show a total of 20 albums
        """
        for num in range(30):
            self.add_mp3(artist='Artist', title='Title %d' % (num+1),
                album='Album %d' % (num+1), filename='song%d.mp3' % (num+1))
        self.run_add()
        self.assertEqual(Album.objects.count(), 30)

        albums = {}
        for num in range(30):
            self.age_album(artist='Artist',
                album='Album %d' % (num+1),
                age_days=num+1)
            albums[num] = Album.objects.get(name='Album %d' % (num+1))

        response = self.client.get(reverse('exordium:index'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['album_list'].data), 30)
        for num in range(20):
            self.assertContains(response, '%s<' % (albums[num]))
            self.assertContains(response, reverse('exordium:album', args=(albums[num].pk,)))
        for num in range(20, 30):
            self.assertNotContains(response, '%s<' % (albums[num]))
            self.assertNotContains(response, reverse('exordium:album', args=(albums[num].pk,)))
        self.assertContains(response, '20 of 30 albums')
        self.assertContains(response, '"?page=2"')

        # test page 2
        response = self.client.get(reverse('exordium:index'), {'page': 2})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['album_list'].data), 30)
        for num in range(20):
            self.assertNotContains(response, '%s<' % (albums[num]))
            self.assertNotContains(response, reverse('exordium:album', args=(albums[num].pk,)))
        for num in range(20, 30):
            self.assertContains(response, '%s<' % (albums[num]))
            self.assertContains(response, reverse('exordium:album', args=(albums[num].pk,)))
        self.assertContains(response, '10 of 30 albums')
        self.assertContains(response, '"?page=1"')

    def test_sorting(self):
        """
        Test for at least one sorting link
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album 1', filename='song1.mp3', year=2016)
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album 2', filename='song2.mp3', year=2006)
        self.run_add()

        self.assertEqual(Album.objects.count(), 2)
        album_2 = self.age_album('Artist', 'Album 2', 2)
        album_1 = Album.objects.get(name='Album 1')

        # Initial view, should be sorted by addition time
        response = self.client.get(reverse('exordium:index'))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['album_list'].data,
            [repr(al) for al in [album_1, album_2]])
        self.assertContains(response, 'Album 1')
        self.assertContains(response, 'Album 2')
        self.assertContains(response, '"?sort=year"')

        # Now sort by year
        response = self.client.get(reverse('exordium:index'), {'sort': 'year'})
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['album_list'].data,
            [repr(al) for al in [album_2, album_1]])
        self.assertContains(response, 'Album 1')
        self.assertContains(response, 'Album 2')
        self.assertContains(response, '"?sort=-year"')

