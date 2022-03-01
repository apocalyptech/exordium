from .base import ExordiumUserTests

from django.urls import reverse

from exordium.models import Artist, Album, Song, App, AlbumArt

class LibraryUpdateViewTests(ExordiumUserTests):
    """
    Testing of our library update view.  All we're really checking here
    is that the update process takes place - all the actual add/update
    functionality is tested in BasicUpdateTests.
    """

    def get_content(self, streaming_content):
        """
        Take an iterable streaming_content and return a block of text.
        """
        contents = []
        for line in streaming_content:
            contents.append(str(line))
        return "\n".join(contents)

    def test_without_permission(self):
        """
        Test when we're not actually logged in.
        """

        url = reverse('exordium:library_update')
        response = self.client.get(url)
        self.assertRedirects(response, '%s?next=%s' % (reverse('admin:login'), url))

    def test_with_permission(self):
        """
        Test when we're logged in - make sure an add actually happens.
        """

        self.longMessage = False

        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3')

        self.login()
        response = self.client.get(reverse('exordium:library_update'), {'type': 'add'})
        self.assertEqual(response.status_code, 200)
        # Since LibraryAddView returns a StreamingHttpResponse, we need to
        # iterate through it for anything to actually happen.
        content = self.get_content(response.streaming_content)
        self.assertNotIn('Showing debug output', content,
            msg='Debug output found where it should not be')

        self.assertEqual(Artist.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Song.objects.count(), 1)

    def test_update_with_permission(self):
        """
        Test when we're logged in - make sure an update actually happens.
        """

        self.longMessage = False

        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3')
        self.run_add()

        self.update_mp3(filename='song1.mp3', title='New Title')

        self.login()
        response = self.client.get(reverse('exordium:library_update'), {'type': 'update'})
        self.assertEqual(response.status_code, 200)
        # Since LibraryAddView returns a StreamingHttpResponse, we need to
        # iterate through it for anything to actually happen.
        content = self.get_content(response.streaming_content)
        self.assertNotIn('Showing debug output', content,
            msg='Debug output found where it should not be')

        self.assertEqual(Artist.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Song.objects.count(), 1)

        song = Song.objects.get()
        self.assertEqual(song.title, 'New Title')

    def test_no_querystring(self):
        """
        Test what happens when we don't have any querystring.  We should be
        redirected back to the library page with an error.
        """

        self.login()
        response = self.client.get(reverse('exordium:library_update'))
        self.assertRedirects(response, reverse('exordium:library'),
            fetch_redirect_response=False)

        response = self.client.get(reverse('exordium:library'))
        self.assertContains(response, 'No update type specified')

    def test_invalid_type(self):
        """
        Test what happens when we pass in an invalid update type.  Should be
        redirected back to the library page with an error.
        """

        self.login()
        response = self.client.get(reverse('exordium:library_update'), {'type': 'foo'})
        self.assertRedirects(response, reverse('exordium:library'),
            fetch_redirect_response=False)

        response = self.client.get(reverse('exordium:library'))
        self.assertContains(response, 'Invalid update type specified')

    def test_debug_checkbox_add(self):
        """
        Test the debug checkbox being active.  Should give us a note about including
        debug output.  (Though we don't really check for the actual debug output
        at the moment.)
        """

        self.longMessage = False

        self.login()
        response = self.client.get(reverse('exordium:library_update'),
            {'type': 'add', 'debug': 'yes'})
        self.assertEqual(response.status_code, 200)
        # Since LibraryAddView returns a StreamingHttpResponse, we need to
        # iterate through it for anything to actually happen.
        content = self.get_content(response.streaming_content)

        self.assertIn('Showing debug output', content, msg='Debug output not found')

    def test_debug_checkbox_update(self):
        """
        Test the debug checkbox being active.  Should give us a note about including
        debug output.  (Though we don't really check for the actual debug output
        at the moment.)
        """

        self.longMessage = False

        self.login()
        response = self.client.get(reverse('exordium:library_update'),
            {'type': 'update', 'debug': 'yes'})
        self.assertEqual(response.status_code, 200)
        # Since LibraryAddView returns a StreamingHttpResponse, we need to
        # iterate through it for anything to actually happen.
        content = self.get_content(response.streaming_content)

        self.assertIn('Showing debug output', content, msg='Debug output not found')

