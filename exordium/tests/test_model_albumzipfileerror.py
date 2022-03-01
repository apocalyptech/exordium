from django.test import TestCase

from exordium.models import Artist, Album, Song, App, AlbumArt

class AlbumZipfileErrorModelTests(TestCase):
    """
    Tests for our App.AlbumZipfileError exception, since we don't have
    a way to legitimately generating one of those.  Mostly just checking
    that the stored exception works all right.
    """

    def test_orig_exception(self):
        """
        Tests that our orig_exception attribute works as-expected
        """
        with self.assertRaises(App.AlbumZipfileError) as cm:
            try:
                a = int('a')
            except ValueError as e:
                raise App.AlbumZipfileError(e)
        self.assertEqual(type(cm.exception.orig_exception), type(ValueError()))

