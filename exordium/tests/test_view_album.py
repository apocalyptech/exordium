from .base import ExordiumUserTests

from django.urls import reverse

from django.templatetags.static import static

from exordium.models import Artist, Album, Song, App, AlbumArt

class AlbumViewTests(ExordiumUserTests):
    """
    Tests of our Album info page
    """

    def test_invalid_album(self):
        """
        Tests making a request for an album which can't be found.
        """
        response = self.client.get(reverse('exordium:album', args=(42,)))
        self.assertEqual(response.status_code, 404)

    def test_minimal_album(self):
        """
        Test a minimally-tagged album
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3')
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        album = Album.objects.get()

        self.assertEqual(Song.objects.count(), 1)
        song = Song.objects.get()

        response = self.client.get(reverse('exordium:album', args=(album.pk,)))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['songs'].data, [repr(song)])
        self.assertEqual(response.context['groups'], [])
        self.assertEqual(response.context['composers'], [])
        self.assertEqual(response.context['conductors'], [])
        self.assertNotContains(response, 'Ensemble')
        self.assertNotContains(response, 'Conductor')
        self.assertNotContains(response, 'Composer')
        self.assertContains(response, reverse('exordium:artist', args=(album.artist.normname,)))
        self.assertContains(response, str(album))
        self.assertContains(response, str(album.artist))
        self.assertNotContains(response, 'Year:')
        self.assertContains(response, 'Tracks: <strong>1</strong>')
        self.assertContains(response, 'Length: <strong>0:02</strong>')
        self.assertContains(response, 'Added on:')
        self.assertContains(response, reverse('exordium:m3udownload', args=(album.pk,)))
        self.assertContains(response, 'albumstreambutton')
        self.assertContains(response, '"%s"' % (static('exordium/no_album_art.png')))
        self.assertContains(response, song.title)
        self.assertContains(response, '1 item')

        # Ensure we have a tracknum column, but not an album column
        self.assertContains(response, '"?sort=tracknum"')
        self.assertNotContains(response, '"?sort=album"')

        # At the moment we do not have album downloads enabled, so we should not see
        # the download button.
        self.assertNotContains(response, reverse('exordium:albumdownload', args=(album.pk,)))

        # We are not logged in, so we shouldn't see the album art regen button
        self.assertNotContains(response, reverse('exordium:albumartupdate', args=(album.pk,)))

    def test_minimal_album_art(self):
        """
        Test a minimally-tagged album which also has album art.
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3')
        self.add_art()
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        album = Album.objects.get()

        self.assertEqual(Song.objects.count(), 1)
        song = Song.objects.get()

        response = self.client.get(reverse('exordium:album', args=(album.pk,)))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['songs'].data, [repr(song)])
        self.assertEqual(response.context['groups'], [])
        self.assertEqual(response.context['composers'], [])
        self.assertEqual(response.context['conductors'], [])
        self.assertNotContains(response, 'Ensemble')
        self.assertNotContains(response, 'Conductor')
        self.assertNotContains(response, 'Composer')
        self.assertContains(response, reverse('exordium:artist', args=(album.artist.normname,)))
        self.assertContains(response, str(album))
        self.assertContains(response, str(album.artist))
        self.assertNotContains(response, 'Year:')
        self.assertContains(response, 'Tracks: <strong>1</strong>')
        self.assertContains(response, 'Length: <strong>0:02</strong>')
        self.assertContains(response, 'Added on:')
        self.assertContains(response, reverse('exordium:m3udownload', args=(album.pk,)))
        self.assertContains(response, 'albumstreambutton')
        self.assertNotContains(response, '"%s"' % (static('exordium/no_album_art.png')))
        self.assertContains(response, reverse('exordium:albumart', args=(album.pk, 'album',)))
        self.assertContains(response, reverse('exordium:origalbumart', args=(album.pk, album.art_ext,)))
        self.assertContains(response, song.title)
        self.assertContains(response, '1 item')

        # Ensure we have a tracknum column, but not an album column
        self.assertContains(response, '"?sort=tracknum"')
        self.assertNotContains(response, '"?sort=album"')

        # At the moment we do not have album downloads enabled, so we should not see
        # the download button.
        self.assertNotContains(response, reverse('exordium:albumdownload', args=(album.pk,)))

        # We are not logged in, so we shouldn't see the album art regen button
        self.assertNotContains(response, reverse('exordium:albumartupdate', args=(album.pk,)))

    def test_login_album_no_art(self):
        """
        Test view when we're logged in and have no album art.  Should see our
        update button now.
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3')
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        album = Album.objects.get()

        self.login()
        response = self.client.get(reverse('exordium:album', args=(album.pk,)))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '"%s"' % (static('exordium/no_album_art.png')))
        self.assertContains(response, reverse('exordium:albumartupdate', args=(album.pk,)))

    def test_login_album_with_art(self):
        """
        Test view when we're logged in and have album art.  Should have our update button.
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3')
        self.add_art()
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        album = Album.objects.get()

        self.login()
        response = self.client.get(reverse('exordium:album', args=(album.pk,)))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, '"%s"' % (static('exordium/no_album_art.png')))
        self.assertContains(response, reverse('exordium:albumart', args=(album.pk, 'album',)))
        self.assertContains(response, reverse('exordium:origalbumart', args=(album.pk, album.art_ext,)))
        self.assertContains(response, reverse('exordium:albumartupdate', args=(album.pk,)))

    def test_fully_tagged_album(self):
        """
        Test a fully-tagged album
        """
        self.add_mp3(artist='Artist', title='Title 1', tracknum=1,
            year=2016, group='Group', conductor='Conductor',
            composer='Composer',
            album='Album', filename='song1.mp3')
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        album = Album.objects.get()

        self.assertEqual(Song.objects.count(), 1)
        song = Song.objects.get()

        artist = Artist.objects.get(name='Artist')
        group = Artist.objects.get(name='Group')
        conductor = Artist.objects.get(name='Conductor')
        composer = Artist.objects.get(name='Composer')

        response = self.client.get(reverse('exordium:album', args=(album.pk,)))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['songs'].data, [repr(song)])
        self.assertQuerysetEqual(response.context['groups'], [repr(group)])
        self.assertQuerysetEqual(response.context['composers'], [repr(composer)])
        self.assertQuerysetEqual(response.context['conductors'], [repr(conductor)])
        self.assertEqual(response.context['have_empty_group'], False)
        self.assertEqual(response.context['have_empty_composer'], False)
        self.assertEqual(response.context['have_empty_conductor'], False)
        self.assertContains(response, 'Ensemble:')
        self.assertContains(response, 'Conductor:')
        self.assertContains(response, 'Composer:')
        self.assertContains(response, reverse('exordium:artist', args=(album.artist.normname,)))
        self.assertContains(response, reverse('exordium:artist', args=(group.normname,)))
        self.assertContains(response, reverse('exordium:artist', args=(conductor.normname,)))
        self.assertContains(response, reverse('exordium:artist', args=(composer.normname,)))
        self.assertContains(response, str(album))
        self.assertContains(response, str(album.artist))
        self.assertContains(response, str(group))
        self.assertContains(response, str(conductor))
        self.assertContains(response, str(composer))
        self.assertContains(response, 'Year: <strong>2016</strong>')
        self.assertContains(response, 'Tracks: <strong>1</strong>')
        self.assertContains(response, 'Length: <strong>0:02</strong>')
        self.assertContains(response, song.title)
        self.assertContains(response, '"?sort=tracknum"')
        self.assertContains(response, '1 item')

    def test_fully_tagged_album_two_tracks(self):
        """
        Test a fully-tagged album, with two tracks
        """
        self.add_mp3(artist='Artist', title='Title 1', tracknum=1,
            year=2016, group='Group', conductor='Conductor',
            composer='Composer',
            album='Album', filename='song1.mp3')
        self.add_mp3(artist='Artist', title='Title 2', tracknum=2,
            year=2016, group='Group 2', conductor='Conductor 2',
            composer='Composer 2',
            album='Album', filename='song2.mp3')
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        album = Album.objects.get()

        self.assertEqual(Song.objects.count(), 2)
        songs = [
            Song.objects.get(filename='song1.mp3'),
            Song.objects.get(filename='song2.mp3'),
        ]

        artist = Artist.objects.get(name='Artist')
        groups = [
            Artist.objects.get(name='Group'),
            Artist.objects.get(name='Group 2'),
        ]
        conductors = [
            Artist.objects.get(name='Conductor'),
            Artist.objects.get(name='Conductor 2'),
        ]
        composers = [
            Artist.objects.get(name='Composer'),
            Artist.objects.get(name='Composer 2'),
        ]

        response = self.client.get(reverse('exordium:album', args=(album.pk,)))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['songs'].data, [repr(song) for song in songs])
        self.assertQuerysetEqual(response.context['groups'], [repr(group) for group in groups])
        self.assertQuerysetEqual(response.context['composers'], [repr(composer) for composer in composers])
        self.assertQuerysetEqual(response.context['conductors'], [repr(conductor) for conductor in conductors])
        self.assertEqual(response.context['have_empty_group'], False)
        self.assertEqual(response.context['have_empty_composer'], False)
        self.assertEqual(response.context['have_empty_conductor'], False)
        self.assertContains(response, 'Ensembles:')
        self.assertContains(response, 'Conductors:')
        self.assertContains(response, 'Composers:')
        for a in [artist] + groups + conductors + composers:
            self.assertContains(response, reverse('exordium:artist', args=(a.normname,)))
            self.assertContains(response, str(a))
        self.assertContains(response, str(album))
        self.assertContains(response, str(album.artist))
        self.assertContains(response, 'Year: <strong>2016</strong>')
        self.assertContains(response, 'Tracks: <strong>2</strong>')
        self.assertContains(response, 'Length: <strong>0:04</strong>')
        for song in songs:
            self.assertContains(response, song.title)
        self.assertContains(response, '"?sort=tracknum"')
        self.assertContains(response, '2 items')

    def test_fully_tagged_album_two_tracks_various(self):
        """
        Test a fully-tagged album, with two tracks, which is also a various-artists
        album.
        """
        self.add_mp3(artist='Artist 1', title='Title 1', tracknum=1,
            year=2016, group='Group 1', conductor='Conductor 1',
            composer='Composer 1',
            album='Album', filename='song1.mp3')
        self.add_mp3(artist='Artist 2', title='Title 2', tracknum=2,
            year=2016, group='Group 2', conductor='Conductor 2',
            composer='Composer 2',
            album='Album', filename='song2.mp3')
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        album = Album.objects.get()

        self.assertEqual(Song.objects.count(), 2)
        songs = [
            Song.objects.get(filename='song1.mp3'),
            Song.objects.get(filename='song2.mp3'),
        ]

        various = Artist.objects.get(name='Various')
        artists = [
            Artist.objects.get(name='Artist 1'),
            Artist.objects.get(name='Artist 2'),
        ]
        groups = [
            Artist.objects.get(name='Group 1'),
            Artist.objects.get(name='Group 2'),
        ]
        conductors = [
            Artist.objects.get(name='Conductor 1'),
            Artist.objects.get(name='Conductor 2'),
        ]
        composers = [
            Artist.objects.get(name='Composer 1'),
            Artist.objects.get(name='Composer 2'),
        ]

        response = self.client.get(reverse('exordium:album', args=(album.pk,)))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Various')
        self.assertContains(response, reverse('exordium:artist', args=(various.normname,)))
        self.assertQuerysetEqual(response.context['songs'].data, [repr(song) for song in songs])
        self.assertQuerysetEqual(response.context['groups'], [repr(group) for group in groups])
        self.assertQuerysetEqual(response.context['composers'], [repr(composer) for composer in composers])
        self.assertQuerysetEqual(response.context['conductors'], [repr(conductor) for conductor in conductors])
        self.assertEqual(response.context['have_empty_group'], False)
        self.assertEqual(response.context['have_empty_composer'], False)
        self.assertEqual(response.context['have_empty_conductor'], False)
        self.assertContains(response, 'Ensembles:')
        self.assertContains(response, 'Conductors:')
        self.assertContains(response, 'Composers:')
        for a in artists + groups + conductors + composers:
            self.assertContains(response, reverse('exordium:artist', args=(a.normname,)))
            self.assertContains(response, str(a))
        self.assertContains(response, str(album))
        self.assertContains(response, str(album.artist))
        self.assertContains(response, 'Year: <strong>2016</strong>')
        self.assertContains(response, 'Tracks: <strong>2</strong>')
        self.assertContains(response, 'Length: <strong>0:04</strong>')
        for song in songs:
            self.assertContains(response, song.title)
        self.assertContains(response, '"?sort=tracknum"')
        self.assertContains(response, '2 items')

    def test_album_some_tracks_with_classical_tags_others_without(self):
        """
        Tests display of an album in which one track has classical tags defined
        but the other does not.  The classical tags should be displayed up in
        the top header, but also with a note that some tracks don't have the
        tags.  Technically we should have a check for making sure the tracks
        themselves are showing the information, though we can't really do that
        without hooking into selenium or whatever.
        """
        self.add_mp3(artist='Artist', title='Title 1', tracknum=1,
            year=2016, group='Group', conductor='Conductor',
            composer='Composer',
            album='Album', filename='song1.mp3')
        self.add_mp3(artist='Artist', title='Title 2', tracknum=2,
            year=2016, album='Album', filename='song2.mp3')
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        album = Album.objects.get()

        self.assertEqual(Song.objects.count(), 2)
        songs = [
            Song.objects.get(filename='song1.mp3'),
            Song.objects.get(filename='song2.mp3'),
        ]

        artist = Artist.objects.get(name='Artist')
        group = Artist.objects.get(name='Group')
        conductor = Artist.objects.get(name='Conductor')
        composer = Artist.objects.get(name='Composer')

        response = self.client.get(reverse('exordium:album', args=(album.pk,)))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['songs'].data, [repr(song) for song in songs])
        self.assertQuerysetEqual(response.context['groups'], [repr(group)])
        self.assertQuerysetEqual(response.context['composers'], [repr(composer)])
        self.assertQuerysetEqual(response.context['conductors'], [repr(conductor)])
        self.assertEqual(response.context['have_empty_group'], True)
        self.assertEqual(response.context['have_empty_composer'], True)
        self.assertEqual(response.context['have_empty_conductor'], True)
        self.assertContains(response, 'Ensemble:')
        self.assertContains(response, 'Conductor:')
        self.assertContains(response, 'Composer:')
        self.assertContains(response, 'Some tracks have no ensemble')
        self.assertContains(response, 'Some tracks have no conductor')
        self.assertContains(response, 'Some tracks have no composer')
        for a in [artist, group, conductor, composer]:
            self.assertContains(response, reverse('exordium:artist', args=(a.normname,)))
            self.assertContains(response, str(a))
        self.assertContains(response, str(album))
        self.assertContains(response, str(album.artist))
        self.assertContains(response, 'Year: <strong>2016</strong>')
        self.assertContains(response, 'Tracks: <strong>2</strong>')
        self.assertContains(response, 'Length: <strong>0:04</strong>')
        for song in songs:
            self.assertContains(response, song.title)
        self.assertContains(response, '"?sort=tracknum"')
        self.assertContains(response, '2 items')

    def test_miscellaneous_album(self):
        """
        Test a miscellaneous (non-album-tracks) album.  The only real difference
        is that this table should NOT contain a tracknum column.
        """
        self.add_mp3(artist='Artist', title='Title 1', filename='song1.mp3')
        self.run_add()

        self.assertEqual(Song.objects.count(), 1)
        song = Song.objects.get()

        self.assertEqual(Album.objects.count(), 1)
        album = Album.objects.get()

        response = self.client.get(reverse('exordium:album', args=(album.pk,)))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['songs'].data, [repr(song)])
        self.assertContains(response, song.title)
        self.assertNotContains(response, '"?sort=tracknum"')
        self.assertContains(response, '1 item')

    def test_sorting_song(self):
        """
        Test at least one case of song sorting.  Default sorting is by track
        number.
        """
        self.add_mp3(artist='Artist', title='Title 3', tracknum=1,
            album='Album', filename='song1.mp3')
        self.add_mp3(artist='Artist', title='Title 2', tracknum=2,
            album='Album', filename='song2.mp3')
        self.add_mp3(artist='Artist', title='Title 1', tracknum=3,
            album='Album', filename='song3.mp3')
        self.run_add()

        songs = [
            Song.objects.get(filename='song1.mp3'),
            Song.objects.get(filename='song2.mp3'),
            Song.objects.get(filename='song3.mp3'),
        ]
        album = Album.objects.get(name='Album')

        response = self.client.get(reverse('exordium:album', args=(album.pk,)))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['songs'].data), 3)
        self.assertQuerysetEqual(response.context['songs'].data, [repr(song) for song in songs])
        self.assertContains(response, '"?sort=title"')
        self.assertContains(response, '3 items')

        # test the sorting button
        response = self.client.get(reverse('exordium:album', args=(album.pk,)), {'sort': 'title'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['songs'].data), 3)
        self.assertQuerysetEqual(response.context['songs'].data, [repr(song) for song in reversed(songs)])
        self.assertContains(response, '"?sort=-title"')
        self.assertContains(response, '3 items')

    def test_pagination(self):
        """
        Test pagination.  Our album view will show 100 tracks, so rather than
        going through our whole ``run_add()`` process, we're just importing
        directly into the database.  Should probably do this for the rest of our
        pagination tests, too, actually, given that ``run_add()`` can be rather
        slow.
        """
        artist = Artist.objects.create(name='Artist', normname='artist')
        album = Album.objects.create(artist=artist, name='Album', normname='album')
        songs = {}
        for num in range(120):
            songs[num] = Song.objects.create(filename='file%03d.mp3' % (num+1),
                artist=artist,
                album=album,
                title='Title %03d' % (num+1),
                year=2016,
                tracknum=num+1,
                normtitle='title %03d' % (num+1),
                raw_artist='artist',
                filetype=Song.MP3,
                bitrate=128000,
                mode=Song.CBR,
                size=123000,
                length=90,
                sha256sum='0cf31fc7d968ec16c69758f9b0ebb2355471d5694a151b40e5e4f8641b061092',
            )

        response = self.client.get(reverse('exordium:album', args=(album.pk,)))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '100 of 120 items')
        self.assertContains(response, '"?page=2"')
        self.assertEqual(len(response.context['songs'].data), 120)
        for num in range(100):
            self.assertContains(response, '%s<' % (songs[num]))
            self.assertContains(response, "'%s'" % (songs[num].get_download_url_html5()))
            self.assertContains(response, '"%s"' % (songs[num].get_download_url_m3u()))
        for num in range(100, 120):
            self.assertNotContains(response, '%s<' % (songs[num]))
            # Note that our album-streaming button *will* have all html5 results in there,
            # even stuff from future pages
            self.assertContains(response, "'%s'" % (songs[num].get_download_url_html5()))
            self.assertNotContains(response, '"%s"' % (songs[num].get_download_url_m3u()))

        # test page 2
        response = self.client.get(reverse('exordium:album', args=(album.pk,)), {'page': 2})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '20 of 120 items')
        self.assertContains(response, '"?page=1"')
        self.assertEqual(len(response.context['songs'].data), 120)
        for num in range(100):
            self.assertNotContains(response, '%s<' % (songs[num]))
            # Likewise -- the album-streaming button will have everything
            self.assertContains(response, "'%s'" % (songs[num].get_download_url_html5()))
            self.assertNotContains(response, '"%s"' % (songs[num].get_download_url_m3u()))
        for num in range(100, 120):
            self.assertContains(response, '%s<' % (songs[num]))
            self.assertContains(response, "'%s'" % (songs[num].get_download_url_html5()))
            self.assertContains(response, '"%s"' % (songs[num].get_download_url_m3u()))

    def test_play_button_single(self):
        """
        Test to make sure we have a "play" button for a single (streamable) track
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3')
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        album = Album.objects.get()

        self.assertEqual(Song.objects.count(), 1)
        song = Song.objects.get()

        response = self.client.get(reverse('exordium:album', args=(album.pk,)))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['songs'].data, [repr(song)])
        self.assertContains(response, 'playbutton')
        self.assertContains(response, 'Stream this track')

    def test_no_play_button_single(self):
        """
        Test to make sure we do NOT have a "play" button for a single
        (non-streamable) track.  That just means Ogg Opus, for now.
        """
        self.add_opus(artist='Artist', title='Title 1',
            album='Album', filename='song1.opus')
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        album = Album.objects.get()

        self.assertEqual(Song.objects.count(), 1)
        song = Song.objects.get()

        response = self.client.get(reverse('exordium:album', args=(album.pk,)))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['songs'].data, [repr(song)])
        self.assertNotContains(response, 'playbutton')
        self.assertNotContains(response, 'Stream this track')
        self.assertContains(response, 'Track cannot be streamed')

    def test_play_button_two_tracks_mixed(self):
        """
        Test to make sure we have both a "play" button and a non-streamable notice,
        for an album with one streamable and one non-streamable track.
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3')
        self.add_opus(artist='Artist', title='Title 2',
            album='Album', filename='song2.opus')
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        album = Album.objects.get()

        self.assertEqual(Song.objects.count(), 2)
        songs = [
            Song.objects.get(filename='song1.mp3'),
            Song.objects.get(filename='song2.opus'),
        ]

        response = self.client.get(reverse('exordium:album', args=(album.pk,)))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['songs'].data, [repr(song) for song in songs])
        self.assertContains(response, 'playbutton')
        self.assertContains(response, 'Stream this track')
        self.assertContains(response, 'Track cannot be streamed')

    def test_html5_album_stream_button(self):
        """
        Test to make sure we have a jPlayer-based album stream button
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3')
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Song.objects.count(), 1)
        album = Album.objects.get()

        response = self.client.get(reverse('exordium:album', args=(album.pk,)))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'albumstreambutton')
        self.assertNotContains(response, 'albumstreambutton" disabled')
        self.assertContains(response, '>Stream Album (HTML5 pop-up)<')

    def test_html5_no_album_stream_button(self):
        """
        Test to make sure we do NOT have a jPlayer-based album stream button,
        when there are no jPlayer-streamable tracks present
        """
        self.add_opus(artist='Artist', title='Title 1',
            album='Album', filename='song1.opus')
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Song.objects.count(), 1)
        album = Album.objects.get()

        response = self.client.get(reverse('exordium:album', args=(album.pk,)))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'albumstreambutton" disabled')
        self.assertContains(response, '>Stream Album (HTML5 pop-up - unavailable)<')

    def test_html5_album_stream_button_mixed(self):
        """
        Test to make sure we have a jPlayer-based album stream button when we
        have a mixed-jPlayer-streamable album present.  Note that this doesn't
        *really* test this fully, since we're not inspecting the contents of the
        button's Javascript, but whatever.
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3')
        self.add_opus(artist='Artist', title='Title 2',
            album='Album', filename='song2.opus')
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Song.objects.count(), 2)
        album = Album.objects.get()

        response = self.client.get(reverse('exordium:album', args=(album.pk,)))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'albumstreambutton')
        self.assertNotContains(response, 'albumstreambutton" disabled')
        self.assertContains(response, '>Stream Album (HTML5 pop-up)<')

