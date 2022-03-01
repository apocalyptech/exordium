from .base import ExordiumTests

from django.urls import reverse

from django.templatetags.static import static

from exordium.models import Artist, Album, Song, App, AlbumArt

class ArtistViewTests(ExordiumTests):
    """
    Tests of our Artist info page
    """

    def test_invalid_artist(self):
        """
        Tests making a request for an artist which can't be found.
        """
        response = self.client.get(reverse('exordium:artist', args=('notfound',)))
        self.assertEqual(response.status_code, 404)

    def test_single_album(self):
        """
        Test an artist who only has a single album
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3')
        self.run_add()
        
        self.assertEqual(Artist.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Song.objects.count(), 1)

        artist = Artist.objects.get(name='Artist')
        album = Album.objects.get()
        song = Song.objects.get()

        response = self.client.get(reverse('exordium:artist', args=('artist',)))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['albums'].data, [repr(album)])
        self.assertEqual(response.context['have_songs'], True)
        self.assertQuerysetEqual(response.context['songs'].data, [repr(song)])
        self.assertContains(response, 'Songs by %s' % (artist))
        self.assertContains(response, reverse('exordium:artist', args=(artist.normname,)))
        self.assertContains(response, reverse('exordium:album', args=(album.pk,)))
        self.assertContains(response, song.get_download_url_html5())
        self.assertContains(response, song.get_download_url_m3u())
        self.assertContains(response, '1 album')
        self.assertContains(response, '1 song')

        # May as well double-check the no-album-art-found image as well
        self.assertContains(response, '"%s"' % (static('exordium/no_album_art_small.png')))

        # Artist song-list view should not have the tracknum column, and should have album-sort
        self.assertNotContains(response, 'sort=tracknum')
        self.assertContains(response, 'song-sort=album')

    def test_single_album_with_art(self):
        """
        Test an artist who only has a single album, with album art.
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3')
        self.add_art()
        self.run_add()
        
        self.assertEqual(Artist.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Song.objects.count(), 1)

        artist = Artist.objects.get(name='Artist')
        album = Album.objects.get()
        song = Song.objects.get()

        response = self.client.get(reverse('exordium:artist', args=('artist',)))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['albums'].data, [repr(album)])
        self.assertEqual(response.context['have_songs'], True)
        self.assertQuerysetEqual(response.context['songs'].data, [repr(song)])
        self.assertContains(response, '1 album')
        self.assertContains(response, '1 song')
        self.assertContains(response, 'Songs by %s' % (artist))
        self.assertContains(response, reverse('exordium:artist', args=(artist.normname,)))
        self.assertContains(response, reverse('exordium:album', args=(album.pk,)))
        self.assertContains(response, reverse('exordium:albumart', args=(album.pk, 'list',)))
        # These will show up once for HTML5, and once for direct download
        self.assertContains(response, song.get_download_url_html5())
        self.assertContains(response, song.get_download_url_m3u())
        self.assertNotContains(response, 'sort=tracknum')
        self.assertContains(response, 'song-sort=album')

    def test_various_artists(self):
        """
        Test a various artist album - the one containing the artist
        we care about should show up in the list
        """
        self.add_mp3(artist='Artist 1', title='Title 1',
            album='Album 1', filename='song1.mp3', path='album_1')
        self.add_mp3(artist='Artist 2', title='Title 2',
            album='Album 1', filename='song2.mp3', path='album_1')
        self.add_mp3(artist='Artist 2', title='Title 3',
            album='Album 2', filename='song3.mp3', path='album_2')
        self.add_mp3(artist='Artist 3', title='Title 4',
            album='Album 2', filename='song4.mp3', path='album_2')
        self.run_add()

        self.assertEqual(Artist.objects.count(), 4)
        self.assertEqual(Album.objects.count(), 2)
        self.assertEqual(Song.objects.count(), 4)

        artist_1 = Artist.objects.get(name='Artist 1')
        artist_2 = Artist.objects.get(name='Artist 2')
        artist_3 = Artist.objects.get(name='Artist 3')
        various = Artist.objects.get(name='Various')

        album_1 = Album.objects.get(name='Album 1')
        album_2 = Album.objects.get(name='Album 2')

        song_1 = Song.objects.get(filename='album_1/song1.mp3')
        song_2 = Song.objects.get(filename='album_1/song2.mp3')
        song_3 = Song.objects.get(filename='album_2/song3.mp3')
        song_4 = Song.objects.get(filename='album_2/song4.mp3')

        response = self.client.get(reverse('exordium:artist', args=(artist_1.normname,)))
        self.assertEqual(response.status_code, 200)

        # Only the Various Artists album should show up
        self.assertContains(response, '1 album')
        self.assertQuerysetEqual(response.context['albums'].data, [repr(album_1)])
        self.assertContains(response, reverse('exordium:album', args=(album_1.pk,)))
        self.assertContains(response, reverse('exordium:artist', args=(various.normname,)))
        self.assertNotContains(response, str(album_2))
        self.assertNotContains(response, reverse('exordium:album', args=(album_2.pk,)))

        # Only one song should show up
        self.assertContains(response, '1 song')
        self.assertQuerysetEqual(response.context['songs'].data, [repr(song_1)])
        self.assertContains(response, reverse('exordium:artist', args=(artist_1.normname,)))
        # This check is a bit silly since it's already shown up above
        self.assertContains(response, reverse('exordium:album', args=(album_1.pk,)))
        self.assertContains(response, song_1.get_download_url_html5())
        self.assertContains(response, song_1.get_download_url_m3u())
        for song in [song_2, song_3, song_4]:
            self.assertNotContains(response, str(song))
            self.assertNotContains(response, song.get_download_url_html5())
            self.assertNotContains(response, song.get_download_url_m3u())

        # Shouldn't see any links to our other two artists
        for artist in [artist_2, artist_3]:
            self.assertNotContains(response, str(artist))
            self.assertNotContains(response, reverse('exordium:artist', args=(artist.normname,)))

    def test_ordering(self):
        """
        Tests ordering of various types of albums.  Regular albums should be first,
        followed by non-album tracks, and then Various-artists albums.  Song lists
        should be alphabetical.
        """
        # "Album 1" and "Album 3" are regular albums
        # "Album 2" is V/A
        # The remaining track will create a non-album track.
        self.add_mp3(artist='Artist 1', title='Title 1',
            album='Album 1', filename='song1.mp3', path='album_1')
        self.add_mp3(artist='Artist 1', title='Title 2',
            album='Album 1', filename='song2.mp3', path='album_1')
        self.add_mp3(artist='Artist 1', title='Title 3',
            album='Album 2', filename='song3.mp3', path='album_2')
        self.add_mp3(artist='Artist 2', title='Title 4',
            album='Album 2', filename='song4.mp3', path='album_2')
        self.add_mp3(artist='Artist 1', title='Title 5',
            album='Album 3', filename='song5.mp3', path='album_3')
        self.add_mp3(artist='Artist 1', title='Title 6',
            album='Album 3', filename='song6.mp3', path='album_3')
        self.add_mp3(artist='Artist 1', title='Title 7',
            filename='song7.mp3')
        self.run_add()

        artist = Artist.objects.get(name='Artist 1')

        self.assertEqual(Album.objects.count(), 4)
        reg_album_1 = Album.objects.get(name='Album 1')
        reg_album_2 = Album.objects.get(name='Album 3')
        va_album = Album.objects.get(name='Album 2')
        misc_album = Album.objects.get(miscellaneous=True)

        response = self.client.get(reverse('exordium:artist', args=(artist.normname,)))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '4 albums')
        self.assertContains(response, '6 songs')
        self.assertQuerysetEqual(response.context['albums'].data,
            [repr(al) for al in [reg_album_1, reg_album_2, misc_album, va_album]])
        self.assertQuerysetEqual(response.context['songs'].data,
            [repr(s) for s in Song.objects.filter(artist=artist).order_by('title')])

        # There are certainly some duplicate tests happening down here.
        for album in [reg_album_1, reg_album_2, misc_album, va_album]:
            self.assertContains(response, str(album))
            self.assertContains(response, str(album.artist))
            self.assertContains(response, reverse('exordium:album', args=(album.pk,)))
            self.assertContains(response, reverse('exordium:artist', args=(album.artist.normname,)))
        for song in Song.objects.filter(artist=artist):
            self.assertContains(response, str(song.title))
            self.assertContains(response, song.get_download_url_html5())
            self.assertContains(response, song.get_download_url_m3u())
        for song in Song.objects.exclude(artist=artist):
            self.assertNotContains(response, str(song.title))
            self.assertNotContains(response, song.get_download_url_html5())
            self.assertNotContains(response, song.get_download_url_m3u())

    def test_classical_as_conductor(self):
        """
        Test the scenario where our only track is as a conductor on
        a track on an album tagged with classical stuff.
        """
        self.add_mp3(artist='Artist 1', title='Title 1',
            group='Group 1', conductor='Conductor 1', composer='Composer 1',
            album='Album 1', filename='song1.mp3', path='album_1')
        self.add_mp3(artist='Artist 1', title='Title 2',
            group='Group 2', conductor='Conductor 2', composer='Composer 2',
            album='Album 1', filename='song2.mp3', path='album_1')
        self.run_add()

        self.assertEqual(Artist.objects.count(), 8)
        artist = Artist.objects.get(name='Conductor 2')

        self.assertEqual(Album.objects.count(), 1)
        album = Album.objects.get()

        self.assertEqual(Song.objects.count(), 2)
        song_1 = Song.objects.get(title='Title 1')
        song_2 = Song.objects.get(title='Title 2')

        response = self.client.get(reverse('exordium:artist', args=(artist.normname,)))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['albums'].data, [repr(album)])
        self.assertContains(response, '1 album')
        self.assertQuerysetEqual(response.context['songs'].data, [repr(song_2)])
        self.assertContains(response, '1 song')
        self.assertContains(response, str(album))
        self.assertContains(response, reverse('exordium:album', args=(album.pk,)))
        
        for artist in Artist.objects.exclude(name='Various'):
            self.assertContains(response, str(artist))
            self.assertContains(response, reverse('exordium:artist', args=(artist.normname,)))

        self.assertNotContains(response, str(song_1))
        self.assertNotContains(response, song_1.get_download_url_html5())
        self.assertNotContains(response, song_1.get_download_url_m3u())
        self.assertContains(response, str(song_2))
        self.assertContains(response, song_2.get_download_url_html5())
        self.assertContains(response, song_2.get_download_url_m3u())

    def test_classical_as_conductor_various(self):
        """
        Test the scenario where our only track is as a conductor on
        a track on an album tagged with classical stuff.  Also the
        album is classified as Various Artists
        """
        self.add_mp3(artist='Artist 1', title='Title 1',
            group='Group 1', conductor='Conductor 1', composer='Composer 1',
            album='Album 1', filename='song1.mp3', path='album_1')
        self.add_mp3(artist='Artist 2', title='Title 2',
            group='Group 2', conductor='Conductor 2', composer='Composer 2',
            album='Album 1', filename='song2.mp3', path='album_1')
        self.run_add()

        self.assertEqual(Artist.objects.count(), 9)
        artist = Artist.objects.get(name='Conductor 2')

        self.assertEqual(Album.objects.count(), 1)
        album = Album.objects.get()

        self.assertEqual(Song.objects.count(), 2)
        song_1 = Song.objects.get(title='Title 1')
        song_2 = Song.objects.get(title='Title 2')

        response = self.client.get(reverse('exordium:artist', args=(artist.normname,)))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['albums'].data, [repr(album)])
        self.assertContains(response, '1 album')
        self.assertQuerysetEqual(response.context['songs'].data, [repr(song_2)])
        self.assertContains(response, '1 song')
        self.assertContains(response, str(album))
        self.assertContains(response, reverse('exordium:album', args=(album.pk,)))
        
        for artist in Artist.objects.exclude(name='Artist 1'):
            self.assertContains(response, str(artist))
            self.assertContains(response, reverse('exordium:artist', args=(artist.normname,)))
        for artist in Artist.objects.filter(name='Artist 1'):
            self.assertNotContains(response, str(artist))
            self.assertNotContains(response, reverse('exordium:artist', args=(artist.normname,)))

        self.assertNotContains(response, str(song_1))
        self.assertNotContains(response, song_1.get_download_url_html5())
        self.assertNotContains(response, song_1.get_download_url_m3u())
        self.assertContains(response, str(song_2))
        self.assertContains(response, song_2.get_download_url_html5())
        self.assertContains(response, song_2.get_download_url_m3u())

    def test_pagination(self):
        """
        Test pagination.  To actually use assertNotContains we have to do both
        album and song pagination at the same time, so we'll go ahead and do that
        rather than splitting them into separate tests.  We show 50 albums and
        25 songs on the artist page.
        """
        for num in range(60):
            self.add_mp3(artist='Artist', title='Title %02d' % (num+1),
                album='Album %02d' % (num+1), filename='song%d.mp3' % (num+1))
        self.run_add()
        self.assertEqual(Album.objects.count(), 60)

        self.assertEqual(Artist.objects.count(), 2)
        artist = Artist.objects.get(name='Artist')

        albums = {}
        for num in range(60):
            albums[num] = Album.objects.get(name='Album %02d' % (num+1))

        songs = {}
        for num in range(60):
            songs[num] = Song.objects.get(title='Title %02d' % (num+1))

        response = self.client.get(reverse('exordium:artist', args=(artist.normname,)))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '50 of 60 albums')
        self.assertContains(response, '25 of 60 songs')
        self.assertContains(response, '"?album-page=2"')
        self.assertContains(response, '"?song-page=2"')
        self.assertEqual(len(response.context['albums'].data), 60)
        self.assertEqual(len(response.context['songs'].data), 60)
        for num in range(50):
            self.assertContains(response, '%s<' % (albums[num]))
            self.assertContains(response, reverse('exordium:album', args=(albums[num].pk,)))
        for num in range(50, 60):
            self.assertNotContains(response, '%s<' % (albums[num]))
            self.assertNotContains(response, reverse('exordium:album', args=(albums[num].pk,)))
        for num in range(25):
            self.assertContains(response, '%s<' % (songs[num]))
        for num in range(25, 60):
            self.assertNotContains(response, '%s<' % (songs[num]))

        # test page 2/3
        response = self.client.get(reverse('exordium:artist', args=(artist.normname,)), {'album-page': 2, 'song-page': 3})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '10 of 60 albums')
        self.assertContains(response, '10 of 60 songs')
        self.assertContains(response, 'album-page=1')
        self.assertContains(response, 'song-page=2')
        self.assertEqual(len(response.context['albums'].data), 60)
        self.assertEqual(len(response.context['songs'].data), 60)
        for num in range(50):
            self.assertNotContains(response, '%s<' % (albums[num]))
            self.assertNotContains(response, reverse('exordium:album', args=(albums[num].pk,)))
        for num in range(50, 60):
            self.assertContains(response, '%s<' % (albums[num]))
            self.assertContains(response, reverse('exordium:album', args=(albums[num].pk,)))
        for num in range(50):
            self.assertNotContains(response, '%s<' % (songs[num]))
        for num in range(50, 60):
            self.assertContains(response, '%s<' % (songs[num]))

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
        artist = Artist.objects.get(name='Artist')

        response = self.client.get(reverse('exordium:artist', args=(artist.normname,)))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['albums'].data), 3)
        self.assertQuerysetEqual(response.context['albums'].data, [repr(al) for al in albums])
        self.assertContains(response, '"?album-sort=year"')

        # test the sorting button
        response = self.client.get(reverse('exordium:artist', args=(artist.normname,)), {'album-sort': 'year'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['albums'].data), 3)
        self.assertQuerysetEqual(response.context['albums'].data, [repr(al) for al in reversed(albums)])
        self.assertContains(response, '"?album-sort=-year"')

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
        artist = Artist.objects.get(name='Artist')

        response = self.client.get(reverse('exordium:artist', args=(artist.normname,)), {'album-sort': 'year'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['albums'].data), 2)
        self.assertQuerysetEqual(response.context['albums'].data, [repr(al) for al in albums])
        self.assertContains(response, '"?album-sort=-year"')

        # test reverse sort
        response = self.client.get(reverse('exordium:artist', args=(artist.normname,)), {'album-sort': '-year'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['albums'].data), 2)
        self.assertQuerysetEqual(response.context['albums'].data, [repr(al) for al in reversed(albums)])
        self.assertContains(response, '"?album-sort=year"')

    def test_sorting_song(self):
        """
        Test at least one case of song sorting.
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album 3', filename='song1.mp3')
        self.add_mp3(artist='Artist', title='Title 2',
            album='Album 2', filename='song2.mp3')
        self.add_mp3(artist='Artist', title='Title 3',
            album='Album 1', filename='song3.mp3')
        self.run_add()
        self.assertEqual(Album.objects.count(), 3)

        songs = [
            Song.objects.get(title='Title 1'),
            Song.objects.get(title='Title 2'),
            Song.objects.get(title='Title 3'),
        ]
        artist = Artist.objects.get(name='Artist')

        response = self.client.get(reverse('exordium:artist', args=(artist.normname,)))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['songs'].data), 3)
        self.assertQuerysetEqual(response.context['songs'].data, [repr(al) for al in songs])
        self.assertContains(response, '"?song-sort=album"')

        # test the sorting button
        response = self.client.get(reverse('exordium:artist', args=(artist.normname,)), {'song-sort': 'album'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['songs'].data), 3)
        self.assertQuerysetEqual(response.context['songs'].data, [repr(al) for al in reversed(songs)])
        self.assertContains(response, '"?song-sort=-album"')

    def test_too_many_songs(self):
        """
        If an artist has more than 500 songs, the song list won't be
        shown on the artist page.  We're going to cheat here and
        insert directly into the database rather than going through our
        ``run_add()`` rigamarole.  Quite possibly I should be doing that
        on all our pagination tests, too, since those are noticeably
        slow.  Ah well.
        """
        artist = Artist.objects.create(name='Artist', normname='artist')
        album = Album.objects.create(artist=artist, name='Album', normname='album')
        for num in range(501):
            Song.objects.create(filename='file%03d.mp3' % (num+1),
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

        response = self.client.get(reverse('exordium:artist', args=(artist.normname,)))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['albums'].data, [repr(album)])
        self.assertEqual(response.context['have_songs'], False)
        self.assertNotIn('songs', response.context)
        self.assertNotContains(response, 'Songs by %s' % (artist))
        self.assertContains(response, reverse('exordium:artist', args=(artist.normname,)))
        self.assertContains(response, reverse('exordium:album', args=(album.pk,)))
        self.assertContains(response, '1 album')
        self.assertNotContains(response, '1 song')

