from django_test_migrations.contrib.unittest_case import MigratorTestCase

from django.urls import reverse

import unittest

# This is a bit hokey 'cause the way the class is defined doesn't let us
# specify a different set of preparation commands per test, so we have
# to use a separate class for each test

class TestMediaURLPrefSplit_Upgrade(MigratorTestCase):  # pragma: no cover

    migrate_from = ('exordium', '0003_add_opus_support')
    migrate_to = ('exordium', '0004_media_url_split')

    def prepare(self):
        # A bit improper to use _migrator like this, but we need dynamic prefs up and running
        self._migrator.apply_initial_migration(('dynamic_preferences', '0006_auto_20191001_2236'))
        GlobalPreferenceModel = self.old_state.apps.get_model('dynamic_preferences', 'GlobalPreferenceModel')

        # Set an initial pref
        url_orig = GlobalPreferenceModel(
                section='exordium',
                name='media_url',
                raw_value='http://original.url',
                )
        url_orig.save()

    @unittest.skip('These migration tests take forever on my system')
    def test_migration_upgrade(self):
        GlobalPreferenceModel = self.new_state.apps.get_model('dynamic_preferences', 'GlobalPreferenceModel')

        # Original pref should be gone, but its value should be copied to the others
        self.assertRaises(GlobalPreferenceModel.DoesNotExist,
                GlobalPreferenceModel.objects.get, section='exordium', name='media_url')

        html5 = GlobalPreferenceModel.objects.get(section='exordium', name='media_url_html5')
        self.assertNotEqual(html5, None)
        m3u = GlobalPreferenceModel.objects.get(section='exordium', name='media_url_m3u')
        self.assertNotEqual(m3u, None)

        self.assertEqual(html5.raw_value, 'http://original.url')
        self.assertEqual(m3u.raw_value, 'http://original.url')

class TestMediaURLPrefSplit_AlreadyVisited(MigratorTestCase):  # pragma: no cover

    migrate_from = ('exordium', '0003_add_opus_support')
    migrate_to = ('exordium', '0004_media_url_split')

    def prepare(self):
        # A bit improper to use _migrator like this, but we need dynamic prefs up and running
        self._migrator.apply_initial_migration(('dynamic_preferences', '0006_auto_20191001_2236'))
        GlobalPreferenceModel = self.old_state.apps.get_model('dynamic_preferences', 'GlobalPreferenceModel')

        # Set initial prefs
        url_orig = GlobalPreferenceModel(
                section='exordium',
                name='media_url',
                raw_value='http://original.url',
                )
        url_orig.save()
        url_html5 = GlobalPreferenceModel(
                section='exordium',
                name='media_url_html5',
                raw_value='http://html5.url',
                )
        url_html5.save()
        url_m3u = GlobalPreferenceModel(
                section='exordium',
                name='media_url_m3u',
                raw_value='http://m3u.url',
                )
        url_m3u.save()

    @unittest.skip('These migration tests take forever on my system')
    def test_migration_upgrade(self):
        GlobalPreferenceModel = self.new_state.apps.get_model('dynamic_preferences', 'GlobalPreferenceModel')

        # Original pref should be gone, and others should remain
        self.assertRaises(GlobalPreferenceModel.DoesNotExist,
                GlobalPreferenceModel.objects.get, section='exordium', name='media_url')

        html5 = GlobalPreferenceModel.objects.get(section='exordium', name='media_url_html5')
        self.assertNotEqual(html5, None)
        m3u = GlobalPreferenceModel.objects.get(section='exordium', name='media_url_m3u')
        self.assertNotEqual(m3u, None)

        self.assertEqual(html5.raw_value, 'http://html5.url')
        self.assertEqual(m3u.raw_value, 'http://m3u.url')

class TestMediaURLPrefSplit_EmptyPrefs(MigratorTestCase):  # pragma: no cover

    migrate_from = ('exordium', '0003_add_opus_support')
    migrate_to = ('exordium', '0004_media_url_split')

    def prepare(self):
        # A bit improper to use _migrator like this, but we need dynamic prefs up and running
        self._migrator.apply_initial_migration(('dynamic_preferences', '0006_auto_20191001_2236'))

    @unittest.skip('These migration tests take forever on my system')
    def test_migration_upgrade(self):
        GlobalPreferenceModel = self.new_state.apps.get_model('dynamic_preferences', 'GlobalPreferenceModel')

        # Shouldn't have any prefs
        self.assertRaises(GlobalPreferenceModel.DoesNotExist,
                GlobalPreferenceModel.objects.get, section='exordium', name='media_url')
        self.assertRaises(GlobalPreferenceModel.DoesNotExist,
                GlobalPreferenceModel.objects.get, section='exordium', name='media_url_html5')
        self.assertRaises(GlobalPreferenceModel.DoesNotExist,
                GlobalPreferenceModel.objects.get, section='exordium', name='media_url_m3u')

