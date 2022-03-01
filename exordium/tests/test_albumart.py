from .base import ExordiumUserTests

from django.test import TestCase
from django.urls import reverse

import io

from PIL import Image

from exordium.models import Artist, Album, Song, App, AlbumArt

class AlbumArtTests(ExordiumUserTests):
    """
    Tests about album art specifically
    """

    def test_basic_add_album_art_gif(self):
        """
        Test a simple case where we have a gif album art.
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3')
        self.add_art(basefile='cover_400.gif', filename='cover.gif')
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        al = Album.objects.get()
        self.assertEqual(al.art_filename, 'cover.gif')
        self.assertEqual(al.art_mime, 'image/gif')
        self.assertEqual(al.art_ext, 'gif')

    def test_basic_add_album_art_png(self):
        """
        Test a simple case where we have a png album art.
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3')
        self.add_art(basefile='cover_400.png', filename='cover.png')
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        al = Album.objects.get()
        self.assertEqual(al.art_filename, 'cover.png')
        self.assertEqual(al.art_mime, 'image/png')
        self.assertEqual(al.art_ext, 'png')

    def test_basic_add_album_art_jpg(self):
        """
        Test a simple case where we have a jpg album art.
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3')
        self.add_art(basefile='cover_400.jpg', filename='cover.jpg')
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        al = Album.objects.get()
        self.assertEqual(al.art_filename, 'cover.jpg')
        self.assertEqual(al.art_mime, 'image/jpeg')
        self.assertEqual(al.art_ext, 'jpg')

    def test_basic_add_album_art_without_filesystem_permissions(self):
        """
        Test a simple case where we have album art but the filesystem
        permissions are bad.
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3')
        self.add_art(filename='cover.jpg')
        self.set_file_unreadable('cover.jpg')
        self.run_add_errors(error='found but not readable')

        self.assertEqual(Album.objects.count(), 1)
        al = Album.objects.get()
        self.assertEqual(al.has_album_art(), False)

    def test_basic_add_album_art_miscellaneous(self):
        """
        Test a case where a miscellaneous album has an image cover.  The
        image should not get loaded.
        """
        self.add_mp3(artist='Artist', title='Title 1', filename='song1.mp3')
        self.add_art()
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        al = Album.objects.get()
        self.assertEqual(al.miscellaneous, True)
        self.assertEqual(al.has_album_art(), False)
        self.assertEqual(al.art_filename, None)

    def test_basic_update_add_album_art(self):
        """
        Test a simple case where we add album art during an update,
        rather than in the add.
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3')
        self.run_add()

        self.add_art(basefile='cover_400.jpg', filename='cover.jpg')
        self.run_update()

        self.assertEqual(Album.objects.count(), 1)
        al = Album.objects.get()
        self.assertEqual(al.art_filename, 'cover.jpg')
        self.assertEqual(al.art_mime, 'image/jpeg')
        self.assertEqual(al.art_ext, 'jpg')

    def test_basic_update_add_album_art_without_filesystem_permissions(self):
        """
        Test a simple case where we add album art during an update,
        rather than in the add.  The filesystem permissions are bad
        on the cover, though.
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3')
        self.run_add()

        self.add_art(filename='cover.jpg')
        self.set_file_unreadable('cover.jpg')
        self.run_update_errors(error='found but not readable')

        self.assertEqual(Album.objects.count(), 1)
        al = Album.objects.get()
        self.assertEqual(al.has_album_art(), False)

    def test_basic_add_album_art_parent_dir(self):
        """
        Tests associating an album cover which is in the song's parent dir.
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3', path='Album')
        self.add_art(basefile='cover_400.jpg', filename='cover.jpg')
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        al = Album.objects.get()
        self.assertEqual(al.art_filename, 'cover.jpg')
        self.assertEqual(al.art_mime, 'image/jpeg')
        self.assertEqual(al.art_ext, 'jpg')

    def test_basic_add_album_art_two_dirs_up(self):
        """
        Tests associating an album cover which is two directories
        above - or in other words should NOT be found.
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3', path='Artist/Album')
        self.add_art(basefile='cover_400.jpg', filename='cover.jpg')
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        al = Album.objects.get()
        self.assertEqual(al.art_filename, None)

    def test_basic_add_album_art_mismatched_extension(self):
        """
        Tests associating an album cover which has an improper
        extension.
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3')
        self.add_art(basefile='cover_400.png', filename='cover.jpg')
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        al = Album.objects.get()
        self.assertEqual(al.art_filename, 'cover.jpg')
        self.assertEqual(al.art_mime, 'image/png')
        self.assertEqual(al.art_ext, 'png')

    def test_basic_add_album_art_invalid_file(self):
        """
        Test a cover file which isn't actually an image we support.
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3')
        self.add_art(basefile='silence-vbr.mp3', filename='cover.jpg')
        self.run_add_errors(error='cannot identify image file')

        self.assertEqual(Album.objects.count(), 1)
        al = Album.objects.get()
        self.assertEqual(al.art_filename, None)
        self.assertEqual(al.art_mime, None)
        self.assertEqual(al.art_ext, None)
        self.assertEqual(al.art_mtime, 0)

    def test_album_art_removal(self):
        """
        Tests removal of album art during an update()
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3')
        self.add_art()
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        al = Album.objects.get()
        self.assertEqual(al.art_filename, 'cover.jpg')

        self.delete_file('cover.jpg')
        self.run_update()

        self.assertEqual(Album.objects.count(), 1)
        al = Album.objects.get()
        self.assertEqual(al.art_filename, None)

    def test_non_album_art(self):
        """
        Tests what happens when there's an image alongside a non-album
        track.  The art should NOT be associated!  The special "non-album"
        albums don't get album art.
        """
        self.add_mp3(artist='Artist', title='Title 1', filename='song1.mp3')
        self.add_art()
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        al = Album.objects.get()
        self.assertEqual(al.art_filename, None)

    def test_album_art_update_no_changes(self):
        """
        Tests what happens on an update when the album art hasn't changed.
        Nothing should change in the record.
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3')
        self.add_art()
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        al = Album.objects.get()
        self.assertEqual(al.art_filename, 'cover.jpg')
        orig_mtime = al.art_mtime
        orig_filename = al.art_filename
        orig_mime = al.art_mime
        orig_ext = al.art_ext

        self.run_update()

        self.assertEqual(Album.objects.count(), 1)
        al = Album.objects.get()
        self.assertEqual(al.art_filename, 'cover.jpg')
        self.assertEqual(orig_mtime, al.art_mtime)
        self.assertEqual(orig_filename, al.art_filename)
        self.assertEqual(orig_mime, al.art_mime)
        self.assertEqual(orig_ext, al.art_ext)

    def test_album_art_update_mtime(self):
        """
        Tests what happens when an album art file is updated
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3')
        self.add_art()
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        al = Album.objects.get()
        self.assertEqual(al.art_filename, 'cover.jpg')
        orig_mtime = al.art_mtime

        self.touch_file('cover.jpg')
        self.run_update()

        self.assertEqual(Album.objects.count(), 1)
        al = Album.objects.get()
        self.assertEqual(al.art_filename, 'cover.jpg')
        self.assertNotEqual(orig_mtime, al.art_mtime)

    def test_album_art_update_different_file(self):
        """
        Tests what happens when an album art file changes filenames.
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3')
        self.add_art(filename='cover-orig.jpg')
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        al = Album.objects.get()
        self.assertEqual(al.art_filename, 'cover-orig.jpg')

        self.delete_file('cover-orig.jpg')
        self.add_art(filename='cover-new.jpg')
        self.run_update()

        self.assertEqual(Album.objects.count(), 1)
        al = Album.objects.get()
        self.assertEqual(al.art_filename, 'cover-new.jpg')

    def test_album_art_update_better_filename(self):
        """
        Tests what happens when a new album art file turns up during
        an update which we consider "better" than the one we're using.
        (ie: moving from GIF to PNG, or moving from "whatever.jpg" to
        "cover.jpg").  Nothing should happen, since the regular update
        will only do something if the mtime on the existing file changes,
        or the file disappears.
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3')
        self.add_art(filename='blah.jpg')
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        al = Album.objects.get()
        self.assertEqual(al.art_filename, 'blah.jpg')

        self.add_art(filename='cover.jpg')
        self.run_update()

        self.assertEqual(Album.objects.count(), 1)
        al = Album.objects.get()
        self.assertEqual(al.art_filename, 'blah.jpg')

    def test_album_art_update_better_filename_direct(self):
        """
        Tests what happens when a new album art file turns up during
        an update which we consider "better" than the one we're using.
        (ie: moving from GIF to PNG, or moving from "whatever.jpg" to
        "cover.jpg").  As with the previous test, we expect nothing to
        change, but instead of going through a full update we're calling
        Album.update_album_art() directly.  This shouldn't be any
        different unless we also pass in full_refresh=True to that
        function, so the album art should remain.
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3')
        self.add_art(filename='blah.jpg')
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        al = Album.objects.get()
        self.assertEqual(al.art_filename, 'blah.jpg')

        self.add_art(filename='cover.jpg')
        self.assertNoErrors(list(al.update_album_art()))

        self.assertEqual(Album.objects.count(), 1)
        al = Album.objects.get()
        self.assertEqual(al.art_filename, 'blah.jpg')

    def test_album_art_update_better_filename_forced(self):
        """
        Tests what happens when a new album art file turns up during
        an update which we consider "better" than the one we're using.
        (ie: moving from GIF to PNG, or moving from "whatever.jpg" to
        "cover.jpg").  This time we are going to simulate a force of
        that update.  Ordinarily this'll only happen direct from an
        admin page click, and is a separate action from add() and update()
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3')
        self.add_art(filename='blah.jpg')
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        al = Album.objects.get()
        self.assertEqual(al.art_filename, 'blah.jpg')

        self.add_art(filename='cover.jpg')
        self.assertNoErrors(list(al.update_album_art(full_refresh=True)))

        self.assertEqual(Album.objects.count(), 1)
        al = Album.objects.get()
        self.assertEqual(al.art_filename, 'cover.jpg')

    def test_album_art_update_miscellaneous_to_regular(self):
        """
        Testing what happens when a miscellaneous album (therefore without
        album art) is updated to be a "real" album - it should find the 
        album art present.
        """
        self.add_mp3(artist='Artist', title='Title 1',
            filename='song1.mp3')
        self.add_art()
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        al = Album.objects.get()
        self.assertEqual(al.miscellaneous, True)
        self.assertEqual(al.has_album_art(), False)

        self.update_mp3('song1.mp3', album='Album')
        self.run_update()

        self.assertEqual(Album.objects.count(), 1)
        al = Album.objects.get()
        self.assertEqual(al.miscellaneous, False)
        self.assertEqual(al.has_album_art(), True)
        self.assertEqual(al.art_filename, 'cover.jpg')

    def test_album_art_update_regular_to_miscellaneous(self):
        """
        Testing what happens when a regular album (with album art)
        is updated to be a miscellaneous album.  The album art info
        should be discarded.
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3')
        self.add_art()
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        al = Album.objects.get()
        self.assertEqual(al.miscellaneous, False)
        self.assertEqual(al.has_album_art(), True)
        self.assertEqual(al.art_filename, 'cover.jpg')

        self.update_mp3('song1.mp3', album='')
        self.run_update()

        self.assertEqual(Album.objects.count(), 1)
        al = Album.objects.get()
        self.assertEqual(al.miscellaneous, True)
        self.assertEqual(al.has_album_art(), False)
        self.assertEqual(al.art_filename, None)

    def test_album_art_move_to_different_directory(self):
        """
        Testing what happens when a regular album (with album art)
        is moved to a different directory.  The album art info
        should be moved along with it.
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3', path='Old')
        self.add_art(path='Old')
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        al = Album.objects.get()
        self.assertEqual(al.has_album_art(), True)
        self.assertEqual(al.art_filename, 'Old/cover.jpg')

        self.move_file('Old/song1.mp3', 'New')
        self.move_file('Old/cover.jpg', 'New')
        self.run_update()

        self.assertEqual(Album.objects.count(), 1)
        al = Album.objects.get()
        self.assertEqual(al.has_album_art(), True)
        self.assertEqual(al.art_filename, 'New/cover.jpg')

    def test_album_art_move_to_different_directory_and_leave_art(self):
        """
        Testing what happens when a regular album (with album art)
        is moved to a different directory, but the album art is not
        moved along with it.  In this case the album art remains where
        it is, and though it seems a bit counterintuitive, we'll permit
        the album art records to stay where they are.
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3', path='Old')
        self.add_art(path='Old')
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        al = Album.objects.get()
        self.assertEqual(al.has_album_art(), True)
        self.assertEqual(al.art_filename, 'Old/cover.jpg')

        self.move_file('Old/song1.mp3', 'New')
        self.run_update()

        self.assertEqual(Album.objects.count(), 1)
        al = Album.objects.get()
        self.assertEqual(al.has_album_art(), True)
        self.assertEqual(al.art_filename, 'Old/cover.jpg')

    def test_album_art_move_to_different_directory_and_remove_art(self):
        """
        Testing what happens when a regular album (with album art)
        is moved to a different directory, but the album art is
        deleted.  In this case the album art info should be removed.
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3', path='Old')
        self.add_art(path='Old')
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        al = Album.objects.get()
        self.assertEqual(al.has_album_art(), True)
        self.assertEqual(al.art_filename, 'Old/cover.jpg')

        self.move_file('Old/song1.mp3', 'New')
        self.delete_file('Old/cover.jpg')
        self.run_update()

        self.assertEqual(Album.objects.count(), 1)
        al = Album.objects.get()
        self.assertEqual(al.has_album_art(), False)
        self.assertEqual(al.art_filename, None)

    def test_album_art_view_retrieve_original_jpg(self):
        """
        Test retrieval of the fullsize cover art from a URL
        """
        self.longMessage = False

        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3')
        self.add_art(basefile='cover_400.jpg', filename='cover.jpg')
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        al = Album.objects.get()
        url = reverse('exordium:origalbumart', args=(al.pk, al.art_ext))
        response = self.client.get(url)
        filedata = self.get_file_contents('cover.jpg')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/jpeg')
        self.assertEqual(response.content, filedata, 'File data differs')

    def test_album_art_view_retrieve_original_gif(self):
        """
        Test retrieval of the fullsize cover art from a URL
        """
        self.longMessage = False

        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3')
        self.add_art(basefile='cover_400.gif', filename='cover.gif')
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        al = Album.objects.get()
        url = reverse('exordium:origalbumart', args=(al.pk, al.art_ext))
        response = self.client.get(url)
        filedata = self.get_file_contents('cover.gif')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/gif')
        self.assertEqual(response.content, filedata, 'File data differs')

    def test_album_art_view_retrieve_original_png(self):
        """
        Test retrieval of the fullsize cover art from a URL
        """
        self.longMessage = False

        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3')
        self.add_art(basefile='cover_400.png', filename='cover.png')
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        al = Album.objects.get()
        url = reverse('exordium:origalbumart', args=(al.pk, al.art_ext))
        response = self.client.get(url)
        filedata = self.get_file_contents('cover.png')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/png')
        self.assertEqual(response.content, filedata, 'File data differs')

    def test_album_art_view_retrieve_original_no_cover(self):
        """
        Test retrieval of the fullsize cover art from a URL, when we don't
        actually have an image to return.  Should throw a 404 (our "no
        album art found" graphic is displayed via templates, not code)
        """
        self.longMessage = False

        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3')
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        al = Album.objects.get()
        self.assertEqual(al.art_filename, None)
        url = reverse('exordium:origalbumart', args=(al.pk, 'jpg'))
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)

    def test_album_art_view_retrieve_original_extension_mismatch(self):
        """
        Test retrieval of the fullsize cover art from a URL, with
        a mismatched extension on the original filename
        """
        self.longMessage = False

        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3')
        self.add_art(basefile='cover_400.jpg', filename='cover.png')
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        al = Album.objects.get()
        url = reverse('exordium:origalbumart', args=(al.pk, al.art_ext))
        response = self.client.get(url)
        filedata = self.get_file_contents('cover.png')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/jpeg')
        self.assertEqual(response.content, filedata, 'File data differs')

    def test_album_art_generate_album_thumb(self):
        """
        Test the creation of an album-sized thumbnail for our art
        """
        self.longMessage = False

        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3')
        self.add_art()
        self.run_add()

        size = AlbumArt.SZ_ALBUM
        resolution = AlbumArt.resolutions[size]

        self.assertEqual(Album.objects.count(), 1)
        al = Album.objects.get()
        url = reverse('exordium:albumart', args=(al.pk, size))
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/jpeg')

        data = io.BytesIO(response.content)
        im = Image.open(data)
        self.assertEqual(im.width, resolution)
        self.assertEqual(im.height, resolution)

        data.seek(0)
        self.assertEqual(AlbumArt.objects.count(), 1)
        art = AlbumArt.objects.get(album=al, size=size)
        self.assertEqual(art.resolution, resolution)
        self.assertEqual(art.from_mtime, al.art_mtime)
        self.assertEqual(bytes(art.image), data.read())

        # Test our get_artist() method, for coverage.py
        ar = Artist.objects.get(name='Artist')
        self.assertEqual(art.get_artist(), ar)

    def test_album_art_generate_album_thumb_twice(self):
        """
        Test the creation of an album-sized thumbnail for our art,
        and call twice.  Mostly just to increase some coverage via
        coverage.py, to ensure we're hitting the bit which returns
        and existing object.
        """
        self.longMessage = False

        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3')
        self.add_art()
        self.run_add()

        size = AlbumArt.SZ_ALBUM
        resolution = AlbumArt.resolutions[size]

        self.assertEqual(Album.objects.count(), 1)
        al = Album.objects.get()
        url = reverse('exordium:albumart', args=(al.pk, size))
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/jpeg')

        data = io.BytesIO(response.content)
        im = Image.open(data)
        self.assertEqual(im.width, resolution)
        self.assertEqual(im.height, resolution)

        data.seek(0)
        self.assertEqual(AlbumArt.objects.count(), 1)
        art = AlbumArt.objects.get(album=al, size=size)
        art_pk = art.pk
        self.assertEqual(art.resolution, resolution)
        self.assertEqual(art.from_mtime, al.art_mtime)
        self.assertEqual(bytes(art.image), data.read())

        # Now the second request - may as well do all the same checks
        # one more time.
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/jpeg')

        data = io.BytesIO(response.content)
        im = Image.open(data)
        self.assertEqual(im.width, resolution)
        self.assertEqual(im.height, resolution)

        data.seek(0)
        self.assertEqual(AlbumArt.objects.count(), 1)
        art = AlbumArt.objects.get(album=al, size=size)
        self.assertEqual(art.pk, art_pk)
        self.assertEqual(art.resolution, resolution)
        self.assertEqual(art.from_mtime, al.art_mtime)
        self.assertEqual(bytes(art.image), data.read())

    def test_album_art_generate_album_thumb_gif(self):
        """
        Test the creation of an album-sized thumbnail for our art,
        using a GIF instead of JPG.
        """
        self.longMessage = False

        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3')
        self.add_art(basefile='cover_400.gif', filename='cover.gif')
        self.run_add()

        size = AlbumArt.SZ_ALBUM
        resolution = AlbumArt.resolutions[size]

        self.assertEqual(Album.objects.count(), 1)
        al = Album.objects.get()
        url = reverse('exordium:albumart', args=(al.pk, size))
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/jpeg')

        data = io.BytesIO(response.content)
        im = Image.open(data)
        self.assertEqual(im.width, resolution)
        self.assertEqual(im.height, resolution)

        data.seek(0)
        self.assertEqual(AlbumArt.objects.count(), 1)
        art = AlbumArt.objects.get(album=al, size=size)
        self.assertEqual(art.resolution, resolution)
        self.assertEqual(art.from_mtime, al.art_mtime)
        self.assertEqual(bytes(art.image), data.read())

    def test_album_art_generate_album_thumb_png(self):
        """
        Test the creation of an album-sized thumbnail for our art,
        using a PNG instead of JPG.
        """
        self.longMessage = False

        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3')
        self.add_art(basefile='cover_400.png', filename='cover.png')
        self.run_add()

        size = AlbumArt.SZ_ALBUM
        resolution = AlbumArt.resolutions[size]

        self.assertEqual(Album.objects.count(), 1)
        al = Album.objects.get()
        url = reverse('exordium:albumart', args=(al.pk, size))
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/jpeg')

        data = io.BytesIO(response.content)
        im = Image.open(data)
        self.assertEqual(im.width, resolution)
        self.assertEqual(im.height, resolution)

        data.seek(0)
        self.assertEqual(AlbumArt.objects.count(), 1)
        art = AlbumArt.objects.get(album=al, size=size)
        self.assertEqual(art.resolution, resolution)
        self.assertEqual(art.from_mtime, al.art_mtime)
        self.assertEqual(bytes(art.image), data.read())

    def test_album_art_generate_list_thumb(self):
        """
        Test the creation of a list-sized thumbnail for our art
        """
        self.longMessage = False

        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3')
        self.add_art()
        self.run_add()

        size = AlbumArt.SZ_LIST
        resolution = AlbumArt.resolutions[size]

        self.assertEqual(Album.objects.count(), 1)
        al = Album.objects.get()
        url = reverse('exordium:albumart', args=(al.pk, size))
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/jpeg')

        data = io.BytesIO(response.content)
        im = Image.open(data)
        self.assertEqual(im.width, resolution)
        self.assertEqual(im.height, resolution)

        data.seek(0)
        self.assertEqual(AlbumArt.objects.count(), 1)
        art = AlbumArt.objects.get(album=al, size=size)
        self.assertEqual(art.resolution, resolution)
        self.assertEqual(art.from_mtime, al.art_mtime)
        self.assertEqual(bytes(art.image), data.read())

    def test_album_art_attempt_invalid_thumb_generation(self):
        """
        Test the creation of an album art thumbnail for a type of
        thumbnail we don't actually support.  Should generate a 404.
        """

        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3')
        self.add_art()
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        al = Album.objects.get()
        self.assertEqual(al.art_filename, 'cover.jpg')
        url = reverse('exordium:albumart', args=(al.pk, 'foobar'))
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(AlbumArt.objects.count(), 0)

    def test_album_art_model_get_or_create_invalid_size(self):
        """
        Test the creation of an album art thumbnail for a type of
        thumbnail we don't actually support.  This time going after the
        actual model method which does the work.  In reality it couldn't
        get this far because we've already checked, but just in case
        we'll make sure we have this test here as well.
        """

        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3')
        self.add_art()
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        al = Album.objects.get()
        self.assertEqual(al.art_filename, 'cover.jpg')
        self.assertEqual(AlbumArt.get_or_create(al, 'foobar'), None)
        self.assertEqual(AlbumArt.objects.count(), 0)

    def test_album_art_attempt_unknown_album_thumb_retrieval(self):
        """
        Test the retrieval of an album art thumbnail for an album
        which doesn't exist.  Should generate a 404.
        """
        self.assertEqual(Album.objects.count(), 0)
        url = reverse('exordium:albumart', args=(42, AlbumArt.SZ_ALBUM))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(AlbumArt.objects.count(), 0)

    def test_album_art_attempt_album_thumb_generation_without_art(self):
        """
        Test the creation of an album art thumbnail for an album which
        doesn't have album art.  Will throw a 404.  (Our "no album art
        found" graphic is shown via templates, not code.)
        """

        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3')
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        al = Album.objects.get()
        self.assertEqual(al.art_filename, None)
        url = reverse('exordium:albumart', args=(al.pk, AlbumArt.SZ_ALBUM))
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)

    def test_album_art_resolution_preset_change(self):
        """
        Test what happens when we have an thumbnail but then our
        preset resolution size changes.  The thumbnail should get
        regenerated when it's re-requested.
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3')
        self.add_art()
        self.run_add()

        size = AlbumArt.SZ_ALBUM
        resolution = AlbumArt.resolutions[size]

        self.assertEqual(Album.objects.count(), 1)
        al = Album.objects.get()
        self.assertEqual(al.art_filename, 'cover.jpg')

        url = reverse('exordium:albumart', args=(al.pk, size))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/jpeg')

        orig_data = io.BytesIO(response.content)
        im = Image.open(orig_data)
        self.assertEqual(im.width, resolution)
        self.assertEqual(im.height, resolution)

        self.assertEqual(AlbumArt.objects.count(), 1)
        art = AlbumArt.objects.get()
        self.assertEqual(art.resolution, resolution)
        art_pk = art.pk

        AlbumArt.resolutions[size] = resolution - 50
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/jpeg')

        new_data = io.BytesIO(response.content)
        im = Image.open(new_data)
        self.assertEqual(im.width, resolution - 50)
        self.assertEqual(im.height, resolution - 50)

        orig_data.seek(0)
        new_data.seek(0)
        self.assertNotEqual(orig_data, new_data)

        self.assertEqual(AlbumArt.objects.count(), 1)
        art = AlbumArt.objects.get(album=al, size=size)
        self.assertEqual(art.resolution, resolution - 50)
        self.assertNotEqual(art_pk, art.pk)

        # Reset the resolutions dict, though we also do this in
        # the test tearDown, in case our test fails before we
        # get here.
        AlbumArt.resolutions[size] = resolution

    def test_album_art_get_art_after_file_deletion(self):
        """
        Test what happens when we have album art but the file is
        deleted before we get a chance to request one of the
        thumbnails.  The album art should get removed and we
        should get no art back.
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3')
        self.add_art()
        self.run_add()

        self.delete_file('cover.jpg')

        size = AlbumArt.SZ_ALBUM
        resolution = AlbumArt.resolutions[size]

        self.assertEqual(Album.objects.count(), 1)
        al = Album.objects.get()
        self.assertEqual(al.has_album_art(), True)
        self.assertEqual(al.art_filename, 'cover.jpg')

        url = reverse('exordium:albumart', args=(al.pk, size))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

        # Get the album again and run some tests
        al = Album.objects.get()
        self.assertEqual(al.has_album_art(), False)
        self.assertEqual(al.art_filename, None)

    def test_album_art_update_after_source_update(self):
        """
        Test what happens when we have an thumbnail but then our
        preset resolution size changes.  The thumbnail should get
        regenerated when it's re-requested.
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3')
        self.add_art()
        self.run_add()

        size = AlbumArt.SZ_ALBUM
        resolution = AlbumArt.resolutions[size]

        self.assertEqual(Album.objects.count(), 1)
        al = Album.objects.get()
        self.assertEqual(al.art_filename, 'cover.jpg')

        url = reverse('exordium:albumart', args=(al.pk, size))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/jpeg')

        orig_data = io.BytesIO(response.content)
        im = Image.open(orig_data)
        self.assertEqual(im.width, resolution)
        self.assertEqual(im.height, resolution)

        self.assertEqual(AlbumArt.objects.count(), 1)
        art = AlbumArt.objects.get()
        self.assertEqual(art.resolution, resolution)
        art_pk = art.pk

        self.touch_file('cover.jpg')
        self.run_update()

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/jpeg')

        new_data = io.BytesIO(response.content)
        im = Image.open(new_data)
        self.assertEqual(im.width, resolution)
        self.assertEqual(im.height, resolution)

        orig_data.seek(0)
        new_data.seek(0)
        self.assertNotEqual(orig_data, new_data)

        self.assertEqual(AlbumArt.objects.count(), 1)
        art = AlbumArt.objects.get(album=al, size=size)
        self.assertEqual(art.resolution, resolution)
        self.assertNotEqual(art_pk, art.pk)

    def test_admin_update_without_permission(self):
        """
        Test an admin album art update when we're not actually logged in.
        """

        url = reverse('exordium:albumartupdate', args=(42,))
        response = self.client.get(url)
        self.assertRedirects(response, '%s?next=%s' % (reverse('admin:login'), url))

    def test_admin_update_invalid_album(self):
        """
        Test an admin album art update for an invalid album ID
        """

        self.login()
        response = self.client.get(reverse('exordium:albumartupdate', args=(42,)))
        self.assertEqual(response.status_code, 404)

    def test_admin_update_no_change(self):
        """
        Test an admin album art update for an album which doesn't actually change.
        """

        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3')
        self.add_art()
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        al = Album.objects.get()
        self.assertEqual(al.art_filename, 'cover.jpg')
        orig_mtime = al.art_mtime
        orig_filename = al.art_filename
        orig_mime = al.art_mime
        orig_ext = al.art_ext

        self.login()
        response = self.client.get(reverse('exordium:albumartupdate', args=(al.pk,)))
        self.assertRedirects(response, reverse('exordium:album', args=(al.pk,)))

        self.assertEqual(Album.objects.count(), 1)
        al = Album.objects.get()
        self.assertEqual(al.art_filename, 'cover.jpg')
        self.assertEqual(orig_mtime, al.art_mtime)
        self.assertEqual(orig_filename, al.art_filename)
        self.assertEqual(orig_mime, al.art_mime)
        self.assertEqual(orig_ext, al.art_ext)

    def test_admin_update_better_filename(self):
        """
        Tests what happens when an update sees a "better" cover filename.
        Our admin update should pick up on it.
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3')
        self.add_art(filename='blah.jpg')
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        al = Album.objects.get()
        self.assertEqual(al.art_filename, 'blah.jpg')

        self.add_art(filename='cover.jpg')

        self.login()
        response = self.client.get(reverse('exordium:albumartupdate', args=(al.pk,)))
        self.assertRedirects(response, reverse('exordium:album', args=(al.pk,)))

        self.assertEqual(Album.objects.count(), 1)
        al = Album.objects.get()
        self.assertEqual(al.art_filename, 'cover.jpg')

    def test_admin_update_file_permissions_wrong_no_initial_art(self):
        """
        Test an admin album art update in which the new album art file
        isn't actually readable.  (When the album did not have art,
        initially.)
        """

        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3')
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        al = Album.objects.get()
        self.assertEqual(al.has_album_art(), False)

        self.add_art(filename='cover.jpg')
        self.set_file_unreadable('cover.jpg')

        self.login()
        response = self.client.get(reverse('exordium:albumartupdate', args=(al.pk,)))
        self.assertRedirects(response, reverse('exordium:album', args=(al.pk,)),
            fetch_redirect_response=False)

        self.assertEqual(Album.objects.count(), 1)
        al = Album.objects.get()
        self.assertEqual(al.has_album_art(), False)

        # Check the next page to ensure we got an error message
        response = self.client.get(reverse('exordium:album', args=(al.pk,)))
        self.assertContains(response, 'found but not readable')

    def test_admin_update_no_change_with_initial_art(self):
        """
        Test an admin album art update for an album which doesn't actually change.
        In this scenario we did have art for the album initially.
        """

        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3')
        self.add_art(filename='cover.jpg')
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        al = Album.objects.get()
        self.assertEqual(al.art_filename, 'cover.jpg')
        orig_mtime = al.art_mtime
        orig_filename = al.art_filename
        orig_mime = al.art_mime
        orig_ext = al.art_ext

        self.set_file_unreadable('cover.jpg')

        self.login()
        response = self.client.get(reverse('exordium:albumartupdate', args=(al.pk,)))
        self.assertRedirects(response, reverse('exordium:album', args=(al.pk,)),
            fetch_redirect_response=False)

        self.assertEqual(Album.objects.count(), 1)
        al = Album.objects.get()
        self.assertEqual(al.art_filename, 'cover.jpg')
        self.assertEqual(orig_mtime, al.art_mtime)
        self.assertEqual(orig_filename, al.art_filename)
        self.assertEqual(orig_mime, al.art_mime)
        self.assertEqual(orig_ext, al.art_ext)

        # Check the next page to ensure we got an error message
        response = self.client.get(reverse('exordium:album', args=(al.pk,)))
        self.assertContains(response, 'found but not readable')

    def test_model_get_album_image_miscellaneous(self):
        """
        Ensure that Album.get_album_image() returns None when the album is
        set to miscellaneous, regardless of if an album image is set.  This
        can currently never actually happen in the app because we do that
        check as soon as possible, but we'll check the method here, regardless.
        """
        self.add_mp3(artist='Artist', title='Title 1',
            filename='song1.mp3')
        self.add_art(filename='cover.jpg')
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        al = Album.objects.get()
        self.assertEqual(al.miscellaneous, True)
        self.assertEqual(al.has_album_art(), False)
        self.assertEqual(al.get_album_image(), None)

        # Just for fun, pretend some album info made it into the database
        # somehow and ensure that our call still returns None.
        al.art_filename = 'cover.jpg'
        al.art_mime = 'media/jpeg'
        al.art_ext = 'jpg'
        al.art_mtime = 0
        al.save()

        self.assertEqual(al.has_album_art(), True)
        self.assertEqual(al.get_album_image(), None)

    def test_model_get_album_image_no_tracks(self):
        """
        Ensure that Album.get_album_image() returns None when we encounter an
        album with no tracks.  This shouldn't be possible under ordinary
        operation, but check for it anyway.  We will manually inject into the
        database to simulate this.
        """
        ar = Artist.objects.create(name='Artist', normname='artist')
        al = Album.objects.create(
            artist = ar,
            name = 'Album',
            normname = 'album',
            art_filename = 'cover.jpg',
            art_ext = 'jpg',
            art_mime = 'media/jpeg',
            art_mtime = 0,
        )

        self.assertEqual(al.has_album_art(), True)
        self.assertEqual(al.get_album_image(), None)

    def test_model_update_album_art_miscellaneous(self):
        """
        Ensure that ``Album.update_album_art()`` does nothing when the album is
        set to miscellaneous.  I'm pretty sure this can't ever actually happen
        in real life due to checks which occur prior to calling this, but
        we're checking here regardless.  We're passing ``full_refresh=True``
        to the procedure to ensure that we get right to the main bit.
        """
        self.add_mp3(artist='Artist', title='Title 1',
            filename='song1.mp3')
        self.add_art(filename='cover.jpg')
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        al = Album.objects.get()
        self.assertEqual(al.miscellaneous, True)
        self.assertEqual(al.has_album_art(), False)
        self.assertEqual(list(al.update_album_art(full_refresh=True)), [])
        self.assertEqual(al.get_album_image(), None)
        self.assertEqual(al.art_filename, None)
        self.assertEqual(al.art_ext, None)
        self.assertEqual(al.art_mime, None)
        self.assertEqual(al.art_mtime, 0)

    def test_model_import_album_image_from_filename_miscellaneous(self):
        """
        Ensure that Album.import_album_image_from_filename() does nothing
        when the album is set to miscellaneous.  This can currently
        never actually happen in the app because we do that check as soon
        as possible, but we'll check the method here, regardless.
        """
        self.add_mp3(artist='Artist', title='Title 1',
            filename='song1.mp3')
        self.add_art(filename='cover.jpg')
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        al = Album.objects.get()
        self.assertEqual(al.miscellaneous, True)
        self.assertEqual(al.has_album_art(), False)
        self.assertEqual(list(al.import_album_image_from_filename('cover.jpg', 'cover.jpg')), [])
        self.assertEqual(al.has_album_art(), False)
        self.assertEqual(al.art_filename, None)
        self.assertEqual(al.art_ext, None)
        self.assertEqual(al.art_mime, None)
        self.assertEqual(al.art_mtime, 0)

    def test_model_import_album_image_from_filename_invalid_extension(self):
        """
        Ensure that Album.import_album_image_from_filename() produces
        an error when the passed-in filename is of an invalid extension.
        This can currently never actually happen in the app because we do
        that check as soon as possible, but we'll check the method here,
        regardless.
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3')
        self.add_art(filename='cover.pdf')
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        al = Album.objects.get()
        self.assertEqual(al.has_album_art(), False)
        self.assertErrors(list(al.import_album_image_from_filename('cover.pdf', 'cover.pdf')),
            error='Invalid extension for image')

    def test_add_image_with_invalid_internal_type(self):
        """
        Here we try importing album art which has a valid extension but is
        in reality a .tif file.
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3')
        self.add_art(filename='cover.jpg', basefile='cover_400.tif')
        self.run_add_errors(error='Unknown image type found')

        self.assertEqual(Album.objects.count(), 1)
        al = Album.objects.get()
        self.assertEqual(al.has_album_art(), False)

class BasicAlbumArtTests(TestCase):
    """
    Album art related tests which don't actually require our full
    fake library test setup, since they don't use add() or update().
    """

    def test_album_art_ordering(self):
        """
        Various tests for finding out if our album art preference sorting
        works how we hope.
        """
        order_tests = [
                (['cover.gif', 'cover.png'], ['cover.png', 'cover.gif']),
                (['cover.jpg', 'cover.png'], ['cover.png', 'cover.jpg']),
                (['cover-back.jpg', 'cover.jpg'], ['cover.jpg', 'cover-back.jpg']),
                (['cover-back.png', 'cover.jpg'], ['cover.jpg', 'cover-back.png']),
                (['cover-test.png', 'cover.gif'], ['cover.gif', 'cover-test.png']),
                (['other.png', 'cover.gif'], ['cover.gif', 'other.png']),
                (['other.png', 'cover-back.jpg'], ['cover-back.jpg', 'other.png']),
                (['cover-back.gif', 'cover-back.jpg'], ['cover-back.jpg', 'cover-back.gif']),
                (['cover-back.jpg', 'cover-back.png'], ['cover-back.png', 'cover-back.jpg']),
                (['zzz.jpg', 'aaa.jpg'], ['aaa.jpg', 'zzz.jpg']),
                (['zzz.png', 'aaa.jpg'], ['zzz.png', 'aaa.jpg']),
                (['foo.mp3', 'cover.png'], ['cover.png']),
                (['foo.mp3', 'cover.png', 'bar.txt'], ['cover.png']),
                (['foo.mp3', 'baz.gif', 'bar.txt'], ['baz.gif']),
                (['foo.mp3', 'baz.gif', 'bar.txt', 'frobozz.png'], ['frobozz.png', 'baz.gif']),
                (['foo.mp3', 'baz.aiff', 'bar.txt', 'frobozz.ogg'], []),
            ]

        # Loop through and test!
        for (before, after) in order_tests:
            self.assertEqual(App.get_cover_images(before), after)

