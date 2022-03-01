from django.test import TestCase

from django.core.management import call_command
from django.core.management.base import CommandError

import io

from exordium.models import Artist, Album, Song, App, AlbumArt

class ImportMysqlAmpacheDatesSubcommandTests(TestCase):
    """
    Tests for our ``importmysqlampachedates`` management subcommand.  Right
    now, just verify that the thing is callable.  Would require having a
    MySQL database available to *actually* test.
    """

    def test_running_command(self):
        out = io.StringIO()
        with self.assertRaises(CommandError) as cm:
            call_command('importmysqlampachedates', stdout=out)

        self.assertIn('the following arguments are required', cm.exception.args[0])
