from django.test import TestCase

from exordium.models import Artist, Album, Song, App, AlbumArt

class AppModelTests(TestCase):
    """
    Tests against our main App class which don't require our full
    fake library setup.
    """

    def test_ensure_various_artists_create_artist(self):
        """
        Test our App.ensure_various_artists() function and ensure that
        it creates a Various artist if needed.
        """
        self.assertEqual(Artist.objects.count(), 0)
        self.assertEqual(App.ensure_various_artists(), True)
        self.assertEqual(Artist.objects.count(), 1)
        ar = Artist.objects.get()
        self.assertEqual(ar.name, 'Various')
        self.assertEqual(ar.various, True)

    def test_ensure_various_artists_return_existing(self):
        """
        Test our App.ensure_various_artists() function and ensure that
        it returns an existing 'Various' artist if one exists.
        """
        App.ensure_various_artists()
        self.assertEqual(Artist.objects.count(), 1)
        ar = Artist.objects.get()
        ar_pk = ar.pk
        self.assertEqual(ar.name, 'Various')
        self.assertEqual(ar.various, True)

        self.assertEqual(App.ensure_various_artists(), False)
        ar = Artist.objects.get()
        self.assertEqual(ar.pk, ar_pk)
        self.assertEqual(ar.name, 'Various')
        self.assertEqual(ar.various, True)

    def test_add_with_empty_to_add_list(self):
        """
        Test what happens when we run ``App.add()`` with an empty to_add
        list.  Calling this method with a list only happens inside
        ``App.update()``, and that method checks for an empty list before
        calling, so this should never actually happen in "real life,"
        but we'll check it anyway.
        """
        retlines = list(App.add([]))
        self.assertEqual(retlines, [])
        self.assertEqual(Artist.objects.count(), 0)
        self.assertEqual(Album.objects.count(), 0)
        self.assertEqual(Song.objects.count(), 0)

