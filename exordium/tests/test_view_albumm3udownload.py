from .base import ExordiumTests

from django.urls import reverse

from exordium.models import Artist, Album, Song, App, AlbumArt

class AlbumM3UDownloadViewTests(ExordiumTests):
    """
    Tests for our album M3U downloads
    """

    def test_invalid_album(self):
        """
        Tests making a request for an album which can't be found.
        """
        response = self.client.get(reverse('exordium:m3udownload', args=(42,)))
        self.assertEqual(response.status_code, 404)

    def test_one_track_album(self):
        """
        Test getting a one-track album M3U
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3')
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        album = Album.objects.get()

        self.assertEqual(Song.objects.count(), 1)
        song = Song.objects.get()

        response = self.client.get(reverse('exordium:m3udownload', args=(album.pk,)))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'audio/mpegurl')
        self.assertEqual(response['Content-Disposition'], 'attachment; filename=Artist_-_Album.m3u')
        self.assertContains(response, '#EXTM3U')
        self.assertContains(response, '#EXTINF:')
        self.assertContains(response, str(song.artist))
        self.assertContains(response, str(song.title))
        self.assertContains(response, '(%s)' % (str(song.album)))
        self.assertContains(response, song.get_download_url_m3u())

    def test_three_track_album(self):
        """
        Test getting a three-track album M3U
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3')
        self.add_mp3(artist='Artist', title='Title 2',
            album='Album', filename='song2.mp3')
        self.add_mp3(artist='Artist', title='Title 3',
            album='Album', filename='song3.mp3')
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        album = Album.objects.get()

        self.assertEqual(Song.objects.count(), 3)

        response = self.client.get(reverse('exordium:m3udownload', args=(album.pk,)))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'audio/mpegurl')
        self.assertEqual(response['Content-Disposition'], 'attachment; filename=Artist_-_Album.m3u')
        self.assertContains(response, '#EXTM3U')
        self.assertContains(response, '#EXTINF:')
        self.assertContains(response, '(%s)' % (str(album)))
        for song in Song.objects.all():
            self.assertContains(response, str(song.artist))
            self.assertContains(response, str(song.title))
            self.assertContains(response, song.get_download_url_m3u())

