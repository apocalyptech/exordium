from .base import ExordiumUserTests

from django.urls import reverse

import os
import shutil
import zipfile
import tempfile

from exordium.models import Artist, Album, Song, App, AlbumArt

class AlbumDownloadViewTests(ExordiumUserTests):
    """
    Tests for album downloads
    """

    def setUp(self):
        """
        For these tests we need to have a place to store our zipfiles
        """
        super(AlbumDownloadViewTests, self).setUp()
        self.zipfile_path = tempfile.mkdtemp()
        self.prefs['exordium__zipfile_path'] = self.zipfile_path
        self.prefs['exordium__zipfile_url'] = 'http://testserver-zip/zipfiles'

    def tearDown(self):
        """
        Get rid of our zipfile download path
        """
        super(AlbumDownloadViewTests, self).tearDown()
        if os.path.exists(self.zipfile_path):
            shutil.rmtree(self.zipfile_path)

    def test_model_support_zipfile_no_zip_dir(self):
        """
        Tests a few conditions of our App.support_zipfile() method to ensure that
        it returns False when the zip dir doesn't exist.
        """
        # Should start out True
        self.assertEqual(App.support_zipfile(), True)
        
        # Should return False if we're configured but the zip dir doesn't
        # actually exist
        shutil.rmtree(self.zipfile_path)
        self.assertEqual(App.support_zipfile(), False)

    def test_model_support_zipfile_no_zip_path(self):
        """
        Tests a few conditions of our App.support_zipfile() method to ensure that
        it returns False when the zip path isn't configured
        """
        # Should start out True
        self.assertEqual(App.support_zipfile(), True)

        # Return false when the configured path is blank
        self.prefs['exordium__zipfile_path'] = ''
        self.assertEqual(App.support_zipfile(), False)

    def test_model_support_zipfile_no_zip_url(self):
        """
        Tests a few conditions of our App.support_zipfile() method to ensure that
        it returns False when the zip path isn't configured
        """

        # Should start out True
        self.assertEqual(App.support_zipfile(), True)

        # When the URL isn't configured, return False
        self.prefs['exordium__zipfile_url'] = ''
        self.assertEqual(App.support_zipfile(), False)

    def test_library_view_show_zipfile(self):
        """
        Test our library management view when we have zipfile configured.  Should
        show our zipfile info.  (The rest of the library management page is tested
        in ``LibraryViewTests``)
        """

        self.login()
        response = self.client.get(reverse('exordium:library'))
        self.assertEqual(response.status_code, 200)

        App.ensure_prefs()
        self.assertContains(response, 'Zipfile Support:</strong> Yes')
        self.assertNotContains(response, 'Zipfile Support:</strong> No')
        self.assertContains(response, App.prefs['exordium__zipfile_url'])
        self.assertContains(response, App.prefs['exordium__zipfile_path'])

    def test_download_button_present(self):
        """
        Test to ensure that the album view renders our download button
        now that we have the necessary preferences set.  The inverse of
        this is taken care of via various tests in ``AlbumViewTests``.
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3')
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        album = Album.objects.get()

        response = self.client.get(reverse('exordium:album', args=(album.pk,)))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '"%s"' % (reverse('exordium:albumdownload', args=(album.pk,))))

    def test_album_download_without_configuration(self):
        """
        Test what happens when someone requests a download when we're
        not actually configured for it.
        """

        # Have to clear out these vars for this test
        self.prefs['exordium__zipfile_path'] = ''
        self.prefs['exordium__zipfile_url'] = ''

        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3')
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        album = Album.objects.get()

        response = self.client.get(reverse('exordium:albumdownload', args=(album.pk,)))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Exordium is not currently configured to allow zipfile creation')
        self.assertNotContains(response, '"%s"' % (reverse('exordium:albumdownload', args=(album.pk,))))
        self.assertNotContains(response, 'meta http-equiv')

    def test_model_create_zip_without_configuration(self):
        """
        Test what happens when ``Album.create_zip()`` is called when
        we're not actually configured for it.  This isn't actually possible
        in the app currently since that is checked before we even get to
        that point, but we'll test regardless.
        """

        # Have to clear out these vars for this test
        self.prefs['exordium__zipfile_path'] = ''
        self.prefs['exordium__zipfile_url'] = ''

        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3')
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        album = Album.objects.get()

        self.assertRaises(App.AlbumZipfileNotSupported, album.create_zip)

    def test_basic_album_download(self):
        """
        Test to ensure that we can generate zipfiles
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3', path='Album')
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        album = Album.objects.get()

        self.assertEqual(Song.objects.count(), 1)
        song = Song.objects.get()

        response = self.client.get(reverse('exordium:albumdownload', args=(album.pk,)))
        self.assertEqual(response.status_code, 200)
        self.assertIn('filenames', response.context)
        self.assertIn('zip_file', response.context)
        self.assertIn('zip_url', response.context)
        self.assertEqual(response.context['filenames'], ['Album/song1.mp3'])
        self.assertEqual(response.context['zip_file'], 'Artist_-_Album.zip')
        self.assertContains(response, 'Album/song1.mp3<')
        self.assertContains(response, response.context['zip_file'])
        self.assertContains(response, response.context['zip_url'])
        self.assertContains(response, 'meta http-equiv')
        zip_file = os.path.join(self.zipfile_path, response.context['zip_file'])
        self.assertEqual(os.path.exists(zip_file), True)

        with zipfile.ZipFile(zip_file, 'r') as zf:
            self.assertEqual(zf.namelist(), ['Album/song1.mp3'])

    def test_basic_album_download_at_library_base(self):
        """
        Test to ensure that we can generate zipfiles from files stored
        right at the library base directory.  The top-level dir stored
        in the zipfile should be the name of the library dir itself,
        which in our case is gonna be the bit of randomness provided
        by ``tempfile.mkdtemp()``.
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3')
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        album = Album.objects.get()

        self.assertEqual(Song.objects.count(), 1)
        song = Song.objects.get()

        library_base = os.path.basename(self.library_path)
        song_full = os.path.join(library_base, 'song1.mp3')

        response = self.client.get(reverse('exordium:albumdownload', args=(album.pk,)))
        self.assertEqual(response.status_code, 200)
        self.assertIn('filenames', response.context)
        self.assertIn('zip_file', response.context)
        self.assertIn('zip_url', response.context)
        self.assertEqual(response.context['filenames'], [song_full])
        self.assertEqual(response.context['zip_file'], 'Artist_-_Album.zip')
        self.assertContains(response, '%s<' % (song_full))
        self.assertContains(response, response.context['zip_file'])
        self.assertContains(response, response.context['zip_url'])
        self.assertContains(response, 'meta http-equiv')
        zip_file = os.path.join(self.zipfile_path, response.context['zip_file'])
        self.assertEqual(os.path.exists(zip_file), True)

        with zipfile.ZipFile(zip_file, 'r') as zf:
            self.assertEqual(zf.namelist(), [song_full])

    def test_basic_album_download_song_before_1980(self):
        """
        Test to ensure that we can generate zipfiles with files created
        before 1980.  Zipfiles can't store dates prior to 1980, so the
        zip process will fail.  We catch that exception in the app and
        then do some nonsense to inject the song with the current
        timestamp, so we'd like to make sure that works.  Pretty unlikely,
        but I ended up having a file right near the epoch (possibly on
        the epoch) due to some past weirdness, no doubt.
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3', path='Album')
        self.run_add()
        self.set_file_ancient('Album/song1.mp3')

        self.assertEqual(Album.objects.count(), 1)
        album = Album.objects.get()

        self.assertEqual(Song.objects.count(), 1)
        song = Song.objects.get()

        response = self.client.get(reverse('exordium:albumdownload', args=(album.pk,)))
        self.assertEqual(response.status_code, 200)
        self.assertIn('filenames', response.context)
        self.assertIn('zip_file', response.context)
        self.assertIn('zip_url', response.context)
        self.assertEqual(response.context['filenames'], ['Album/song1.mp3'])
        self.assertEqual(response.context['zip_file'], 'Artist_-_Album.zip')
        self.assertContains(response, 'Album/song1.mp3<')
        self.assertContains(response, response.context['zip_file'])
        self.assertContains(response, response.context['zip_url'])
        self.assertContains(response, 'meta http-equiv')
        zip_file = os.path.join(self.zipfile_path, response.context['zip_file'])
        self.assertEqual(os.path.exists(zip_file), True)

        with zipfile.ZipFile(zip_file, 'r') as zf:
            self.assertEqual(zf.namelist(), ['Album/song1.mp3'])

    def test_basic_album_download_twice(self):
        """
        Generate a zipfile and then request the zipfile again.  Should get a page
        back which has a link to the zipfile, and a message about how it was
        generated previously.
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3', path='Album')
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        album = Album.objects.get()

        self.assertEqual(Song.objects.count(), 1)
        song = Song.objects.get()

        # Original request
        response = self.client.get(reverse('exordium:albumdownload', args=(album.pk,)))
        self.assertEqual(response.status_code, 200)

        # Subsequent request
        response = self.client.get(reverse('exordium:albumdownload', args=(album.pk,)))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Zipfile already exists.  You should be able to download with the link below.')
        self.assertNotIn('filenames', response.context)
        self.assertIn('zip_file', response.context)
        self.assertIn('zip_url', response.context)
        self.assertEqual(response.context['zip_file'], 'Artist_-_Album.zip')
        self.assertNotContains(response, 'Album/song1.mp3<')
        self.assertContains(response, response.context['zip_file'])
        self.assertContains(response, response.context['zip_url'])
        self.assertContains(response, 'meta http-equiv')
        zip_file = os.path.join(self.zipfile_path, response.context['zip_file'])
        self.assertEqual(os.path.exists(zip_file), True)

        with zipfile.ZipFile(zip_file, 'r') as zf:
            self.assertEqual(zf.namelist(), ['Album/song1.mp3'])

    def test_basic_album_download_with_art(self):
        """
        Test to ensure that we can generate zipfiles, with album art included.
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3', path='Album')
        self.add_art(path='Album')
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        album = Album.objects.get()

        self.assertEqual(Song.objects.count(), 1)
        song = Song.objects.get()

        response = self.client.get(reverse('exordium:albumdownload', args=(album.pk,)))
        self.assertEqual(response.status_code, 200)
        self.assertIn('filenames', response.context)
        self.assertIn('zip_file', response.context)
        self.assertIn('zip_url', response.context)
        self.assertEqual(response.context['filenames'], ['Album/song1.mp3', 'Album/cover.jpg'])
        self.assertEqual(response.context['zip_file'], 'Artist_-_Album.zip')
        self.assertContains(response, 'Album/song1.mp3<')
        self.assertContains(response, 'Album/cover.jpg<')
        self.assertContains(response, response.context['zip_file'])
        self.assertContains(response, response.context['zip_url'])
        self.assertContains(response, 'meta http-equiv')
        zip_file = os.path.join(self.zipfile_path, response.context['zip_file'])
        self.assertEqual(os.path.exists(zip_file), True)

        with zipfile.ZipFile(zip_file, 'r') as zf:
            self.assertEqual(zf.namelist(), ['Album/song1.mp3', 'Album/cover.jpg'])

    def test_basic_album_download_with_art_in_parent_dir(self):
        """
        Test to ensure that we can generate zipfiles, with album art included
        but in the parent directory.
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3', path='Artist/Album')
        self.add_art(path='Artist')
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        album = Album.objects.get()

        self.assertEqual(Song.objects.count(), 1)
        song = Song.objects.get()

        response = self.client.get(reverse('exordium:albumdownload', args=(album.pk,)))
        self.assertEqual(response.status_code, 200)
        self.assertIn('filenames', response.context)
        self.assertIn('zip_file', response.context)
        self.assertIn('zip_url', response.context)
        self.assertEqual(response.context['filenames'], ['Artist/Album/song1.mp3', 'Artist/cover.jpg'])
        self.assertEqual(response.context['zip_file'], 'Artist_-_Album.zip')
        self.assertContains(response, 'Artist/Album/song1.mp3<')
        self.assertContains(response, 'Artist/cover.jpg<')
        self.assertContains(response, response.context['zip_file'])
        self.assertContains(response, response.context['zip_url'])
        self.assertContains(response, 'meta http-equiv')
        zip_file = os.path.join(self.zipfile_path, response.context['zip_file'])
        self.assertEqual(os.path.exists(zip_file), True)

        with zipfile.ZipFile(zip_file, 'r') as zf:
            self.assertEqual(zf.namelist(), ['Artist/Album/song1.mp3', 'Artist/cover.jpg'])

    def test_miscellaneous_album_download_in_multiple_dirs(self):
        """
        Test to ensure that we can generate zipfiles for an album which is contained
        in more than one directory.  (Using a 'miscellaneous' album here but this'd
        work for any album which happens to do this)
        """
        self.add_mp3(artist='Artist', title='Title 1',
            filename='song1.mp3', path='Artist/Tracks')
        self.add_mp3(artist='Artist', title='Title 2',
            filename='song2.mp3', path='Artist/MoreTracks')
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        album = Album.objects.get()

        self.assertEqual(Song.objects.count(), 2)

        response = self.client.get(reverse('exordium:albumdownload', args=(album.pk,)))
        self.assertEqual(response.status_code, 200)
        self.assertIn('filenames', response.context)
        self.assertIn('zip_file', response.context)
        self.assertIn('zip_url', response.context)
        self.assertEqual(
            sorted(response.context['filenames']),
            sorted(['Artist/Tracks/song1.mp3', 'Artist/MoreTracks/song2.mp3'])
        )
        self.assertEqual(response.context['zip_file'], 'Artist_-_%s.zip' % (App.norm_filename(album.name)))
        self.assertContains(response, 'Artist/Tracks/song1.mp3<')
        self.assertContains(response, 'Artist/MoreTracks/song2.mp3<')
        self.assertContains(response, response.context['zip_file'])
        self.assertContains(response, response.context['zip_url'])
        self.assertContains(response, 'meta http-equiv')
        zip_file = os.path.join(self.zipfile_path, response.context['zip_file'])
        self.assertEqual(os.path.exists(zip_file), True)

        with zipfile.ZipFile(zip_file, 'r') as zf:
            self.assertEqual(
                sorted(zf.namelist()),
                sorted(['Artist/Tracks/song1.mp3', 'Artist/MoreTracks/song2.mp3'])
            )

