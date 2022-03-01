from .base import ExordiumUserTests

from django.urls import reverse

from exordium.models import Artist, Album, Song, App, AlbumArt
from exordium.views import UserAwareView, IndexView

# TODO: Really we should convert our preference form to a django.form.Form
# and test the full submission, rather than just faking a POST.
class UserPreferenceTests(ExordiumUserTests):
    """
    Tests of our user-based preferences, which for the purpose of this
    class are View-dependent, because if we are a logged-in user they
    should be stored in our actual user preferences DB-or-whatever (via
    our third party django-dynamic-preferences, but if we're AnonymousUser,
    it should just be stored in our session.
    """

    def test_show_live_anonymous(self):
        """
        Test the behavior when we're anonymous.  Should be stored just
        in the session.
        """

        # First up - our default show_live should be None
        response = self.client.get(reverse('exordium:index'))
        self.assertEqual(UserAwareView.get_preference_static(response.wsgi_request, 'show_live'), None)
        self.assertNotIn('exordium__show_live', response.wsgi_request.session)

        # Check to make sure our checkbox is in the state we expect
        self.assertNotContains(response, '"show_live" checked')

        # Next: submit our preferences form to enable show_live.
        response = self.client.post(reverse('exordium:updateprefs'), {'show_live': 'yes'})
        self.assertRedirects(response, reverse('exordium:index'), fetch_redirect_response=False)
        response = self.client.get(reverse('exordium:index'))
        self.assertEqual(UserAwareView.get_preference_static(response.wsgi_request, 'show_live'), True)
        self.assertIn('exordium__show_live', response.wsgi_request.session)
        self.assertEqual(response.wsgi_request.session['exordium__show_live'], True)
        self.assertContains(response, 'Set user preferences')

        # Check to make sure our checkbox is in the state we expect
        self.assertContains(response, '"show_live" checked')

        # And now, submit one more, flipping back to False.
        response = self.client.post(reverse('exordium:updateprefs'), {})
        self.assertRedirects(response, reverse('exordium:index'), fetch_redirect_response=False)
        response = self.client.get(reverse('exordium:index'))
        self.assertEqual(UserAwareView.get_preference_static(response.wsgi_request, 'show_live'), False)
        self.assertIn('exordium__show_live', response.wsgi_request.session)
        self.assertEqual(response.wsgi_request.session['exordium__show_live'], False)
        self.assertContains(response, 'Set user preferences')

        # Check to make sure our checkbox is in the state we expect
        self.assertNotContains(response, '"show_live" checked')

    def test_show_live_user(self):
        """
        Test the behavior when we're logged in.  Should be stored in
        our user preferences, and avoid the session entirely.
        """
        
        # Log in!
        self.login()

        # Now, our default show_live should be False
        response = self.client.get(reverse('exordium:index'))
        self.assertEqual(UserAwareView.get_preference_static(response.wsgi_request, 'show_live'), False)
        self.assertNotIn('exordium__show_live', response.wsgi_request.session)
        self.assertEqual(response.wsgi_request.user.preferences['exordium__show_live'], False)

        # Check to make sure our checkbox is in the state we expect
        self.assertNotContains(response, '"show_live" checked')

        # Next: submit our preferences form to enable show_live.  Actually loading
        # the index again here isn't really required, but this simulates a browser,
        # so I dig it.
        response = self.client.post(reverse('exordium:updateprefs'), {'show_live': 'yes'})
        self.assertRedirects(response, reverse('exordium:index'), fetch_redirect_response=False)
        response = self.client.get(reverse('exordium:index'))
        self.assertEqual(UserAwareView.get_preference_static(response.wsgi_request, 'show_live'), True)
        self.assertNotIn('exordium__show_live', response.wsgi_request.session)
        self.assertEqual(response.wsgi_request.user.preferences['exordium__show_live'], True)
        self.assertContains(response, 'Set user preferences')

        # Check to make sure our checkbox is in the state we expect
        self.assertContains(response, '"show_live" checked')

        # And now, submit one more, flipping back to False.  Once again, the extra
        # redirect to index is a bit gratuitous.
        response = self.client.post(reverse('exordium:updateprefs'), {})
        self.assertRedirects(response, reverse('exordium:index'), fetch_redirect_response=False)
        response = self.client.get(reverse('exordium:index'))
        self.assertEqual(UserAwareView.get_preference_static(response.wsgi_request, 'show_live'), False)
        self.assertNotIn('exordium__show_live', response.wsgi_request.session)
        self.assertEqual(response.wsgi_request.user.preferences['exordium__show_live'], False)
        self.assertContains(response, 'Set user preferences')

        # Check to make sure our checkbox is in the state we expect
        self.assertNotContains(response, '"show_live" checked')

    def test_preferences_referer_redirect(self):
        """
        After a preference submission, we should be returned to the page
        we started on.
        """
        
        response = self.client.post(reverse('exordium:updateprefs'), {}, HTTP_REFERER=reverse('exordium:browse_artist'))
        self.assertRedirects(response, reverse('exordium:browse_artist'))

    def test_non_static_set_preference(self):
        """
        Our ``UserAwareView`` class has a non-static ``set_preference()`` method.  This
        isn't currently actually used anywhere, but I don't really want to get rid of it,
        since it makes sense to be in there.  So here's a test for it.
        """

        # First up - our default show_live should be None
        response = self.client.get(reverse('exordium:index'))
        self.assertEqual(UserAwareView.get_preference_static(response.wsgi_request, 'show_live'), None)
        self.assertNotIn('exordium__show_live', response.wsgi_request.session)

        # This is a bit hokey - I'm actually not really sure how to correctly
        # instansiate a view object with a request so that I can make calls as
        # if I'm currently in the view.  This seems to work, though, so whatever.
        view = IndexView()
        view.request = response.wsgi_request
        view.set_preference('show_live', True)
        self.assertIn('exordium__show_live', response.wsgi_request.session)
        self.assertEqual(response.wsgi_request.session['exordium__show_live'], True)

