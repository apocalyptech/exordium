from .base import ExordiumTests

from django.urls import reverse
from django.db.models import Q

from django.templatetags.static import static

from exordium.models import Artist, Album, Song, App, AlbumArt

class BrowseAlbumViewTests(ExordiumTests):
    """
    Tests of our Browse Album page
    """

    def test_no_albums(self):
        """
        Test the view when there are no albums
        """
        response = self.client.get(reverse('exordium:browse_album'))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['table'].data, [])

    def test_one_album(self):
        """
        Test the view when there is one album
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3')
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        album = Album.objects.get()

        response = self.client.get(reverse('exordium:browse_album'))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['table'].data, [repr(album)])
        self.assertContains(response, '1 album')
        self.assertContains(response, reverse('exordium:album', args=(album.pk,)))
        self.assertContains(response, reverse('exordium:artist', args=(album.artist.normname,)))
        self.assertContains(response, '"%s"' % (static('exordium/no_album_art_small.png')))

    def test_one_album_with_art(self):
        """
        Test the view when there is one album, with album art
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3')
        self.add_art()
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        album = Album.objects.get()

        response = self.client.get(reverse('exordium:browse_album'))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['table'].data, [repr(album)])
        self.assertContains(response, '1 album')
        self.assertContains(response, reverse('exordium:album', args=(album.pk,)))
        self.assertContains(response, reverse('exordium:artist', args=(album.artist.normname,)))
        self.assertContains(response, reverse('exordium:albumart', args=(album.pk, 'list',)))

    def test_ordering_three_regular_albums(self):
        """
        Test ordering with three "regular" albums.  Should be alphabetical by
        album name.
        """
        self.add_mp3(artist='Zebra', title='Title 1',
            album='Z Album', filename='song1.mp3')
        self.add_mp3(artist='Artist', title='Title 1',
            album='R Album', filename='song2.mp3')
        self.add_mp3(artist='Zebra', title='Title 1',
            album='Album', filename='song3.mp3')
        self.run_add()

        self.assertEqual(Album.objects.count(), 3)
        albums = [
            Album.objects.get(normname='album'),
            Album.objects.get(normname='r album'),
            Album.objects.get(normname='z album'),
        ]

        response = self.client.get(reverse('exordium:browse_album'))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['table'].data, [repr(al) for al in albums])
        self.assertContains(response, '3 albums')
        for al in albums:
            self.assertContains(response, reverse('exordium:album', args=(al.pk,)))
            self.assertContains(response, reverse('exordium:artist', args=(al.artist.normname,)))

    def test_ordering_miscellaneous_albums(self):
        """
        By default, "miscellaneous" (non-album) albums should come at
        the end of the list.
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Z Album', filename='song1.mp3')
        self.add_mp3(artist='Artist', title='Title 2',
            album='S Album', filename='song2.mp3')
        self.add_mp3(artist='Artist', title='Title 3',
            filename='song3.mp3')
        self.add_mp3(artist='Zebra', title='Title 4',
            album='C Album', filename='song4.mp3')
        self.add_mp3(artist='Zebra', title='Title 5',
            album='V Album', filename='song5.mp3')
        self.add_mp3(artist='Zebra', title='Title 6',
            filename='song6.mp3')
        self.add_mp3(artist='Yellow', title='Title 7',
            filename='song7.mp3')
        self.run_add()

        self.assertEqual(Album.objects.count(), 7)
        albums = []
        for albumname in [
                'C Album',
                'S Album',
                'V Album',
                'Z Album',
                Album.miscellaneous_format_str % ('Artist'),
                Album.miscellaneous_format_str % ('Yellow'),
                Album.miscellaneous_format_str % ('Zebra'),
                ]:
            albums.append(Album.objects.get(name=albumname))

        response = self.client.get(reverse('exordium:browse_album'))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['table'].data, [repr(al) for al in albums])
        self.assertContains(response, '7 albums')
        for al in albums:
            self.assertContains(response, reverse('exordium:album', args=(al.pk,)))
            self.assertContains(response, reverse('exordium:artist', args=(al.artist.normname,)))

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

        response = self.client.get(reverse('exordium:browse_album'))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['table'].data, [repr(album)])
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

        response = self.client.get(reverse('exordium:browse_album'))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['table'].data, [repr(album)])
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

        response = self.client.get(reverse('exordium:browse_album'))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['table'].data, [repr(album)])
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

        response = self.client.get(reverse('exordium:browse_album'))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['table'].data, [repr(album)])
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
        The album browse page will show a total of 50 albums
        """
        for num in range(60):
            self.add_mp3(artist='Artist', title='Title %d' % (num+1),
                album='Album %02d' % (num+1), filename='song%d.mp3' % (num+1))
        self.run_add()
        self.assertEqual(Album.objects.count(), 60)

        albums = {}
        for num in range(60):
            albums[num] = Album.objects.get(name='Album %02d' % (num+1))

        response = self.client.get(reverse('exordium:browse_album'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['table'].data), 60)
        for num in range(50):
            self.assertContains(response, '%s<' % (albums[num]))
            self.assertContains(response, reverse('exordium:album', args=(albums[num].pk,)))
        for num in range(50, 60):
            self.assertNotContains(response, '%s<' % (albums[num]))
            self.assertNotContains(response, reverse('exordium:album', args=(albums[num].pk,)))
        self.assertContains(response, '50 of 60 albums')
        self.assertContains(response, '"?page=2"')

        # test page 2
        response = self.client.get(reverse('exordium:browse_album'), {'page': 2})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['table'].data), 60)
        for num in range(50):
            self.assertNotContains(response, '%s<' % (albums[num]))
            self.assertNotContains(response, reverse('exordium:album', args=(albums[num].pk,)))
        for num in range(50, 60):
            self.assertContains(response, '%s<' % (albums[num]))
            self.assertContains(response, reverse('exordium:album', args=(albums[num].pk,)))
        self.assertContains(response, '10 of 60 albums')
        self.assertContains(response, '"?page=1"')

    def test_sorting(self):
        """
        Test at least one case of sorting.
        """
        self.add_mp3(artist='Zed', title='Title 1',
            album='Album 1', filename='song1.mp3')
        self.add_mp3(artist='Gee', title='Title 2',
            album='Album 2', filename='song2.mp3')
        self.add_mp3(artist='Artist', title='Title 3',
            album='Album 3', filename='song3.mp3')
        self.run_add()
        self.assertEqual(Album.objects.count(), 3)

        albums = [
            Album.objects.get(name='Album 1'),
            Album.objects.get(name='Album 2'),
            Album.objects.get(name='Album 3'),
        ]
        response = self.client.get(reverse('exordium:browse_album'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['table'].data), 3)
        self.assertQuerysetEqual(response.context['table'].data, [repr(al) for al in albums])
        self.assertContains(response, '"?sort=artist"')

        # test the sorting button
        response = self.client.get(reverse('exordium:browse_album'), {'sort': 'artist'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['table'].data), 3)
        self.assertQuerysetEqual(response.context['table'].data, [repr(al) for al in reversed(albums)])
        self.assertContains(response, '"?sort=-artist"')

