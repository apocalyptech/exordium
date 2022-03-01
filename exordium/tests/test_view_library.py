from .base import ExordiumUserTests

from django.urls import reverse

from exordium.models import Artist, Album, Song, App, AlbumArt

class LibraryViewTests(ExordiumUserTests):
    """
    Tests for our main library view index.  Not a whole lot here, honestly.
    I'm not bothering to test the aggregate information shown here, alas.
    """

    def test_without_permission(self):
        """
        Test when we're not actually logged in.
        """

        url = reverse('exordium:library')
        response = self.client.get(url)
        self.assertRedirects(response, '%s?next=%s' % (reverse('admin:login'), url))

    def test_with_permission(self):
        """
        Test when we're logged in.
        """

        self.login()
        response = self.client.get(reverse('exordium:library'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse('exordium:library_update'))

        # We should show our library config, and not have zipfile info
        App.ensure_prefs()
        self.assertContains(response, App.prefs['exordium__base_path'])
        self.assertContains(response, App.prefs['exordium__media_url_html5'])
        self.assertContains(response, App.prefs['exordium__media_url_m3u'])
        self.assertNotContains(response, 'Zipfile Support:</strong> Yes')
        self.assertContains(response, 'Zipfile Support:</strong> No')

