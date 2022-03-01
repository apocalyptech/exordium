from .base import ExordiumTests

from django.urls import reverse

from exordium.models import Artist, Album, Song, App, AlbumArt

class BrowseArtistViewTests(ExordiumTests):
    """
    Tests of our Browse Artists page
    """

    def test_no_artists(self):
        """
        Test the view when there are no artists (except for Various)
        """
        various = Artist.objects.get()

        response = self.client.get(reverse('exordium:browse_artist'))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['table'].data, [repr(various)])
        self.assertContains(response, '1 artist')
        self.assertContains(response, reverse('exordium:artist', args=(various.normname,)))

    def test_one_artists(self):
        """
        Test the view when there is one artist (and Various)
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album 1', filename='song1.mp3')
        self.run_add()

        various = Artist.objects.get(normname='various')
        artist = Artist.objects.get(normname='artist')

        response = self.client.get(reverse('exordium:browse_artist'))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['table'].data, [repr(artist), repr(various)])
        self.assertContains(response, '2 artists')
        for a in [various, artist]:
            self.assertContains(response, reverse('exordium:artist', args=(a.normname,)))

    def test_ten_artists(self):
        """
        Test the view when there are a bunch of artists
        """
        artists = ['Adipiscing',
            'Amet',
            'Congue',
            'Consectetur',
            'Dolor',
            'Elit',
            'Ipsum',
            'Lorem',
            'Sit',
            'Vivamus',
        ]
        for (idx, artist) in enumerate(artists):
            self.add_mp3(artist=artist, title='Title %d' % (idx+1),
                album='Album', filename='song%d.mp3' % (idx+1))
        self.run_add()

        # add Various to our list, in the properly-sorted place.
        artists.insert(9, 'Various')
        artist_objs = []
        for artist in artists:
            artist_objs.append(Artist.objects.get(name=artist))

        response = self.client.get(reverse('exordium:browse_artist'))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['table'].data,
            [repr(artist) for artist in artist_objs])
        self.assertContains(response, '11 artists')
        for artist in artist_objs:
            self.assertContains(response, reverse('exordium:artist',
                args=(artist.normname,)))

    def test_classical_song(self):
        """
        Test the view when a single song created multiple artists
        """
        self.add_mp3(artist='Artist', group='Group',
            conductor='Conductor', composer='Composer',
            title='Title', album='Album', filename='song1.mp3')
        self.run_add()

        self.assertEqual(Artist.objects.count(), 5)
        artists = [
            Artist.objects.get(name='Artist'),
            Artist.objects.get(name='Composer'),
            Artist.objects.get(name='Conductor'),
            Artist.objects.get(name='Group'),
            Artist.objects.get(name='Various'),
        ]

        response = self.client.get(reverse('exordium:browse_artist'))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['table'].data,
            [repr(artist) for artist in artists])
        self.assertContains(response, '5 artists')
        for artist in artists:
            self.assertContains(response, str(artist))
            self.assertContains(response, reverse('exordium:artist',
                args=(artist.normname,)))

    def test_pagination(self):
        """
        Test to make sure that our pagination is working properly.
        The Browse Artists page will show a total of 25 artists
        """
        for num in range(30):
            self.add_mp3(artist='Artist %02d' % (num+1), title='Title %d' % (num+1),
                album='Album %d' % (num+1), filename='song%d.mp3' % (num+1))
        self.run_add()
        self.assertEqual(Artist.objects.count(), 31)

        artists = {}
        for num in range(30):
            artists[num] = Artist.objects.get(name='Artist %02d' % (num+1))

        response = self.client.get(reverse('exordium:browse_artist'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['table'].data), 31)
        for num in range(25):
            self.assertContains(response, '%s<' % (artists[num]))
            self.assertContains(response, reverse('exordium:artist', args=(artists[num].normname,)))
        for num in range(25, 30):
            self.assertNotContains(response, '%s<' % (artists[num]))
            self.assertNotContains(response, reverse('exordium:artist', args=(artists[num].normname,)))
        self.assertNotContains(response, 'Various<')
        self.assertContains(response, '25 of 31 artists')
        self.assertContains(response, '"?page=2"')

        # test page 2
        response = self.client.get(reverse('exordium:browse_artist'), {'page': 2})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['table'].data), 31)
        for num in range(25):
            self.assertNotContains(response, '%s<' % (artists[num]))
            self.assertNotContains(response, reverse('exordium:artist', args=(artists[num].normname,)))
        for num in range(25, 30):
            self.assertContains(response, '%s<' % (artists[num]))
            self.assertContains(response, reverse('exordium:artist', args=(artists[num].normname,)))
        self.assertContains(response, 'Various<')
        self.assertContains(response, '6 of 31 artists')
        self.assertContains(response, '"?page=1"')

    def test_sorting(self):
        """
        Test at least one sort
        """
        self.add_mp3(artist='A Artist', title='Title 1',
            album='Album 1', filename='song1.mp3')
        self.add_mp3(artist='B Artist', title='Title 2',
            album='Album 2', filename='song2.mp3')
        self.run_add()

        various = Artist.objects.get(normname='various')
        artist_a = Artist.objects.get(normname='a artist')
        artist_b = Artist.objects.get(normname='b artist')

        # Initial view, artist name.
        response = self.client.get(reverse('exordium:browse_artist'))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['table'].data,
            [repr(artist_a), repr(artist_b), repr(various)])
        self.assertContains(response, "?sort=-name")

        # Now sort by name descending
        response = self.client.get(reverse('exordium:browse_artist'), {'sort': '-name'})
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['table'].data,
            [repr(various), repr(artist_b), repr(artist_a)])
        self.assertContains(response, "?sort=name")

