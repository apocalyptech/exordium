from django.test import TestCase
from django.urls import reverse

from exordium.models import Artist, Album, Song, App, AlbumArt
from exordium.views import add_session_success, add_session_fail, add_session_msg

class SessionViewTests(TestCase):
    """
    Tests dealing with the session variables we set (for success/fail messages).
    Mostly this isn't really necessary since they're tested "by accident" in a
    number of other tests, but we'll explicitly run a couple tests here and
    slightly increase our coverage to boot.
    """

    def setUp(self):
        """
        All of these tests will require a valid session, so we need to request
        a page.
        """
        self.initial_response = self.client.get(reverse('exordium:index'))

    def test_add_success_message(self):
        """
        Add a success message.
        """
        add_session_success(self.initial_response.wsgi_request, 'Success')
        self.assertIn('exordium_msg_success', self.initial_response.wsgi_request.session)
        self.assertEqual(self.initial_response.wsgi_request.session['exordium_msg_success'], ['Success'])

    def test_add_two_success_messages(self):
        """
        Adds two success messages.
        """
        add_session_success(self.initial_response.wsgi_request, 'Success')
        self.assertIn('exordium_msg_success', self.initial_response.wsgi_request.session)
        self.assertEqual(self.initial_response.wsgi_request.session['exordium_msg_success'], ['Success'])

        add_session_success(self.initial_response.wsgi_request, 'Two')
        self.assertIn('exordium_msg_success', self.initial_response.wsgi_request.session)
        self.assertEqual(self.initial_response.wsgi_request.session['exordium_msg_success'], ['Success', 'Two'])

    def test_add_fail_message(self):
        """
        Add a fail message.
        """
        add_session_fail(self.initial_response.wsgi_request, 'Fail')
        self.assertIn('exordium_msg_fail', self.initial_response.wsgi_request.session)
        self.assertEqual(self.initial_response.wsgi_request.session['exordium_msg_fail'], ['Fail'])

    def test_add_two_fail_messages(self):
        """
        Adds two fail messages.
        """
        add_session_fail(self.initial_response.wsgi_request, 'Fail')
        self.assertIn('exordium_msg_fail', self.initial_response.wsgi_request.session)
        self.assertEqual(self.initial_response.wsgi_request.session['exordium_msg_fail'], ['Fail'])

        add_session_fail(self.initial_response.wsgi_request, 'Two')
        self.assertIn('exordium_msg_fail', self.initial_response.wsgi_request.session)
        self.assertEqual(self.initial_response.wsgi_request.session['exordium_msg_fail'], ['Fail', 'Two'])

    def test_add_invalid_message(self):
        """
        Add an invalid message type (should just silently ignore it)
        """
        initial_session_keys = sorted(self.initial_response.wsgi_request.session.keys())
        add_session_msg(self.initial_response.wsgi_request, 'Invalid', 'invalid')
        self.assertNotIn('exordium_msg_invalid', self.initial_response.wsgi_request.session)
        self.assertEqual(initial_session_keys, sorted(self.initial_response.wsgi_request.session.keys()))

