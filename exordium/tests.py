from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone, html
from django.db.models import Q
from django.core.management import call_command
from django.core.management.base import CommandError

from django.contrib.auth.models import User
from django.contrib.staticfiles.templatetags.staticfiles import static

from dynamic_preferences.registries import global_preferences_registry

import io
import os
import shutil
import pathlib
import zipfile
import datetime
import tempfile

from mutagen.id3 import ID3, TIT2, TALB, TPE1, TDRC, TRCK, TDRL, TPE2, TPE3, TCOM
from mutagen.oggvorbis import OggVorbis
from mutagen.mp4 import MP4
from PIL import Image

from .models import Artist, Album, Song, App, AlbumArt
from .views import UserAwareView, IndexView, add_session_success, add_session_fail, add_session_msg

# These two imports are just here in case we want to examine SQL while running tests.
# If so, set "settings.DEBUG = True" in the test and then use connection.queries
#from django.conf import settings
#from django.db import connection

class ExordiumTests(TestCase):
    """
    Custom TestCase class for Exordium.  Includes our ``initial_data``
    fixture and sets up a pretend library under ``testdata``.  Uses
    the sample mp3 files in ``testdata`` as the basis for all the files
    that we'll be testing with.
    """

    fixtures = ['initial_data.json']

    testdata_path = os.path.join(os.path.dirname(__file__), 'testdata')
    library_path = None

    prefs = None

    def setUp(self):
        """
        Run automatically at the start of any test.  Ensure that there's no
        library hanging around in our testdata dir, ensure that our base
        testing files exist, and then set up the base library path.
        """
        for filename in ['silence-abr.mp3', 'silence-cbr.mp3', 'silence-vbr.mp3', 'invalid-tags.mp3',
                'silence.ogg', 'silence.m4a', 'silence.flac', 'cover_400.jpg', 'cover_400.gif',
                'cover_400.png', 'cover_400.tif', 'cover_100.jpg']:
            if not os.path.exists(os.path.join(self.testdata_path, filename)):  # pragma: no cover
                raise Exception('Required testing file "%s" does not exist!' % (filename))
        self.library_path = tempfile.mkdtemp()
        self.prefs = global_preferences_registry.manager()
        self.prefs['exordium__base_path'] = self.library_path
        self.prefs['exordium__media_url'] = 'http://testserver-media/music'

        # We have one test which alters the following value, which
        # will stay changed between tests unless we restore it.
        self.saved_album_size = AlbumArt.resolutions[AlbumArt.SZ_ALBUM]

    def tearDown(self):
        """
        Run automatically at the test conclusion.  Get rid of our base
        library.
        """
        shutil.rmtree(self.library_path)
        AlbumArt.resolutions[AlbumArt.SZ_ALBUM] = self.saved_album_size

    def check_library_filename(self, filename):
        """
        Checks to make sure our passed-in filename isn't trying to break
        out of our library.  This is a bit silly since only these tests
        will ever be passing in paths, and we'd have to be attempting to
        do nasty things to ourselves, but this should help prevent any
        unintentional blunders, at least.

        Returns our full filename, with library path, since we basically
        always want that after doing this check.
        """
        if len(filename) < 3 or '..' in filename or filename[0] == '/':
            raise Exception('Given filename "%s" is invalid' % (filename))
        return os.path.join(self.library_path, filename)

    def add_file(self, basefile, filename, path=''):
        """
        Adds an arbitrary datafile somewhere in our library.  Returns the
        full filename.
        """
        if path != '' and ('..' in path or path[0] == '/'):
            raise Exception('Given path "%s" is invalid' % (path))

        if '/' in basefile or len(basefile) < 3 or '.' not in basefile:
            raise Exception('Invalid basefile name: %s' % (basefile))

        src_filename = os.path.join(self.testdata_path, basefile)
        if not os.path.exists(src_filename):
            raise Exception('Source filename %s is not found' % (src_filename))

        full_path = os.path.join(self.library_path, path)
        full_filename = os.path.join(full_path, filename)
        os.makedirs(full_path, exist_ok=True)
        shutil.copyfile(src_filename, full_filename)
        self.assertEqual(os.path.exists(full_filename), True)

        return full_filename

    def add_mp3(self, path='', filename='file.mp3', artist='', album='',
            title='', tracknum=0, maxtracks=None, year=0, yeartag='TDRC',
            group='', conductor='', composer='',
            basefile='silence-vbr.mp3', save_as_v23=False,
            apply_tags=True):
        """
        Adds a new mp3 with the given parameters to our library.

        Pass in ``save_as_v23`` as ``True`` to have the file save with an ID3v2.3
        tag, instead of ID3v2.4.  One of the main tag-level changes which
        will happen there is conversion of the year tag to TYER, which
        we'll otherwise not be specifying directly.  ``yeartag`` is effectively
        ignored when ``save_as_v23`` is True.

        Pass in ``False`` for ``apply_tags`` to only use whatever tags happen to
        be present in the source basefile.
        """

        full_filename = self.add_file(basefile, filename, path=path)

        # Finish here if we've been told to.
        if not apply_tags:
            return

        # Apply the tags as specified
        tags = ID3()
        tags.add(TPE1(encoding=3, text=artist))
        tags.add(TALB(encoding=3, text=album))
        tags.add(TIT2(encoding=3, text=title))

        if group != '':
            tags.add(TPE2(encoding=3, text=group))
        if conductor != '':
            tags.add(TPE3(encoding=3, text=conductor))
        if composer != '':
            tags.add(TCOM(encoding=3, text=composer))

        if maxtracks is None:
            tags.add(TRCK(encoding=3, text=str(tracknum)))
        else:
            tags.add(TRCK(encoding=3, text='%s/%s' % (tracknum, maxtracks)))

        if yeartag == 'TDRL':
            tags.add(TDRL(encoding=3, text=str(year)))
        elif yeartag == 'TDRC':
            tags.add(TDRC(encoding=3, text=str(year)))
        else:
            raise Exception('Unknown year tag specified: %s' % (yeartag))

        # Convert to ID3v2.3 if requested.
        if save_as_v23:
            tags.update_to_v23()

        # Save to our filename
        tags.save(full_filename)

    def update_mp3(self, filename, artist=None, album=None,
            title=None, tracknum=None, maxtracks=None, year=None,
            group=None, conductor=None, composer=None):
        """
        Updates an on-disk mp3 with the given tag data.  Any passed-in
        variable set to None will be ignored.  It's possible there could
        be some problems with ID3v2.3 vs. ID3v2.4 tags in here - I don't
        know if mutagen does an auto-convert.  I think it might.

        If group/conductor/composer is a blank string, those fields will
        be completely removed from the file.  Any of the other fields set
        to blank will leave the tag in place.

        Will ensure that the file's mtime is updated.
        """

        full_filename = self.check_library_filename(filename)
        self.assertEqual(os.path.exists(full_filename), True)

        starting_mtime = int(os.stat(full_filename).st_mtime)

        tags = ID3(full_filename)

        if artist is not None:
            tags.delall('TPE1')
            tags.add(TPE1(encoding=3, text=artist))

        if album is not None:
            tags.delall('TALB')
            tags.add(TALB(encoding=3, text=album))

        if title is not None:
            tags.delall('TIT2')
            tags.add(TIT2(encoding=3, text=title))

        if group is not None:
            tags.delall('TPE2')
            if group != '':
                tags.add(TPE2(encoding=3, text=group))

        if conductor is not None:
            tags.delall('TPE3')
            if conductor != '':
                tags.add(TPE3(encoding=3, text=conductor))

        if composer is not None:
            tags.delall('TCOM')
            if composer != '':
                tags.add(TCOM(encoding=3, text=composer))

        if tracknum is not None:
            tags.delall('TRCK')
            if maxtracks is None:
                tags.add(TRCK(encoding=3, text=str(tracknum)))
            else:
                tags.add(TRCK(encoding=3, text='%s/%s' % (tracknum, maxtracks)))

        if year is not None:
            tags.delall('TDRC')
            tags.delall('TDRL')
            tags.delall('TYER')
            tags.add(TDRC(encoding=3, text=str(year)))

        # Save
        tags.save()

        # Check on mtime update and manually fix it if it's not updated
        stat_result = os.stat(full_filename)
        ending_mtime = int(stat_result.st_mtime)
        if starting_mtime == ending_mtime:
            new_mtime = ending_mtime + 1
            os.utime(full_filename, times=(stat_result.st_atime, new_mtime))

    def add_ogg(self, path='', filename='file.ogg', artist='', album='',
            title='', tracknum=None, year=None, group='', conductor='', composer='',
            basefile='silence.ogg', apply_tags=True):
        """
        Adds a new ogg with the given parameters to our library.

        Pass in ``False`` for ``apply_tags`` to only use whatever tags happen to
        be present in the source basefile.
        """

        full_filename = self.add_file(basefile, filename, path=path)

        # Finish here if we've been told to.
        if not apply_tags:
            return

        # Apply the tags as specified
        tags = OggVorbis(full_filename)
        tags['ARTIST'] = artist
        tags['ALBUM'] = album
        tags['TITLE'] = title

        if group != '':
            tags['ENSEMBLE'] = group
        if conductor != '':
            tags['CONDUCTOR'] = conductor
        if composer != '':
            tags['COMPOSER'] = composer
        if tracknum is not None:
            tags['TRACKNUMBER'] = str(tracknum)
        if year is not None:
            tags['DATE'] = str(year)

        # Save to our filename
        tags.save()

    def update_ogg(self, filename, artist=None, album=None,
            title=None, tracknum=None, year=None,
            group=None, conductor=None, composer=None):
        """
        Updates an on-disk ogg with the given tag data.  Any passed-in
        variable set to None will be ignored.

        If group/conductor/composer is a blank string, those fields will
        be completely removed from the file.  Any of the other fields set
        to blank will leave the tag in place.

        Will ensure that the file's mtime is updated.
        """

        full_filename = self.check_library_filename(filename)
        self.assertEqual(os.path.exists(full_filename), True)

        starting_mtime = int(os.stat(full_filename).st_mtime)

        tags = OggVorbis(full_filename)

        if artist is not None:
            try:
                del tags['ARTIST']
            except KeyError:
                pass
            tags['ARTIST'] = artist

        if album is not None:
            try:
                del tags['ALBUM']
            except KeyError:
                pass
            tags['ALBUM'] = album

        if title is not None:
            try:
                del tags['TITLE']
            except KeyError:
                pass
            tags['TITLE'] = title

        if group is not None:
            try:
                del tags['ENSEMBLE']
            except KeyError:
                pass
            if group != '':
                tags['ENSEMBLE'] = group

        if conductor is not None:
            try:
                del tags['CONDUCTOR']
            except KeyError:
                pass
            if conductor != '':
                tags['CONDUCTOR'] = conductor

        if composer is not None:
            try:
                del tags['COMPOSER']
            except KeyError:
                pass
            if composer != '':
                tags['COMPOSER'] = composer

        if tracknum is not None:
            try:
                del tags['TRACKNUMBER']
            except KeyError:
                pass
            tags['TRACKNUMBER'] = str(tracknum)

        if year is not None:
            try:
                del tags['DATE']
            except KeyError:
                pass
            try:
                del tags['YEAR']
            except KeyError:
                pass
            tags['DATE'] = str(year)

        # Save
        tags.save()

        # Check on mtime update and manually fix it if it's not updated
        stat_result = os.stat(full_filename)
        ending_mtime = int(stat_result.st_mtime)
        if starting_mtime == ending_mtime:
            new_mtime = ending_mtime + 1
            os.utime(full_filename, times=(stat_result.st_atime, new_mtime))

    def add_m4a(self, path='', filename='file.m4a', artist='', album='',
            title='', tracknum=None, year=None, composer='',
            basefile='silence.m4a', apply_tags=True):
        """
        Adds a new m4a with the given parameters to our library.

        Note that m4a tagging doesn't seem to support conductor or group/ensemble. 

        Pass in ``False`` for ``apply_tags`` to only use whatever tags happen to
        be present in the source basefile.
        """

        full_filename = self.add_file(basefile, filename, path=path)

        # Finish here if we've been told to.
        if not apply_tags:
            return

        # Apply the tags as specified
        tags = MP4(full_filename)
        tags['\xa9ART'] = artist
        tags['\xa9alb'] = album
        tags['\xa9nam'] = title

        if composer != '':
            tags['\xa9wrt'] = composer
        if tracknum is not None:
            tags['trkn'] = [(tracknum, 0)]
        if year is not None:
            tags['\xa9day'] = str(year)

        # Save to our filename
        tags.save()

    def update_m4a(self, filename, artist=None, album=None,
            title=None, tracknum=None, year=None,
            composer=None):
        """
        Updates an on-disk ogg with the given tag data.  Any passed-in
        variable set to None will be ignored.

        Note again that m4a tagging apparently doesn't support conductor or
        group/ensemble.

        If composer is a blank string, that field will be completely
        removed from the file.  Any of the other fields set to blank will
        leave the tag in place.

        Will ensure that the file's mtime is updated.
        """

        full_filename = self.check_library_filename(filename)
        self.assertEqual(os.path.exists(full_filename), True)

        starting_mtime = int(os.stat(full_filename).st_mtime)

        tags = MP4(full_filename)

        if artist is not None:
            try:
                del tags['\xa9ART']
            except KeyError:
                pass
            tags['\xa9ART'] = artist

        if album is not None:
            try:
                del tags['\xa9alb']
            except KeyError:
                pass
            tags['\xa9alb'] = album

        if title is not None:
            try:
                del tags['\xa9nam']
            except KeyError:
                pass
            tags['\xa9nam'] = title

        if composer is not None:
            try:
                del tags['\xa9wrt']
            except KeyError:
                pass
            if composer != '':
                tags['\xa9wrt'] = composer

        if tracknum is not None:
            try:
                del tags['trkn']
            except KeyError:
                pass
            tags['trkn'] = [(tracknum, 0)]

        if year is not None:
            try:
                del tags['\xa9day']
            except KeyError:
                pass
            tags['\xa9day'] = str(year)

        # Save
        tags.save()

        # Check on mtime update and manually fix it if it's not updated
        stat_result = os.stat(full_filename)
        ending_mtime = int(stat_result.st_mtime)
        if starting_mtime == ending_mtime:
            new_mtime = ending_mtime + 1
            os.utime(full_filename, times=(stat_result.st_atime, new_mtime))

    def delete_file(self, filename):
        """
        Deletes the given file from our fake library
        """
        full_filename = self.check_library_filename(filename)
        self.assertEqual(os.path.exists(full_filename), True)

        os.unlink(full_filename)

        self.assertEqual(os.path.exists(full_filename), False)

    def move_file(self, filename, destination):
        """
        Moves the given file in our fake library to a different destination
        """
        full_filename = self.check_library_filename(filename)
        self.assertEqual(os.path.exists(full_filename), True)

        if destination != '':
            full_destination = self.check_library_filename(destination)
        else:
            full_destination = self.library_path

        # Create the destination dir if it doesn't exist
        os.makedirs(full_destination, exist_ok=True)

        # Now move
        shutil.move(full_filename, full_destination)

        dest_filename = os.path.join(full_destination, os.path.basename(filename))
        self.assertEqual(os.path.exists(dest_filename), True)

    def touch_file(self, filename):
        """
        'touches' a file to have the current modification time, with the extra
        guarantee that the mtime WILL change.  Will set the time one second
        in the future if need be.
        """

        full_filename = self.check_library_filename(filename)

        starting_mtime = int(os.stat(full_filename).st_mtime)

        pathlib.Path(full_filename).touch(exist_ok=True)

        stat_result = os.stat(full_filename)
        ending_mtime = int(stat_result.st_mtime)
        if starting_mtime == ending_mtime:
            new_mtime = ending_mtime + 1
            os.utime(full_filename, times=(stat_result.st_atime, new_mtime))

    def set_file_ancient(self, filename):
        """
        Sets a file's mtime to be as old as it can possibly be.  This is
        only actually used in a single check in AlbumDownloadViewTests, but
        here it is anyway.
        """

        full_filename = self.check_library_filename(filename)
        stat_result = os.stat(full_filename)
        os.utime(full_filename, times=(stat_result.st_atime, 0))

    def age_album(self, artist, album, age_days):
        """
        Given an album already in our database, age it by setting its
        mtime to the current date minus the specified number of days.
        Returns the album object, since it's likely you'll want to use
        it for comparisons anyway.
        """
        album = Album.objects.get(artist__name=artist, name=album)
        album.time_added = timezone.now() - datetime.timedelta(days=age_days)
        album.save()
        return album

    def get_file_contents(self, filename):
        """
        Retrieves file contents from the named file in the library
        """

        full_filename = self.check_library_filename(filename)
        with open(full_filename, 'rb') as df:
            return df.read()

    def set_file_unreadable(self, filename):
        """
        Well set the given file to be unreadable by our add/update processes.
        """

        full_filename = self.check_library_filename(filename)
        os.chmod(full_filename, 0)

    def add_art(self, path='', filename='cover.jpg', basefile='cover_400.jpg'):
        """
        Adds a new cover image to our library in the specified dir.
        """

        self.add_file(basefile, filename, path=path)

    def assertNoErrors(self, appresults):
        """
        Given a list of tuples (as returned from ``App.add()`` or ``App.update()``),
        ensure that none of the lines have status App.STATUS_ERROR
        """
        for (status, line) in appresults:
            self.assertNotEqual(status, App.STATUS_ERROR, msg='Error found: "%s"' % (line))
        return appresults

    def assertErrors(self, appresults, errors_min=1, error=None):
        """
        Given a list of tuples (as returned from ``App.add()`` or ``App.update()``),
        ensure that we have at least ``errors_min`` with a status of App.STATUS_ERROR

        Optionally, also ensure that the errors we DO find match the text specified
        in ``error``.
        """
        error_count = 0
        for (status, line) in appresults:
            if status == App.STATUS_ERROR:
                error_count += 1
                if error is not None:
                    self.assertIn(error, line)
        self.assertGreaterEqual(error_count, errors_min, msg='%d errors expected, %d found' %
            (errors_min, error_count))
        return appresults

    def run_add(self):
        """
        Runs an ``add`` operation on our library, and checks for errors.
        """
        return self.assertNoErrors(list(App.add()))

    def run_add_errors(self, errors_min=1, error=None):
        """
        Runs an ``add`` operation on our library, and expect to see at least
        one error.
        """
        return self.assertErrors(list(App.add()), errors_min, error=error)

    def run_update(self):
        """
        Runs an ``update`` operation on our library, and checks for errors.
        """
        return self.assertNoErrors(list(App.update()))

    def run_update_errors(self, errors_min=1, error=None):
        """
        Runs an ``add`` operation on our library, and expect to see at least
        one error.
        """
        return self.assertErrors(list(App.update()), errors_min, error=error)

# My main Django installation uses an authentication backend of
# django.contrib.auth.backends.RemoteUserBackend, which the test
# client does NOT know what to do with by default.  We could
# have our stuff set a REMOTE_USER variable, perhaps, but it makes
# more sense to just ensure that these tests use a more common
# Django authentication backend.
@override_settings(AUTHENTICATION_BACKENDS=['django.contrib.auth.backends.ModelBackend'])
class ExordiumUserTests(ExordiumTests):
    """
    Tests of ours which also test views, which means that we might need to
    have an admin/staff user in order to test various things.
    """

    @classmethod
    def setUpTestData(self):
        """
        Sets up a user which all tests in this class can use.  The user
        will have staff privileges.
        """
        super(ExordiumUserTests, self).setUpTestData()
        self.user = User.objects.create_user('mainuser')
        self.user.is_staff = True
        self.user.save()

    def login(self):
        """
        Logs in as our staff user
        """
        self.client.force_login(self.user)

class TestTests(ExordiumTests):
    """
    This is silly, but I've become a bit obsessed about 100% coverage.py
    results.  This class just tests various cases in our main ExordiumTests
    class which for whatever reason don't actually end up happening in the
    main test areas.
    """

    def test_file_move_to_base_dir(self):
        """
        Move a file to the base library directory.
        """
        self.add_art(path='albumdir')
        self.move_file('albumdir/cover.jpg', '')

    def test_add_ogg_without_tags(self):
        """
        Add an ogg file without tags
        """
        self.add_ogg(filename='song.ogg', apply_tags=False)

    def test_update_ogg_with_previously_empty_tags(self):
        """
        Update an ogg file which previously had no tags.
        """
        self.add_ogg(filename='song.ogg', apply_tags=False)
        self.update_ogg('song.ogg',
            artist='Artist',
            album='Album',
            title='Title',
            tracknum=1,
            year=2016,
            group='Group',
            conductor='Conductor',
            composer='Composer')

    def test_update_ogg_with_previously_full_tags(self):
        """
        Update an ogg file which previously had a full set of tags
        """
        self.add_ogg(filename='song.ogg', 
            artist='Artist',
            album='Album',
            title='Title',
            tracknum=1,
            year=2016,
            group='Group',
            conductor='Conductor',
            composer='Composer')
        self.update_ogg('song.ogg',
            artist='New Artist',
            album='New Album',
            title='New Title',
            tracknum=2,
            year=2006,
            group='New Group',
            conductor='New Conductor',
            composer='New Composer')

    def test_add_m4a_without_tags(self):
        """
        Add an m4a file without tags
        """
        self.add_m4a(filename='song.m4a', apply_tags=False)

    def test_update_m4a_with_previously_empty_tags(self):
        """
        Update an m4a file which previously had no tags.
        """
        self.add_m4a(filename='song.m4a', apply_tags=False)
        self.update_m4a('song.m4a',
            artist='Artist',
            album='Album',
            title='Title',
            tracknum=1,
            year=2016,
            composer='Composer')

    def test_update_m4a_with_previously_full_tags(self):
        """
        Update an m4a file which previously had a full set of tags
        """
        self.add_m4a(filename='song.m4a', 
            artist='Artist',
            album='Album',
            title='Title',
            tracknum=1,
            year=2016,
            composer='Composer')
        self.update_m4a('song.m4a',
            artist='New Artist',
            album='New Album',
            title='New Title',
            tracknum=2,
            year=2006,
            composer='New Composer')

    def test_update_mp3_with_maxtracks(self):
        """
        Updates an mp3 with a track number which includes the max track count.
        """
        self.add_mp3(filename='song.mp3', artist='Artist',
            album='Album', title='Title', tracknum=1)
        self.update_mp3('song.mp3', tracknum=2, maxtracks=10)

    def test_add_mp3_invalid_year_tags(self):
        """
        Adds an mp3 with an invalid year tag specified.
        """
        self.assertRaises(Exception, self.add_mp3, yeartag='INVALID')

    def test_add_file_invalid_path_dotdot(self):
        """
        Attemps to add a file with an invalid path which includes '..'
        """
        with self.assertRaises(Exception) as cm:
            self.add_file(basefile='foo', filename='file', path='..')

        self.assertIn('Given path ".." is invalid', cm.exception.args[0])

    def test_add_file_invalid_path_leading_slash(self):
        """
        Attemps to add a file with an invalid path which includes a leading
        slash
        """
        with self.assertRaises(Exception) as cm:
            self.add_file(basefile='foo', filename='file', path='/hello')

        self.assertIn('Given path "/hello" is invalid', cm.exception.args[0])

    def test_add_file_invalid_basefile_slash(self):
        """
        Attemps to add a file with an invalid basefile which includes
        a slash anywhere in the filename
        """
        with self.assertRaises(Exception) as cm:
            self.add_file(basefile='foo/bar.mp3', filename='file')

        self.assertIn('Invalid basefile name:', cm.exception.args[0])

    def test_add_file_invalid_basefile_too_short(self):
        """
        Attemps to add a file with an invalid basefile which is
        too short
        """
        with self.assertRaises(Exception) as cm:
            self.add_file(basefile='aa', filename='file')

        self.assertIn('Invalid basefile name:', cm.exception.args[0])

    def test_add_file_invalid_basefile_without_dot(self):
        """
        Attemps to add a file with an invalid basefile which does
        not contain a dot in the filename
        """
        with self.assertRaises(Exception) as cm:
            self.add_file(basefile='hellothere', filename='file')

        self.assertIn('Invalid basefile name:', cm.exception.args[0])

    def test_add_file_invalid_basefile_does_not_exist(self):
        """
        Attemps to add a file with an invalid basefile which does
        not exist
        """
        with self.assertRaises(Exception) as cm:
            self.add_file(basefile='hello.there', filename='hello.there')

        self.assertIn('Source filename %s is not found' %
            (os.path.join(self.testdata_path, 'hello.there')), cm.exception.args[0])

    def test_check_library_filename_invalid_dotdot(self):
        """
        Tests a call to ``check_library_filename()`` with an invalid
        filename (one which contains a '..')
        """
        with self.assertRaises(Exception) as cm:
            self.check_library_filename('../stuff')

        self.assertIn('Given filename "../stuff" is invalid', cm.exception.args[0])

    def test_check_library_filename_invalid_too_short(self):
        """
        Tests a call to ``check_library_filename()`` with an invalid
        filename (one which is too short)
        """
        with self.assertRaises(Exception) as cm:
            self.check_library_filename('aa')

        self.assertIn('Given filename "aa" is invalid', cm.exception.args[0])

    def test_check_library_filename_invalid_leading_slash(self):
        """
        Tests a call to ``check_library_filename()`` with an invalid
        filename (one which has a leading slash)
        """
        with self.assertRaises(Exception) as cm:
            self.check_library_filename('/file')

        self.assertIn('Given filename "/file" is invalid', cm.exception.args[0])

class BasicAddTests(ExordiumTests):
    """
    Basic testing of the add() procedure under various circumstances.
    """

    ###
    ### Some methods called by the actual tests to get rid of some duplication
    ###

    def mp3_mode_test(self, mode):
        """
        Tests a simple addition of an mp3 of the given mode
        (abr/cbr/vbr) to the database, to ensure that that detection
        process is working properly.
        """
        self.add_mp3(artist='Artist', title='Title', basefile='silence-%s.mp3' % (mode.lower()))
        self.run_add()
        song = Song.objects.get(title='Title')
        self.assertEqual(song.mode, mode.upper())

    def mp3_year_test(self, year, yeartag):
        """
        Tests a simple addition of an mp3 to the database, using
        the specified year tag.
        """
        self.add_mp3(artist='Artist', title='Title', year=year, yeartag=yeartag)
        self.run_add()
        song = Song.objects.get()
        self.assertEqual(song.year, year)

    ###
    ### Actual tests follow
    ###

    def test_add_single_vbr_mp3(self):
        """
        Tests adding a single VBR mp3 to our library
        """
        self.mp3_mode_test('vbr')

    def test_add_single_cbr_mp3(self):
        """
        Tests adding a single CBR mp3 to our library
        """
        self.mp3_mode_test('cbr')

    def test_add_single_abr_mp3(self):
        """
        Tests adding a single ABR mp3 to our library
        """
        self.mp3_mode_test('abr')

    def test_add_with_no_various_artist(self):
        """
        Test what happens when we run an add without having a Various artist.
        It should be created.  Note that this won't actually happen unless
        we're also adding at least one real track.
        """
        self.assertEqual(Artist.objects.count(), 1)
        self.assertEqual(Album.objects.count(), 0)
        self.assertEqual(Song.objects.count(), 0)
        ar = Artist.objects.get()
        self.assertEqual(ar.various, True)
        ar.delete()
        self.assertEqual(Artist.objects.count(), 0)

        self.add_mp3(artist='Artist', title='Title',
            filename='song.mp3')
        self.run_add()

        self.assertEqual(Artist.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Song.objects.count(), 1)
        ar = Artist.objects.get(name='Various')
        self.assertEqual(ar.various, True)

    def test_add_mp3_simple_tag_check(self):
        """
        Adds a single fully-tagged track and check that the resulting database
        objects are all populated properly
        """
        self.add_mp3(artist='Artist', title='Title', album='Album',
            year=1970, tracknum=1)
        self.run_add()

        artist = Artist.objects.get(name='Artist')
        self.assertEqual(artist.name, 'Artist')
        self.assertEqual(artist.prefix, '')

        album = Album.objects.get()
        self.assertEqual(album.name, 'Album')
        self.assertEqual(album.year, 1970)
        self.assertEqual(album.artist.name, 'Artist')

        song = Song.objects.get()
        self.assertEqual(song.title, 'Title')
        self.assertEqual(song.normtitle, 'title')
        self.assertEqual(song.year, 1970)
        self.assertEqual(song.tracknum, 1)
        self.assertEqual(song.album.name, 'Album')
        self.assertEqual(song.artist.name, 'Artist')

    def test_add_classical_simple_tag_check(self):
        """
        Adds a single fully-tagged track and check that the resulting database
        objects are all populated properly
        """
        self.add_mp3(artist='Artist', title='Title', album='Album',
            group='Group', conductor='Conductor', composer='Composer',
            year=1970, tracknum=1)
        self.run_add()

        self.assertEqual(Song.objects.count(), 1)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 5)

        artist = Artist.objects.get(name='Artist')
        self.assertEqual(artist.name, 'Artist')
        self.assertEqual(artist.prefix, '')

        artist = Artist.objects.get(name='Group')
        self.assertEqual(artist.name, 'Group')
        self.assertEqual(artist.prefix, '')

        artist = Artist.objects.get(name='Conductor')
        self.assertEqual(artist.name, 'Conductor')
        self.assertEqual(artist.prefix, '')

        artist = Artist.objects.get(name='Composer')
        self.assertEqual(artist.name, 'Composer')
        self.assertEqual(artist.prefix, '')

        album = Album.objects.get()
        self.assertEqual(album.name, 'Album')
        self.assertEqual(album.year, 1970)
        self.assertEqual(album.artist.name, 'Artist')

        song = Song.objects.get()
        self.assertEqual(song.title, 'Title')
        self.assertEqual(song.year, 1970)
        self.assertEqual(song.tracknum, 1)
        self.assertEqual(song.album.name, 'Album')
        self.assertEqual(song.artist.name, 'Artist')
        self.assertEqual(song.group.name, 'Group')
        self.assertEqual(song.conductor.name, 'Conductor')
        self.assertEqual(song.composer.name, 'Composer')

    def test_add_ogg_simple_tag_check(self):
        """
        Adds a single fully-tagged track and check that the resulting database
        objects are all populated properly
        """
        self.add_ogg(artist='Artist', title='Title', album='Album',
            year=1970, tracknum=1)
        self.run_add()

        artist = Artist.objects.get(name='Artist')
        self.assertEqual(artist.name, 'Artist')
        self.assertEqual(artist.prefix, '')

        album = Album.objects.get()
        self.assertEqual(album.name, 'Album')
        self.assertEqual(album.year, 1970)
        self.assertEqual(album.artist.name, 'Artist')

        song = Song.objects.get()
        self.assertEqual(song.title, 'Title')
        self.assertEqual(song.normtitle, 'title')
        self.assertEqual(song.year, 1970)
        self.assertEqual(song.tracknum, 1)
        self.assertEqual(song.album.name, 'Album')
        self.assertEqual(song.artist.name, 'Artist')

    def test_add_classical_simple_tag_check_ogg(self):
        """
        Adds a single fully-tagged track and check that the resulting database
        objects are all populated properly
        """
        self.add_ogg(artist='Artist', title='Title', album='Album',
            group='Group', conductor='Conductor', composer='Composer',
            year=1970, tracknum=1)
        self.run_add()

        self.assertEqual(Song.objects.count(), 1)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 5)

        artist = Artist.objects.get(name='Artist')
        self.assertEqual(artist.name, 'Artist')
        self.assertEqual(artist.prefix, '')

        artist = Artist.objects.get(name='Group')
        self.assertEqual(artist.name, 'Group')
        self.assertEqual(artist.prefix, '')

        artist = Artist.objects.get(name='Conductor')
        self.assertEqual(artist.name, 'Conductor')
        self.assertEqual(artist.prefix, '')

        artist = Artist.objects.get(name='Composer')
        self.assertEqual(artist.name, 'Composer')
        self.assertEqual(artist.prefix, '')

        album = Album.objects.get()
        self.assertEqual(album.name, 'Album')
        self.assertEqual(album.year, 1970)
        self.assertEqual(album.artist.name, 'Artist')

        song = Song.objects.get()
        self.assertEqual(song.title, 'Title')
        self.assertEqual(song.year, 1970)
        self.assertEqual(song.tracknum, 1)
        self.assertEqual(song.album.name, 'Album')
        self.assertEqual(song.artist.name, 'Artist')
        self.assertEqual(song.group.name, 'Group')
        self.assertEqual(song.conductor.name, 'Conductor')
        self.assertEqual(song.composer.name, 'Composer')

    def test_add_m4a_simple_tag_check(self):
        """
        Adds a single fully-tagged track and check that the resulting database
        objects are all populated properly
        """
        self.add_m4a(artist='Artist', title='Title', album='Album',
            year=1970, tracknum=1)
        self.run_add()

        artist = Artist.objects.get(name='Artist')
        self.assertEqual(artist.name, 'Artist')
        self.assertEqual(artist.prefix, '')

        album = Album.objects.get()
        self.assertEqual(album.name, 'Album')
        self.assertEqual(album.year, 1970)
        self.assertEqual(album.artist.name, 'Artist')

        song = Song.objects.get()
        self.assertEqual(song.title, 'Title')
        self.assertEqual(song.normtitle, 'title')
        self.assertEqual(song.year, 1970)
        self.assertEqual(song.tracknum, 1)
        self.assertEqual(song.album.name, 'Album')
        self.assertEqual(song.artist.name, 'Artist')

    def test_add_classical_simple_tag_check_m4a(self):
        """
        Adds a single fully-tagged track and check that the resulting database
        objects are all populated properly
        """
        self.add_m4a(artist='Artist', title='Title', album='Album',
            composer='Composer', year=1970, tracknum=1)
        self.run_add()

        self.assertEqual(Song.objects.count(), 1)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 3)

        artist = Artist.objects.get(name='Artist')
        self.assertEqual(artist.name, 'Artist')
        self.assertEqual(artist.prefix, '')

        artist = Artist.objects.get(name='Composer')
        self.assertEqual(artist.name, 'Composer')
        self.assertEqual(artist.prefix, '')

        album = Album.objects.get()
        self.assertEqual(album.name, 'Album')
        self.assertEqual(album.year, 1970)
        self.assertEqual(album.artist.name, 'Artist')

        song = Song.objects.get()
        self.assertEqual(song.title, 'Title')
        self.assertEqual(song.year, 1970)
        self.assertEqual(song.tracknum, 1)
        self.assertEqual(song.album.name, 'Album')
        self.assertEqual(song.artist.name, 'Artist')
        self.assertEqual(song.composer.name, 'Composer')

    def test_add_mp3_total_track_tag_check(self):
        """
        Adds a single track to check for the alternate tracknum format
        where the maximum track count is included in the tag.
        """
        self.add_mp3(artist='Artist', title='Title', tracknum=1,
            maxtracks=5)
        self.run_add()

        song = Song.objects.get()
        self.assertEqual(song.tracknum, 1)

    def test_add_mp3_id3v23(self):
        """
        Adds a single track using ID3v2.3 encoding, rather than ID3v2.4.  The
        main thing we're checking here is for the year (whose tag changed between
        those two versions), but we'll be checking basically everything anyway.
        """
        self.add_mp3(artist='Artist', title='Title', album='Album',
            year=1970, tracknum=1, save_as_v23=True)
        self.run_add()
        song = Song.objects.get()
        self.assertEqual(song.title, 'Title')
        self.assertEqual(song.year, 1970)
        self.assertEqual(song.tracknum, 1)
        self.assertEqual(song.album.name, 'Album')
        self.assertEqual(song.artist.name, 'Artist')

    def test_add_mp3_alternate_year_tdrl(self):
        """
        Adds a single track using the specific year tag TDRL, and verify
        that the year is populated properly.
        """
        self.mp3_year_test(1970, 'TDRL')

    def test_add_mp3_alternate_year_tdrc(self):
        """
        Adds a single track using the specific year tag TDRC, and verify
        that the year is populated properly.
        """
        self.mp3_year_test(1970, 'TDRC')

    def test_add_mp3_empty_track_tag(self):
        """
        Adds a single track with an empty tracknum field.  Note that
        mutagen refuses to write an actually-empty string to a tag,
        so we're using a space instead.  The important part is just
        that it's a value that fails when passed to int()
        """
        self.add_mp3(artist='Artist', title='Title', tracknum=' ')
        self.run_add()
        self.assertEqual(Song.objects.count(), 1)
        song = Song.objects.get()
        self.assertEqual(song.artist.name, 'Artist')
        self.assertEqual(song.title, 'Title')
        self.assertEqual(song.tracknum, 0)

    def test_add_mp3_empty_year_tag(self):
        """
        Adds a single track with an empty year field.  Mutagen refuses to
        write out invalid tags, so we've just constructed one to pass in.
        This technically also tests an empty tracknum field, making the
        previous test unnecessary, but whatever, we'll do both.
        """
        self.add_mp3(basefile='invalid-tags.mp3', apply_tags=False)
        self.run_add()
        self.assertEqual(Song.objects.count(), 1)
        song = Song.objects.get()
        self.assertEqual(song.artist.name, 'Artist')
        self.assertEqual(song.title, 'Title')
        self.assertEqual(song.year, 0)
        self.assertEqual(song.tracknum, 0)

    def test_add_mp3_no_tags(self):
        """
        Test adding an mp3 file which has no tags specified
        """
        self.add_mp3(apply_tags=False)
        self.run_add_errors(error='Artist name not found')
        self.assertEqual(Song.objects.count(), 0)
        self.assertEqual(Artist.objects.count(), 1)
        self.assertEqual(Album.objects.count(), 0)

    def test_add_mp3_no_title_tag(self):
        """
        Test adding an mp3 file which has no title tag specified
        """
        self.add_mp3(artist='Artist')
        self.run_add_errors(error='Title not found')
        self.assertEqual(Song.objects.count(), 0)
        self.assertEqual(Artist.objects.count(), 1)
        self.assertEqual(Album.objects.count(), 0)

    def test_add_mp3_no_artist_tag(self):
        """
        Test adding an mp3 file which has no artist tag specified
        """
        self.add_mp3(title='Title', composer='Composer', album='Album')
        self.run_add_errors(error='Artist name not found')
        self.assertEqual(Song.objects.count(), 0)
        self.assertEqual(Artist.objects.count(), 1)
        self.assertEqual(Album.objects.count(), 0)

    def test_add_without_filesystem_permissions(self):
        """
        Attempts adding a file that we don't actually have permission
        to read.  This does NOT produce any errors, because I intentionally
        mark some files as not readable by the user Django's running as,
        in order to hide them from Exordium.  It does get logged as a
        DEBUG message, but I won't bother looking for that.
        """
        self.add_mp3(artist='Artist', title='Title', album='Album',
            year=1970, tracknum=1, filename='song.mp3')
        self.set_file_unreadable('song.mp3')
        self.run_add()
        self.assertEqual(Song.objects.count(), 0)
        self.assertEqual(Artist.objects.count(), 1)
        self.assertEqual(Album.objects.count(), 0)

    def test_add_invalid_filetype(self):
        """
        Attempts adding a file of a type we don't support (masquerading as
        one we do, with an invalid extension.  Using a .flac here)
        """
        self.add_file('silence.flac', 'song.ogg')
        self.run_add_errors(error='not yet understood')
        self.assertEqual(Song.objects.count(), 0)
        self.assertEqual(Artist.objects.count(), 1)
        self.assertEqual(Album.objects.count(), 0)

    def test_add_various_reserved_name(self):
        """
        Attempts adding a file which uses the artist name "Various", which
        is currently a reserved value in Exordium.
        """
        self.add_mp3(artist='Various', title='Title',
            album='Album', filename='song.mp3')
        self.run_add_errors(error='Artist name "Various" is reserved')

        self.assertEqual(Song.objects.count(), 0)
        self.assertEqual(Artist.objects.count(), 1)
        self.assertEqual(Album.objects.count(), 0)

    def test_add_mp3s_different_artist_case(self):
        """
        Adds two tracks by the same artist, but with different capitalization
        on the artist name.  Which version of the artist name gets stored is
        basically just dependent on whatever the app sees first.  I'm tempted
        to have it compare when it sees alternate cases and use the one with
        the most uppercase, but I think I'll just leave that to manual editing.
        """
        self.add_mp3(artist='Artist Name', title='Title 1', filename='song1.mp3')
        self.add_mp3(artist='artist name', title='Title 2', filename='song2.mp3')
        self.run_add()
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 2)
        # Note the mixed-case in the query, just checking that too.
        artist = Artist.objects.get(name__iexact='artist Name')
        self.assertEqual(artist.name.lower(), 'artist name')

    def test_add_song_different_composer_case(self):
        """
        Add a track with the same artist and composer but with different capitalization.
        Should only have one artist for it.
        """
        self.add_mp3(artist='Artist Name', composer='artist name', title='Title 1', filename='song1.mp3')
        self.run_add()
        self.assertEqual(Song.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)
        artist = Artist.objects.get(name__iexact='artist Name')
        self.assertEqual(artist.name.lower(), 'artist name')
        song = Song.objects.get()
        self.assertEqual(song.artist.name.lower(), 'artist name')
        self.assertEqual(song.composer.name.lower(), 'artist name')

    def test_add_song_different_group_case(self):
        """
        Add a track with the same artist and group but with different capitalization.
        Should only have one artist for it.
        """
        self.add_mp3(artist='Artist Name', group='artist name', title='Title 1', filename='song1.mp3')
        self.run_add()
        self.assertEqual(Song.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)
        artist = Artist.objects.get(name__iexact='artist Name')
        self.assertEqual(artist.name.lower(), 'artist name')
        song = Song.objects.get()
        self.assertEqual(song.artist.name.lower(), 'artist name')
        self.assertEqual(song.group.name.lower(), 'artist name')

    def test_add_song_different_conductor_case(self):
        """
        Add a track with the same artist and conductor but with different capitalization.
        Should only have one artist for it.
        """
        self.add_mp3(artist='Artist Name', conductor='artist name', title='Title 1', filename='song1.mp3')
        self.run_add()
        self.assertEqual(Song.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)
        artist = Artist.objects.get(name__iexact='artist Name')
        self.assertEqual(artist.name.lower(), 'artist name')
        song = Song.objects.get()
        self.assertEqual(song.artist.name.lower(), 'artist name')
        self.assertEqual(song.conductor.name.lower(), 'artist name')

    def test_add_songs_different_group_cases(self):
        """
        Add two tracks with alternating artist/group names, both with different cases.
        """
        self.add_mp3(artist='Artist One', group='artist two', title='Title 1', filename='song1.mp3')
        self.add_mp3(artist='Artist Two', group='artist one', title='Title 2', filename='song2.mp3')
        self.run_add()
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 3)
        artist = Artist.objects.get(name__iexact='artist One')
        self.assertEqual(artist.name.lower(), 'artist one')
        artist = Artist.objects.get(name__iexact='artist Two')
        self.assertEqual(artist.name.lower(), 'artist two')
        song = Song.objects.get(filename='song1.mp3')
        self.assertEqual(song.artist.name.lower(), 'artist one')
        self.assertEqual(song.group.name.lower(), 'artist two')
        song = Song.objects.get(filename='song2.mp3')
        self.assertEqual(song.artist.name.lower(), 'artist two')
        self.assertEqual(song.group.name.lower(), 'artist one')

    def test_add_songs_different_conductor_cases(self):
        """
        Add two tracks with alternating artist/conductor names, both with different cases.
        """
        self.add_mp3(artist='Artist One', conductor='artist two', title='Title 1', filename='song1.mp3')
        self.add_mp3(artist='Artist Two', conductor='artist one', title='Title 2', filename='song2.mp3')
        self.run_add()
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 3)
        artist = Artist.objects.get(name__iexact='artist One')
        self.assertEqual(artist.name.lower(), 'artist one')
        artist = Artist.objects.get(name__iexact='artist Two')
        self.assertEqual(artist.name.lower(), 'artist two')
        song = Song.objects.get(filename='song1.mp3')
        self.assertEqual(song.artist.name.lower(), 'artist one')
        self.assertEqual(song.conductor.name.lower(), 'artist two')
        song = Song.objects.get(filename='song2.mp3')
        self.assertEqual(song.artist.name.lower(), 'artist two')
        self.assertEqual(song.conductor.name.lower(), 'artist one')

    def test_add_songs_different_composer_cases(self):
        """
        Add two tracks with alternating artist/composer names, both with different cases.
        """
        self.add_mp3(artist='Artist One', composer='artist two', title='Title 1', filename='song1.mp3')
        self.add_mp3(artist='Artist Two', composer='artist one', title='Title 2', filename='song2.mp3')
        self.run_add()
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 3)
        artist = Artist.objects.get(name__iexact='artist One')
        self.assertEqual(artist.name.lower(), 'artist one')
        artist = Artist.objects.get(name__iexact='artist Two')
        self.assertEqual(artist.name.lower(), 'artist two')
        song = Song.objects.get(filename='song1.mp3')
        self.assertEqual(song.artist.name.lower(), 'artist one')
        self.assertEqual(song.composer.name.lower(), 'artist two')
        song = Song.objects.get(filename='song2.mp3')
        self.assertEqual(song.artist.name.lower(), 'artist two')
        self.assertEqual(song.composer.name.lower(), 'artist one')

    def test_add_mp3s_different_album_case(self):
        """
        Adds two tracks by the same artist and album, but with different
        capitalization on the album name.  Which version of the album name
        gets stored is basically just dependent on whatever the app sees first.
        """
        self.add_mp3(artist='Artist', album='Album Name',
            title='Title 1', filename='song1.mp3')
        self.add_mp3(artist='Artist', album='album name',
            title='Title 2', filename='song2.mp3')
        self.run_add()

        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)

        # Note the mixed-case in the query, just checking that too.
        album = Album.objects.get(name__iexact='album Name')
        self.assertEqual(album.name.lower(), 'album name')
        self.assertEqual(album.song_set.count(), 2)

    def test_add_mp3s_different_artist_and_album_case(self):
        """
        Adds two tracks by the same artist and album, but with different
        capitalization on the album and artist names.  Which version of the names
        gets stored is basically just dependent on whatever the app sees first.
        """
        self.add_mp3(artist='artist name', album='Album Name',
            title='Title 1', filename='song1.mp3')
        self.add_mp3(artist='Artist Name', album='album name',
            title='Title 2', filename='song2.mp3')
        self.run_add()

        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)

        # Note the mixed-case in the query, just checking that too.
        album = Album.objects.get(name__iexact='album Name')
        self.assertEqual(album.name.lower(), 'album name')
        self.assertEqual(album.song_set.count(), 2)
        artist = Artist.objects.get(name__iexact='artist Name')
        self.assertEqual(artist.name.lower(), 'artist name')

    def test_add_mp3s_differing_umlaut_artist(self):
        """
        Add two mp3s with the same artist but differing umlauts for the
        artist name.
        """
        self.add_mp3(artist='Umläut', album='Album',
            title='Title 1', filename='song1.mp3')
        self.add_mp3(artist='Umlaut', album='Album',
            title='Title 2', filename='song2.mp3')
        self.run_add()

        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)

    def test_add_song_differing_umlaut_group(self):
        """
        Add two mp3s with the same artist but differing umlauts for the
        artist name.
        """
        self.add_mp3(artist='Umläut', group='Umlaut', album='Album',
            title='Title 1', filename='song1.mp3')
        self.run_add()

        self.assertEqual(Song.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        artist = Artist.objects.get(normname='umlaut')
        self.assertEqual(artist.name, 'Umläut')
        song = Song.objects.get()
        self.assertEqual(song.artist.normname, 'umlaut')
        self.assertEqual(song.group.normname, 'umlaut')

    def test_add_song_differing_umlaut_conductor(self):
        """
        Add two mp3s with the same artist but differing umlauts for the
        artist name.
        """
        self.add_mp3(artist='Umläut', conductor='Umlaut', album='Album',
            title='Title 1', filename='song1.mp3')
        self.run_add()

        self.assertEqual(Song.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        artist = Artist.objects.get(normname='umlaut')
        self.assertEqual(artist.name, 'Umläut')
        song = Song.objects.get()
        self.assertEqual(song.artist.normname, 'umlaut')
        self.assertEqual(song.conductor.normname, 'umlaut')

    def test_add_song_differing_umlaut_composer(self):
        """
        Add two mp3s with the same artist but differing umlauts for the
        artist name.
        """
        self.add_mp3(artist='Umläut', composer='Umlaut', album='Album',
            title='Title 1', filename='song1.mp3')
        self.run_add()

        self.assertEqual(Song.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        artist = Artist.objects.get(normname='umlaut')
        self.assertEqual(artist.name, 'Umläut')
        song = Song.objects.get()
        self.assertEqual(song.artist.normname, 'umlaut')
        self.assertEqual(song.composer.normname, 'umlaut')

    def test_add_songs_different_group_umlaut(self):
        """
        Add two tracks with alternating artist/group names, both with different umlauts.
        """
        self.add_mp3(artist='Umläut 1', group='Umlaut 2', title='Title 1', filename='song1.mp3')
        self.add_mp3(artist='Umläut 2', group='Umlaut 1', title='Title 2', filename='song2.mp3')
        self.run_add()
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 3)
        song = Song.objects.get(filename='song1.mp3')
        self.assertEqual(song.artist.normname, 'umlaut 1')
        self.assertEqual(song.group.normname, 'umlaut 2')
        song = Song.objects.get(filename='song2.mp3')
        self.assertEqual(song.artist.normname, 'umlaut 2')
        self.assertEqual(song.group.normname, 'umlaut 1')

    def test_add_songs_different_conductor_umlaut(self):
        """
        Add two tracks with alternating artist/conductor names, both with different umlauts.
        """
        self.add_mp3(artist='Umläut 1', conductor='Umlaut 2', title='Title 1', filename='song1.mp3')
        self.add_mp3(artist='Umläut 2', conductor='Umlaut 1', title='Title 2', filename='song2.mp3')
        self.run_add()
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 3)
        song = Song.objects.get(filename='song1.mp3')
        self.assertEqual(song.artist.normname, 'umlaut 1')
        self.assertEqual(song.conductor.normname, 'umlaut 2')
        song = Song.objects.get(filename='song2.mp3')
        self.assertEqual(song.artist.normname, 'umlaut 2')
        self.assertEqual(song.conductor.normname, 'umlaut 1')

    def test_add_songs_different_composer_umlaut(self):
        """
        Add two tracks with alternating artist/composer names, both with different umlauts.
        """
        self.add_mp3(artist='Umläut 1', composer='Umlaut 2', title='Title 1', filename='song1.mp3')
        self.add_mp3(artist='Umläut 2', composer='Umlaut 1', title='Title 2', filename='song2.mp3')
        self.run_add()
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 3)
        song = Song.objects.get(filename='song1.mp3')
        self.assertEqual(song.artist.normname, 'umlaut 1')
        self.assertEqual(song.composer.normname, 'umlaut 2')
        song = Song.objects.get(filename='song2.mp3')
        self.assertEqual(song.artist.normname, 'umlaut 2')
        self.assertEqual(song.composer.normname, 'umlaut 1')

    def test_add_mp3s_differing_umlaut_album(self):
        """
        Add two mp3s with the same artist but differing umlauts for the
        album name.
        """
        self.add_mp3(artist='Umlaut', album='Albüm',
            title='Title 1', filename='song1.mp3')
        self.add_mp3(artist='Umlaut', album='Album',
            title='Title 2', filename='song2.mp3')
        self.run_add()

        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)

    def test_add_mp3s_differing_umlaut_album_and_artist(self):
        """
        Add two mp3s with the same artist but differing umlauts for the
        album and artist names.
        """
        self.add_mp3(artist='Umläut', album='Albüm',
            title='Title 1', filename='song1.mp3')
        self.add_mp3(artist='Umlaut', album='Album',
            title='Title 2', filename='song2.mp3')
        self.run_add()

        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)

    def test_add_mp3s_mismatched_japanese_artists(self):
        """
        Adds two files with different artist names using Japanese characters,
        to ensure that our artist-comparison normalization stuff keeps them
        separate instead of collapsing them into a single artist.

        Characters taken from a search for "test" at google.co.jp,
        hopefully they are nothing offensive.  :)
        """
        self.add_mp3(artist='\u81EA\u52D5\u8ABF', album='Album',
            title='Title 1', filename='song1.mp3', path='Album1')
        self.add_mp3(artist='\u30AB\u30CA\u30C0', album='Album',
            title='Title 2', filename='song2.mp3', path='Album2')
        self.run_add()
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 3)
        self.assertEqual(Album.objects.count(), 2)

    def test_add_mp3s_mismatched_japanese_artists_group(self):
        """
        Adds two files with different artist names using Japanese characters,
        to ensure that our artist-comparison normalization stuff keeps them
        separate instead of collapsing them into a single artist.  Also tests
        the same functionality with groups.

        Characters taken from a search for "test" at google.co.jp,
        hopefully they are nothing offensive.  :)
        """
        self.add_mp3(artist='\u81EA\u52D5\u8ABF', group='\u30AB\u30CA\u30C0',
            album='Album', title='Title 1', filename='song1.mp3', path='Album1')
        self.add_mp3(artist='\u30AB\u30CA\u30C0', group='\u81EA\u52D5\u8ABF',
            album='Album', title='Title 2', filename='song2.mp3', path='Album2')
        self.run_add()
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 3)
        self.assertEqual(Album.objects.count(), 2)

    def test_add_mp3s_mismatched_japanese_artists_conductor(self):
        """
        Adds two files with different artist names using Japanese characters,
        to ensure that our artist-comparison normalization stuff keeps them
        separate instead of collapsing them into a single artist.  Also tests
        the same functionality with conductors.

        Characters taken from a search for "test" at google.co.jp,
        hopefully they are nothing offensive.  :)
        """
        self.add_mp3(artist='\u81EA\u52D5\u8ABF', conductor='\u30AB\u30CA\u30C0',
            album='Album', title='Title 1', filename='song1.mp3', path='Album1')
        self.add_mp3(artist='\u30AB\u30CA\u30C0', conductor='\u81EA\u52D5\u8ABF',
            album='Album', title='Title 2', filename='song2.mp3', path='Album2')
        self.run_add()
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 3)
        self.assertEqual(Album.objects.count(), 2)

    def test_add_mp3s_mismatched_japanese_artists_composer(self):
        """
        Adds two files with different artist names using Japanese characters,
        to ensure that our artist-comparison normalization stuff keeps them
        separate instead of collapsing them into a single artist.  Also tests
        the same functionality with composers.

        Characters taken from a search for "test" at google.co.jp,
        hopefully they are nothing offensive.  :)
        """
        self.add_mp3(artist='\u81EA\u52D5\u8ABF', composer='\u30AB\u30CA\u30C0',
            album='Album', title='Title 1', filename='song1.mp3', path='Album1')
        self.add_mp3(artist='\u30AB\u30CA\u30C0', composer='\u81EA\u52D5\u8ABF',
            album='Album', title='Title 2', filename='song2.mp3', path='Album2')
        self.run_add()
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 3)
        self.assertEqual(Album.objects.count(), 2)

    def test_add_mp3s_same_japanese_artists(self):
        """
        Adds two files with the same artist name using Japanese characters,
        to ensure that our artist-comparison normalization stuff keeps them
        together.
        """
        self.add_mp3(artist='\u81EA\u52D5\u8ABF', album='Album',
            title='Title 1', filename='song1.mp3')
        self.add_mp3(artist='\u81EA\u52D5\u8ABF', album='Album',
            title='Title 2', filename='song2.mp3')
        self.run_add()
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)

    def test_add_song_same_japanese_artist_group(self):
        """
        Adds one files with the same artist/group name using Japanese characters,
        to ensure that our artist-comparison normalization stuff keeps them
        together.
        """
        self.add_mp3(artist='\u81EA\u52D5\u8ABF', group='\u81EA\u52D5\u8ABF',
            album='Album', title='Title 1', filename='song1.mp3')
        self.run_add()
        self.assertEqual(Song.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)

    def test_add_song_same_japanese_artist_conductor(self):
        """
        Adds one files with the same artist/conductor name using Japanese characters,
        to ensure that our artist-comparison normalization stuff keeps them
        together.
        """
        self.add_mp3(artist='\u81EA\u52D5\u8ABF', conductor='\u81EA\u52D5\u8ABF',
            album='Album', title='Title 1', filename='song1.mp3')
        self.run_add()
        self.assertEqual(Song.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)

    def test_add_song_same_japanese_artist_composer(self):
        """
        Adds one files with the same artist/composer name using Japanese characters,
        to ensure that our artist-comparison normalization stuff keeps them
        together.
        """
        self.add_mp3(artist='\u81EA\u52D5\u8ABF', composer='\u81EA\u52D5\u8ABF',
            album='Album', title='Title 1', filename='song1.mp3')
        self.run_add()
        self.assertEqual(Song.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)

    def test_add_songs_same_japanese_artists_and_groups(self):
        """
        Adds two files with the same artist name using Japanese characters,
        to ensure that our artist-comparison normalization stuff keeps them
        together.  Also test groups.
        """
        self.add_mp3(artist='\u81EA\u52D5\u8ABF', group='\u81EA\u52D5\u8ABF',
            album='Album', title='Title 1', filename='song1.mp3')
        self.add_mp3(artist='\u81EA\u52D5\u8ABF', group='\u81EA\u52D5\u8ABF',
            album='Album', title='Title 2', filename='song2.mp3')
        self.run_add()
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)

    def test_add_songs_same_japanese_artists_and_conductors(self):
        """
        Adds two files with the same artist name using Japanese characters,
        to ensure that our artist-comparison normalization stuff keeps them
        together.  Also test conductors.
        """
        self.add_mp3(artist='\u81EA\u52D5\u8ABF', conductor='\u81EA\u52D5\u8ABF',
            album='Album', title='Title 1', filename='song1.mp3')
        self.add_mp3(artist='\u81EA\u52D5\u8ABF', conductor='\u81EA\u52D5\u8ABF',
            album='Album', title='Title 2', filename='song2.mp3')
        self.run_add()
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)

    def test_add_songs_same_japanese_artists_and_composers(self):
        """
        Adds two files with the same artist name using Japanese characters,
        to ensure that our artist-comparison normalization stuff keeps them
        together.  Also test composers.
        """
        self.add_mp3(artist='\u81EA\u52D5\u8ABF', composer='\u81EA\u52D5\u8ABF',
            album='Album', title='Title 1', filename='song1.mp3')
        self.add_mp3(artist='\u81EA\u52D5\u8ABF', composer='\u81EA\u52D5\u8ABF',
            album='Album', title='Title 2', filename='song2.mp3')
        self.run_add()
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)

    def test_add_mp3s_mismatched_japanese_albums(self):
        """
        Adds two files with different album names using Japanese characters,
        to ensure that our album-comparison normalization stuff keeps them
        separate instead of collapsing them into a single album.

        Characters taken from a search for "test" at google.co.jp,
        hopefully they are nothing offensive.  :)
        """
        self.add_mp3(artist='Artist', album='\u81EA\u52D5\u8ABF',
            title='Title 1', filename='song1.mp3')
        self.add_mp3(artist='Artist', album='\u30AB\u30CA\u30C0',
            title='Title 2', filename='song2.mp3')
        self.run_add()
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 2)

    def test_add_mp3s_mismatched_aesc_artist(self):
        """
        Adds two files with artist names which differ in that one uses an "æ" char
        and the other uses "ae".  Should both normalize to the same artist.
        """
        self.add_mp3(artist='Mediæval', title='Title 1', filename='song1.mp3')
        self.add_mp3(artist='Mediaeval', title='Title 2', filename='song2.mp3')
        self.run_add()
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 2)

    def test_add_song_mismatched_aesc_artist_group(self):
        """
        Adds one files with artist/group names which differ in that one uses an
        "æ" char and the other uses "ae".  Should both normalize to the same artist.
        """
        self.add_mp3(artist='Mediæval', group='Mediaeval',title='Title 1', filename='song1.mp3')
        self.run_add()
        self.assertEqual(Song.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)

    def test_add_song_mismatched_aesc_artist_conductor(self):
        """
        Adds one files with artist/conductor names which differ in that one uses an
        "æ" char and the other uses "ae".  Should both normalize to the same artist.
        """
        self.add_mp3(artist='Mediæval', conductor='Mediaeval',title='Title 1', filename='song1.mp3')
        self.run_add()
        self.assertEqual(Song.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)

    def test_add_song_mismatched_aesc_artist_composer(self):
        """
        Adds one files with artist/composer names which differ in that one uses an
        "æ" char and the other uses "ae".  Should both normalize to the same artist.
        """
        self.add_mp3(artist='Mediæval', composer='Mediaeval',title='Title 1', filename='song1.mp3')
        self.run_add()
        self.assertEqual(Song.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)

    def test_add_songs_mismatched_aesc_artist_and_group(self):
        """
        Adds two files with artist/group names which differ in that one uses an "æ" char
        and the other uses "ae".  Should both normalize to the same artist.
        """
        self.add_mp3(artist='Mediæval', group='Mediaeval',title='Title 1', filename='song1.mp3')
        self.add_mp3(artist='Mediaeval', group='Mediæval',title='Title 2', filename='song2.mp3')
        self.run_add()
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 2)

    def test_add_songs_mismatched_aesc_artist_and_conductor(self):
        """
        Adds two files with artist/conductor names which differ in that one uses an "æ" char
        and the other uses "ae".  Should both normalize to the same artist.
        """
        self.add_mp3(artist='Mediæval', conductor='Mediaeval',title='Title 1', filename='song1.mp3')
        self.add_mp3(artist='Mediaeval', conductor='Mediæval',title='Title 2', filename='song2.mp3')
        self.run_add()
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 2)

    def test_add_songs_mismatched_aesc_artist_and_composer(self):
        """
        Adds two files with artist/composer names which differ in that one uses an "æ" char
        and the other uses "ae".  Should both normalize to the same artist.
        """
        self.add_mp3(artist='Mediæval', composer='Mediaeval',title='Title 1', filename='song1.mp3')
        self.add_mp3(artist='Mediaeval', composer='Mediæval',title='Title 2', filename='song2.mp3')
        self.run_add()
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 2)

    def test_add_mp3s_mismatched_aesc_album(self):
        """
        Adds two files with album names which differ in that one uses an "æ" char
        and the other uses "ae".  Should both normalize to the same album.
        """
        self.add_mp3(artist='Artist', album='Mediæval',
            title='Title 1', filename='song1.mp3')
        self.add_mp3(artist='Artist', album='Mediaeval',
            title='Title 2', filename='song2.mp3')
        self.run_add()
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)

    def test_add_mp3s_mismatched_slashed_o_artist(self):
        """
        Adds two files with artist names which differ in that one uses an "ø" char
        and the other uses "o".  Should both normalize to the same artist.
        """
        self.add_mp3(artist='søster', title='Title 1', filename='song1.mp3')
        self.add_mp3(artist='soster', title='Title 2', filename='song2.mp3')
        self.run_add()
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 2)

    def test_add_mp3s_mismatched_slashed_o_album(self):
        """
        Adds two files with album names which differ in that one uses an "ø" char
        and the other uses "o".  Should both normalize to the same album.
        """
        self.add_mp3(artist='Artist', album='søster',
            title='Title 1', filename='song1.mp3')
        self.add_mp3(artist='Artist', album='soster',
            title='Title 2', filename='song2.mp3')
        self.run_add()
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)

    def test_add_mp3_artist_prefix(self):
        """
        Adds a single track with an artist name "The Artist" to check for
        proper prefix handling.
        """
        self.add_mp3(artist='The Artist', title='Title')
        self.run_add()

        artist = Artist.objects.get(name='Artist')
        self.assertEqual(artist.name, 'Artist')
        self.assertEqual(artist.prefix, 'The')

    def test_add_classical_simple_tag_check_prefixes(self):
        """
        Adds a single fully-tagged track and check that the resulting database
        objects are all populated properly.  This time with a prefix on all
        the artist fields.
        """
        self.add_mp3(artist='The Artist', title='Title', album='Album',
            group='The Group', conductor='The Conductor', composer='The Composer',
            year=1970, tracknum=1)
        self.run_add()

        self.assertEqual(Song.objects.count(), 1)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 5)

        artist = Artist.objects.get(name='Artist')
        self.assertEqual(artist.name, 'Artist')
        self.assertEqual(artist.prefix, 'The')

        artist = Artist.objects.get(name='Group')
        self.assertEqual(artist.name, 'Group')
        self.assertEqual(artist.prefix, 'The')

        artist = Artist.objects.get(name='Conductor')
        self.assertEqual(artist.name, 'Conductor')
        self.assertEqual(artist.prefix, 'The')

        artist = Artist.objects.get(name='Composer')
        self.assertEqual(artist.name, 'Composer')
        self.assertEqual(artist.prefix, 'The')

    def test_add_mp3_artist_prefix_double_spaces(self):
        """
        Adds a single track with an artist name "The  Artist" to check for
        proper prefix handling, with more space than necessary between the
        prefix and the actual artist name.
        """
        self.add_mp3(artist='The  Artist', title='Title')
        self.run_add()

        artist = Artist.objects.get(name='Artist')
        self.assertEqual(artist.name, 'Artist')
        self.assertEqual(artist.prefix, 'The')

    def test_add_classical_prfix_double_spaces_full(self):
        """
        Adds a single fully-tagged track with some improper spaces between
        prefix and artist name - clean out the space and do the right thing.
        """
        self.add_mp3(artist='The  Artist', title='Title', group='The  Group',
                conductor='The  Conductor', composer='The  Composer')
        self.run_add()

        self.assertEqual(Song.objects.count(), 1)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 5)

        artist = Artist.objects.get(name='Artist')
        self.assertEqual(artist.name, 'Artist')
        self.assertEqual(artist.prefix, 'The')

        artist = Artist.objects.get(name='Group')
        self.assertEqual(artist.name, 'Group')
        self.assertEqual(artist.prefix, 'The')

        artist = Artist.objects.get(name='Conductor')
        self.assertEqual(artist.name, 'Conductor')
        self.assertEqual(artist.prefix, 'The')

        artist = Artist.objects.get(name='Composer')
        self.assertEqual(artist.name, 'Composer')
        self.assertEqual(artist.prefix, 'The')

    def test_add_mp3_with_exterior_spaces(self):
        """
        Adds a single track with both artist and album tags having extra
        spaces on the outside of the name.  Spaces should be stripped
        off.
        """
        self.add_mp3(artist=' Artist ', album=' Album ', title='Title')
        self.run_add()

        self.assertEqual(Song.objects.count(), 1)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)

        artist = Artist.objects.get(name='Artist')
        self.assertEqual(artist.name, 'Artist')
        album = Album.objects.get(name='Album')
        self.assertEqual(album.name, 'Album')

    def test_add_mp3_with_trailing_nulls(self):
        """
        Adds a single track with both artist and album tags having an
        extra NULL character at the end of the string.  The null char
        should be stripped out.
        """
        self.add_mp3(artist="Artist\x00", album="Album\x00", title="Title\x00")
        self.run_add()

        self.assertEqual(Song.objects.count(), 1)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)

        artist = Artist.objects.get(name='Artist')
        self.assertEqual(artist.name, 'Artist')
        album = Album.objects.get(name='Album')
        self.assertEqual(album.name, 'Album')
        song = Song.objects.get()
        self.assertEqual(song.title, 'Title')

    def test_add_mp3_normalize_title(self):
        """
        Test to ensure that song title normalization is working properly.
        """
        self.add_mp3(artist='Artist', title='Title: øÆ & ü')
        self.run_add()

        self.assertEqual(Song.objects.count(), 1)
        song = Song.objects.get()
        self.assertEqual(song.title, 'Title: øÆ & ü')
        self.assertEqual(song.normtitle, 'title: oae and u')

    def test_add_mp3_no_album(self):
        """
        Adds an mp3 without an album to check that it's properly sorted
        into a 'Non-Album Tracks' album.
        """
        self.add_mp3(artist='Artist', title='Title')
        self.run_add()

        album_title = Album.miscellaneous_format_str % ('Artist')
        album = Album.objects.get()
        self.assertEqual(str(album), album_title)

    def test_add_mp3_no_album_two_stage(self):
        """
        Adds an mp3 without an album to check that it's properly sorted
        into a 'Non-Album Tracks' album, and then add a second using
        an umlaut to test out our matching abilities there
        """
        self.add_mp3(artist='Artist', title='Title', filename='song1.mp3')
        self.run_add()

        # Preliminary checks
        album_title = Album.miscellaneous_format_str % ('Artist')
        self.assertEqual(Song.objects.count(), 1)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)
        album = Album.objects.get()
        self.assertEqual(album.miscellaneous, True)
        self.assertEqual(str(album), album_title)

        # Another add
        self.add_mp3(artist='Ärtist', title='Title 2', filename='song2.mp3')
        self.run_add()

        # Now the real checks
        album_title = Album.miscellaneous_format_str % ('Artist')
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)
        album = Album.objects.get()
        self.assertEqual(album.miscellaneous, True)
        self.assertEqual(str(album), album_title)
        self.assertEqual(album.song_set.count(), 2)

    def test_add_mp3_no_album_two_stage_aesc(self):
        """
        Adds an mp3 without an album to check that it's properly sorted
        into a 'Non-Album Tracks' album, and then add a second using
        an aesc to test out our matching abilities there.
        """
        self.add_mp3(artist='Aertist', title='Title', filename='song1.mp3')
        self.run_add()

        # Preliminary checks
        album_title = Album.miscellaneous_format_str % ('Aertist')
        self.assertEqual(Song.objects.count(), 1)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)
        album = Album.objects.get()
        self.assertEqual(album.miscellaneous, True)
        self.assertEqual(str(album), album_title)

        # Another add
        self.add_mp3(artist='Ærtist', title='Title 2', filename='song2.mp3')
        self.run_add()

        # Now the real checks
        album_title = Album.miscellaneous_format_str % ('Aertist')
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)
        album = Album.objects.get()
        self.assertEqual(album.miscellaneous, True)
        self.assertEqual(str(album), album_title)
        self.assertEqual(album.song_set.count(), 2)

    def test_add_mp3_two_song_album(self):
        """
        Adds two mp3s which should be in the same album.
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='1-title_1.mp3')
        self.add_mp3(artist='Artist', title='Title 2',
            album='Album', filename='2-title_2.mp3')
        self.run_add()

        album = Album.objects.get()
        self.assertEqual(album.name, 'Album')
        self.assertEqual(album.artist.name, 'Artist')
        self.assertEqual(album.song_set.count(), 2)

    def test_add_mp3_two_alternating_prefix(self):
        """
        Add one mp3 with the artist name "The Artist"
        and then a second with the artist name "Artist".
        Both should be associated with the same base
        Artist name.
        """
        self.add_mp3(artist='The Artist', title='Title 1',
            album='Album 1', filename='album_1.mp3')
        self.run_add()
        self.add_mp3(artist='Artist', title='Title 2',
            album='Album 2', filename='album_2.mp3')
        self.run_add()

        for artist in Artist.objects.all():
            if artist.name != 'Various':
                self.assertEqual(artist.name, 'Artist')
                self.assertEqual(artist.prefix, 'The')
        for song in Song.objects.all():
            self.assertEqual(song.artist.name, 'Artist')

    def test_add_mp3_two_alternating_prefix_group(self):
        """
        Add one mp3 with the artist name "The Artist"
        and then a second with a group name "Artist".
        Both should be associated with the same base
        Artist name.
        """
        self.add_mp3(artist='The Artist', title='Title 1',
            album='Album 1', filename='album_1.mp3')
        self.run_add()
        self.add_mp3(artist='The Artist', group='Artist',
            title='Title 2', album='Album 2', filename='album_2.mp3')
        self.run_add()

        for artist in Artist.objects.all():
            if artist.name != 'Various':
                self.assertEqual(artist.name, 'Artist')
                self.assertEqual(artist.prefix, 'The')
        song = Song.objects.get(filename='album_2.mp3')
        self.assertEqual(song.group.name, 'Artist')

    def test_add_mp3_two_alternating_prefix_conductor(self):
        """
        Add one mp3 with the artist name "The Artist"
        and then a second with a conductor name "Artist".
        Both should be associated with the same base
        Artist name.
        """
        self.add_mp3(artist='The Artist', title='Title 1',
            album='Album 1', filename='album_1.mp3')
        self.run_add()
        self.add_mp3(artist='The Artist', conductor='Artist',
            title='Title 2', album='Album 2', filename='album_2.mp3')
        self.run_add()

        for artist in Artist.objects.all():
            if artist.name != 'Various':
                self.assertEqual(artist.name, 'Artist')
                self.assertEqual(artist.prefix, 'The')
        song = Song.objects.get(filename='album_2.mp3')
        self.assertEqual(song.conductor.name, 'Artist')

    def test_add_mp3_two_alternating_prefix_composer(self):
        """
        Add one mp3 with the artist name "The Artist"
        and then a second with a composer name "Artist".
        Both should be associated with the same base
        Artist name.
        """
        self.add_mp3(artist='The Artist', title='Title 1',
            album='Album 1', filename='album_1.mp3')
        self.run_add()
        self.add_mp3(artist='The Artist', composer='Artist',
            title='Title 2', album='Album 2', filename='album_2.mp3')
        self.run_add()

        for artist in Artist.objects.all():
            if artist.name != 'Various':
                self.assertEqual(artist.name, 'Artist')
                self.assertEqual(artist.prefix, 'The')
        song = Song.objects.get(filename='album_2.mp3')
        self.assertEqual(song.composer.name, 'Artist')

    def test_add_mp3_two_alternating_prefix_reverse(self):
        """
        Add one mp3 with the artist name "Artist" and
        then a second one with the artist name "The Artist".
        The artist record should be updated to have a
        prefix.
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album 1', filename='album_1.mp3')
        self.run_add()

        artist = Artist.objects.get(name='Artist')
        self.assertEqual(artist.name, 'Artist')
        self.assertEqual(artist.prefix, '')

        self.add_mp3(artist='The Artist', title='Title 2',
            album='Album 2', filename='album_2.mp3')
        self.run_add()

        artist = Artist.objects.get(name='Artist')
        self.assertEqual(artist.name, 'Artist')
        self.assertEqual(artist.prefix, 'The')

    def test_add_mp3_two_alternating_prefix_reverse_by_group(self):
        """
        Add one mp3 with the artist name "Artist" and
        then a second one with a group name "The Artist".
        The artist record should be updated to have a
        prefix.
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album 1', filename='album_1.mp3')
        self.run_add()

        artist = Artist.objects.get(name='Artist')
        self.assertEqual(artist.name, 'Artist')
        self.assertEqual(artist.prefix, '')

        self.add_mp3(artist='Artist', title='Title 2',
            group='The Artist',
            album='Album 2', filename='album_2.mp3')
        self.run_add()

        artist = Artist.objects.get(name='Artist')
        self.assertEqual(artist.name, 'Artist')
        self.assertEqual(artist.prefix, 'The')

    def test_add_mp3_two_alternating_prefix_reverse_by_conductor(self):
        """
        Add one mp3 with the artist name "Artist" and
        then a second one with a conductor name "The Artist".
        The artist record should be updated to have a
        prefix.
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album 1', filename='album_1.mp3')
        self.run_add()

        artist = Artist.objects.get(name='Artist')
        self.assertEqual(artist.name, 'Artist')
        self.assertEqual(artist.prefix, '')

        self.add_mp3(artist='Artist', title='Title 2',
            conductor='The Artist',
            album='Album 2', filename='album_2.mp3')
        self.run_add()

        artist = Artist.objects.get(name='Artist')
        self.assertEqual(artist.name, 'Artist')
        self.assertEqual(artist.prefix, 'The')

    def test_add_mp3_two_alternating_prefix_reverse_by_composer(self):
        """
        Add one mp3 with the artist name "Artist" and
        then a second one with a composer name "The Artist".
        The artist record should be updated to have a
        prefix.
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album 1', filename='album_1.mp3')
        self.run_add()

        artist = Artist.objects.get(name='Artist')
        self.assertEqual(artist.name, 'Artist')
        self.assertEqual(artist.prefix, '')

        self.add_mp3(artist='Artist', title='Title 2',
            composer='The Artist',
            album='Album 2', filename='album_2.mp3')
        self.run_add()

        artist = Artist.objects.get(name='Artist')
        self.assertEqual(artist.name, 'Artist')
        self.assertEqual(artist.prefix, 'The')

    def test_add_various_artists_album(self):
        """
        Test adding a various-artists album.
        """
        tracks = [
            ('1-title_1.mp3', 'Artist 1', 'Title 1', 1),
            ('2-title_2.mp3', 'Artist 2', 'Title 2', 2),
        ]
        for (filename, artist, title, tracknum) in tracks:
            self.add_mp3(artist=artist, title=title, album='Album',
                tracknum=tracknum, filename=filename)
        self.run_add()

        # First check that we have three total artists, and that
        # they're what we expect
        self.assertEqual(Artist.objects.count(), 3)
        va = Artist.objects.get(name='Various')
        self.assertEqual(va.name, 'Various')
        a1 = Artist.objects.get(name='Artist 1')
        self.assertEqual(a1.name, 'Artist 1')
        a2 = Artist.objects.get(name='Artist 2')
        self.assertEqual(a2.name, 'Artist 2')

        # Now check that there's just one album and that IT is
        # how we expect.
        self.assertEqual(Album.objects.count(), 1)
        album = Album.objects.get()
        self.assertEqual(album.name, 'Album')
        self.assertEqual(album.artist.name, 'Various')
        self.assertEqual(album.song_set.count(), 2)

        # Aaand check the individual songs
        for (filename, artist, title, tracknum) in tracks:
            song = Song.objects.get(filename=filename)
            self.assertEqual(song.title, title)
            self.assertEqual(song.artist.name, artist)
            self.assertEqual(song.album.name, 'Album')
            self.assertEqual(song.album.artist.name, 'Various')
            self.assertEqual(song.tracknum, tracknum)

    def test_add_va_album_and_normal_album(self):
        """
        Create a Various Artists album, and at the same time another
        album belonging to one of the artists on the VA comp.
        """
        tracks = [
            ('Various', '1-title_1.mp3', 'Artist 1', 'Title 1', 1),
            ('Various', '2-title_2.mp3', 'Artist 2', 'Title 2', 2),
            ('Album', '1-first.mp3', 'Artist 1', 'First', 1),
            ('Album', '2-second.mp3', 'Artist 1', 'Second', 2),
        ]
        for (path, filename, artist, title, tracknum) in tracks:
            self.add_mp3(path=path, filename=filename, artist=artist,
                title=title, tracknum=tracknum, album=path)
        self.run_add()

        # First check that we have three total artists, and that
        # they're what we expect
        self.assertEqual(Artist.objects.count(), 3)
        va = Artist.objects.get(name='Various')
        self.assertEqual(va.name, 'Various')
        self.assertEqual(va.album_set.count(), 1)
        a1 = Artist.objects.get(name='Artist 1')
        self.assertEqual(a1.name, 'Artist 1')
        self.assertEqual(a1.album_set.count(), 1)
        a2 = Artist.objects.get(name='Artist 2')
        self.assertEqual(a2.name, 'Artist 2')
        self.assertEqual(a2.album_set.count(), 0)

        # Now check for two albums
        self.assertEqual(Album.objects.count(), 2)
        various = Album.objects.get(name='Various')
        self.assertEqual(various.name, 'Various')
        self.assertEqual(various.artist.name, 'Various')
        self.assertEqual(various.song_set.count(), 2)
        single = Album.objects.get(name='Album')
        self.assertEqual(single.name, 'Album')
        self.assertEqual(single.artist.name, 'Artist 1')
        self.assertEqual(single.song_set.count(), 2)

        # Now check the individual album tracks
        for song in various.song_set.all():
            self.assertNotEqual(song.artist.name, 'Various')
            self.assertEqual(song.album.name, 'Various')
            self.assertEqual(song.album.artist.name, 'Various')
        for song in single.song_set.all():
            self.assertEqual(song.artist.name, 'Artist 1')
            self.assertEqual(song.album.name, 'Album')
            self.assertEqual(song.album.artist.name, 'Artist 1')

    def test_add_normal_track_to_normal_album(self):
        """
        Create a single-artist album and then add another track to the
        album (by the same artist).
        """
        tracks = [
            ('Album', '1-first.mp3', 'Artist 1', 'First', 1),
            ('Album', '2-second.mp3', 'Artist 1', 'Second', 2),
        ]
        for (path, filename, artist, title, tracknum) in tracks:
            self.add_mp3(path=path, filename=filename, artist=artist,
                title=title, tracknum=tracknum, album=path)
        self.run_add()

        # Just verify that the album is Artist 1
        album = Album.objects.get(name='Album')
        self.assertEqual(album.name, 'Album')
        self.assertEqual(album.artist.name, 'Artist 1')

        # Now add the new track
        self.add_mp3(path='Album', filename='3-third.mp3',
            artist='Artist 1', title='Third', tracknum=3,
            album='Album')
        self.run_add()

        # Verify that we only have one album, and that it's still Artist 1
        self.assertEqual(Album.objects.count(), 1)
        album = Album.objects.get(name='Album')
        self.assertEqual(album.song_set.count(), 3)
        self.assertEqual(album.artist.name, 'Artist 1')

    def test_add_va_track_to_va_album(self):
        """
        Create a various-artist album and then add another track to the
        album.
        """
        tracks = [
            ('Album', '1-first.mp3', 'Artist 1', 'First', 1),
            ('Album', '2-second.mp3', 'Artist 2', 'Second', 2),
        ]
        for (path, filename, artist, title, tracknum) in tracks:
            self.add_mp3(path=path, filename=filename, artist=artist,
                title=title, tracknum=tracknum, album=path)
        self.run_add()

        # Just verify that the album is Various
        album = Album.objects.get(name='Album')
        self.assertEqual(album.name, 'Album')
        self.assertEqual(album.artist.name, 'Various')

        # Now add the new track
        self.add_mp3(path='Album', filename='3-third.mp3',
            artist='Artist 3', title='Third', tracknum=3,
            album='Album')
        self.run_add()

        # Verify that we only have one album, and that it's still VA
        self.assertEqual(Album.objects.count(), 1)
        album = Album.objects.get(name='Album')
        self.assertEqual(album.song_set.count(), 3)
        self.assertEqual(album.artist.name, 'Various')

    def test_add_va_track_to_non_va_album(self):
        """
        Create a regular single-artist album and then add a track to the
        album which turns it into a Various Artists album.
        """
        tracks = [
            ('Album', '1-first.mp3', 'Artist 1', 'First', 1),
            ('Album', '2-second.mp3', 'Artist 1', 'Second', 2),
        ]
        for (path, filename, artist, title, tracknum) in tracks:
            self.add_mp3(path=path, filename=filename, artist=artist,
                title=title, tracknum=tracknum, album=path)
        self.run_add()

        # Just verify that the album is Artist 1 quick
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)
        album = Album.objects.get(name='Album')
        self.assertEqual(album.name, 'Album')
        self.assertEqual(album.artist.name, 'Artist 1')

        # Now add the new track
        self.add_mp3(path='Album', filename='3-third.mp3',
            artist='Artist 2', title='Third', tracknum=3,
            album='Album')
        self.run_add()

        # Verify that we only have one album, and that it's changed
        self.assertEqual(Album.objects.count(), 1)
        album = Album.objects.get(name='Album')
        self.assertEqual(album.song_set.count(), 3)
        self.assertEqual(album.artist.name, 'Various')

    def test_add_two_regular_albums_with_same_album_name(self):
        """
        Test behavior when two regular albums are added with the same
        album name.  This is a subpar situation and may result in
        problems down the line, but for now the expected behavior
        is that there will be a single regular album containing tracks
        from both directories.
        """
        tracks = [
            ('al1', 'Album', '1-first.mp3', 'Artist 1', 'First', 1),
            ('al1', 'Album', '2-second.mp3', 'Artist 1', 'Second', 2),
            ('al2', 'Album', '1-first.mp3', 'Artist 1', 'First', 1),
            ('al2', 'Album', '2-second.mp3', 'Artist 1', 'Second', 2),
        ]
        for (path, album, filename, artist, title, tracknum) in tracks:
            self.add_mp3(path=path, filename=filename, artist=artist,
                title=title, tracknum=tracknum, album=album)
        self.run_add()

        # Some simple checks
        self.assertEqual(Song.objects.count(), 4)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)
        album = Album.objects.get()
        self.assertEqual(album.song_set.count(), 4)
        for song in Song.objects.all():
            self.assertEqual(song.album.name, 'Album')
            self.assertEqual(song.album.artist.name, 'Artist 1')
            self.assertEqual(song.artist.name, 'Artist 1')

    def test_add_two_va_albums_with_same_album_name(self):
        """
        Test behavior when two V/A albums are added with the same
        album name.  This is a subpar situation and may result in
        problems down the line, but for now the expected behavior
        is that there will be a single V/A album containing tracks
        from both directories.
        """
        tracks = [
            ('va1', 'Album', '1-first.mp3', 'Artist 1', 'First', 1),
            ('va1', 'Album', '2-second.mp3', 'Artist 2', 'Second', 2),
            ('va2', 'Album', '1-first.mp3', 'Artist 3', 'First', 1),
            ('va2', 'Album', '2-second.mp3', 'Artist 4', 'Second', 2),
        ]
        for (path, album, filename, artist, title, tracknum) in tracks:
            self.add_mp3(path=path, filename=filename, artist=artist,
                title=title, tracknum=tracknum, album=album)
        self.run_add()

        # Some simple checks
        self.assertEqual(Song.objects.count(), 4)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 5)
        album = Album.objects.get()
        self.assertEqual(album.song_set.count(), 4)
        for song in Song.objects.all():
            self.assertEqual(song.album.name, 'Album')
            self.assertEqual(song.album.artist.name, 'Various')

    def test_add_live_album(self):
        """
        Simple test to add an album with a title which will mark it as
        being "live"
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='2016-09-20 - Live at Somewhere',
            filename='song1.mp3')
        self.run_add()

        self.assertEqual(Song.objects.count(), 1)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)
        album = Album.objects.get()
        self.assertEqual(album.live, True)

class BasicUpdateAsAddTests(BasicAddTests):
    """
    This is a bit of nonsense.  Basically, all tests for add() should be
    repeated for update(), since add() is technically a subset of update().
    Rather than rewriting everything, we're just subclassing and
    overriding the ``run_add()`` method so that all calls to ``run_add()``
    end up doing an update instead.
    """

    def run_add(self):
        """
        Runs an ``update`` operation on our library while pretending to be
        ``add``, and checks for errors.
        """
        return self.assertNoErrors(list(App.update()))

    def run_add_errors(self, errors_min=1, error=None):
        """
        Runs an ``update`` operation on our library while pretending to be
        ``add``, and ensures that there's at least one error
        """
        return self.assertErrors(list(App.update()), errors_min, error=error)

class BasicUpdateTests(ExordiumTests):
    """
    Tests for the update procedure - this time, tests specifically related
    to the update() call, rather than fiddling around.
    """

    def test_basic_update(self):
        """
        Test a simple track update to the title.
        """
        self.add_mp3(filename='song.mp3', artist='Artist', title='Title')
        self.run_add()

        # Quick verification
        song = Song.objects.get()
        self.assertEqual(song.artist.name, 'Artist')
        self.assertEqual(song.title, 'Title')

        # Now make some changes.
        self.update_mp3(filename='song.mp3', title='New Title Æ')
        self.run_update()

        # Now the real verifications
        song = Song.objects.get()
        self.assertEqual(song.artist.name, 'Artist')
        self.assertEqual(song.title, 'New Title Æ')
        self.assertEqual(song.normtitle, 'new title ae')

    def test_basic_update_ogg(self):
        """
        Test a simple track update to the title, on an ogg file.  (This
        is really more testing our ogg update function than it is Exordium,
        at this point.)
        """
        self.add_ogg(filename='song.ogg', artist='Artist', title='Title')
        self.run_add()

        # Quick verification
        song = Song.objects.get()
        self.assertEqual(song.artist.name, 'Artist')
        self.assertEqual(song.title, 'Title')

        # Now make some changes.
        self.update_ogg(filename='song.ogg', title='New Title Æ')
        self.run_update()

        # Now the real verifications
        song = Song.objects.get()
        self.assertEqual(song.artist.name, 'Artist')
        self.assertEqual(song.title, 'New Title Æ')
        self.assertEqual(song.normtitle, 'new title ae')

    def test_basic_update_m4a(self):
        """
        Test a simple track update to the title, on an m4a file.  (This
        is really more testing our m4a update function than it is Exordium,
        at this point.)
        """
        self.add_m4a(filename='song.m4a', artist='Artist', title='Title')
        self.run_add()

        # Quick verification
        song = Song.objects.get()
        self.assertEqual(song.artist.name, 'Artist')
        self.assertEqual(song.title, 'Title')

        # Now make some changes.
        self.update_m4a(filename='song.m4a', title='New Title Æ')
        self.run_update()

        # Now the real verifications
        song = Song.objects.get()
        self.assertEqual(song.artist.name, 'Artist')
        self.assertEqual(song.title, 'New Title Æ')
        self.assertEqual(song.normtitle, 'new title ae')

    def test_update_file_no_longer_readable(self):
        """
        Test an update where the file becomes no longer readable.  We'll
        err on the side of caution and NOT remove the data, for now.
        """
        self.add_mp3(filename='song.mp3', artist='Artist', title='Title')
        self.run_add()

        # Quick verification
        song = Song.objects.get()
        self.assertEqual(song.artist.name, 'Artist')
        self.assertEqual(song.title, 'Title')

        # Now make some changes.
        self.update_mp3(filename='song.mp3', title='New Title')
        self.set_file_unreadable('song.mp3')
        self.run_update_errors(error='Could not read updated information')

        # Now the real verifications
        self.assertEqual(Song.objects.count(), 1)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)

    def test_basic_album_update(self):
        """
        Test a simple track update in which the album name changes
        """
        self.add_mp3(filename='song.mp3', artist='Artist', title='Title',
            album = 'Album')
        self.run_add()

        # Quick verification
        song = Song.objects.get()
        self.assertEqual(song.album.name, 'Album')

        # Now make some changes
        self.update_mp3(filename='song.mp3', album='New Album')
        self.run_update()

        # Now the real verification
        self.assertEqual(Album.objects.count(), 1)
        album = Album.objects.get()
        self.assertEqual(album.artist.name, 'Artist')
        self.assertEqual(album.name, 'New Album')
        self.assertEqual(album.song_set.count(), 1)
        self.assertEqual(Song.objects.count(), 1)
        song = Song.objects.get()
        self.assertEqual(song.title, 'Title')
        self.assertEqual(song.album.name, 'New Album')

    def test_basic_artist_update(self):
        """
        Test a simple track update in which the artist name changes
        """
        self.add_mp3(filename='song.mp3', artist='Artist', title='Title',
            album = 'Album')
        self.run_add()

        # Quick verification
        song = Song.objects.get()
        self.assertEqual(song.artist.name, 'Artist')

        # Now make some changes
        self.update_mp3(filename='song.mp3', artist='New Artist')
        self.run_update()

        # Now the real verification
        self.assertEqual(Artist.objects.count(), 2)
        artist = Artist.objects.get(name='New Artist')
        self.assertEqual(artist.name, 'New Artist')
        self.assertEqual(Album.objects.count(), 1)
        album = Album.objects.get()
        self.assertEqual(album.artist.name, 'New Artist')
        self.assertEqual(album.name, 'Album')
        self.assertEqual(album.song_set.count(), 1)
        self.assertEqual(Song.objects.count(), 1)
        song = Song.objects.get()
        self.assertEqual(song.title, 'Title')
        self.assertEqual(song.artist.name, 'New Artist')

    def test_basic_title_update(self):
        """
        Test a simple track update in which the title changes
        """
        self.add_mp3(filename='song.mp3', artist='Artist', title='Title',
            album = 'Album')
        self.run_add()

        # Quick verification
        self.assertEqual(Song.objects.count(), 1)
        song = Song.objects.get()
        song_pk = song.pk
        self.assertEqual(song.title, 'Title')

        # Now make some changes
        self.update_mp3(filename='song.mp3', title='New Title')
        self.run_update()

        # Now the real verification
        self.assertEqual(Song.objects.count(), 1)
        song = Song.objects.get()
        self.assertEqual(song.title, 'New Title')
        self.assertEqual(song.pk, song_pk)

    def test_basic_tracknum_update(self):
        """
        Test a simple track update in which the track number changes
        """
        self.add_mp3(filename='song.mp3', artist='Artist', title='Title',
            album = 'Album', tracknum=1)
        self.run_add()

        # Quick verification
        self.assertEqual(Song.objects.count(), 1)
        song = Song.objects.get()
        song_pk = song.pk
        self.assertEqual(song.tracknum, 1)

        # Now make some changes
        self.update_mp3(filename='song.mp3', tracknum=3)
        self.run_update()

        # Now the real verification
        self.assertEqual(Song.objects.count(), 1)
        song = Song.objects.get()
        self.assertEqual(song.tracknum, 3)
        self.assertEqual(song.pk, song_pk)

    def test_basic_year_update(self):
        """
        Test a simple track update in which the year changes.  The
        album year should also be updated
        """
        self.add_mp3(filename='song.mp3', artist='Artist', title='Title',
            album = 'Album', year=2016)
        self.run_add()

        # Quick verification
        self.assertEqual(Song.objects.count(), 1)
        song = Song.objects.get()
        song_pk = song.pk
        self.assertEqual(song.year, 2016)

        self.assertEqual(Album.objects.count(), 1)
        album = Album.objects.get()
        album_pk = album.pk
        self.assertEqual(album.year, 2016)

        # Now make some changes
        self.update_mp3(filename='song.mp3', year=2006)
        self.run_update()

        # Now the real verification
        self.assertEqual(Song.objects.count(), 1)
        song = Song.objects.get()
        self.assertEqual(song.year, 2006)
        self.assertEqual(song.pk, song_pk)

        self.assertEqual(Album.objects.count(), 1)
        album = Album.objects.get()
        self.assertEqual(album.pk, album_pk)
        self.assertEqual(album.year, 2006)

    def test_basic_group_update(self):
        """
        Test a simple track update in which the group name changes
        """
        self.add_mp3(filename='song.mp3', artist='Artist', group='Group',
            title='Title', album = 'Album')
        self.run_add()

        # Quick verification
        self.assertEqual(Song.objects.count(), 1)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 3)
        song = Song.objects.get()
        self.assertEqual(song.artist.name, 'Artist')
        self.assertEqual(song.group.name, 'Group')

        # Now make some changes
        self.update_mp3(filename='song.mp3', group='New Group')
        self.run_update()

        # Now the real verification
        self.assertEqual(Artist.objects.count(), 3)
        artist = Artist.objects.get(name='New Group')
        self.assertEqual(artist.name, 'New Group')
        song = Song.objects.get()
        self.assertEqual(song.group.name, 'New Group')

    def test_basic_conductor_update(self):
        """
        Test a simple track update in which the conductor name changes
        """
        self.add_mp3(filename='song.mp3', artist='Artist', conductor='Conductor',
            title='Title', album = 'Album')
        self.run_add()

        # Quick verification
        self.assertEqual(Song.objects.count(), 1)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 3)
        song = Song.objects.get()
        self.assertEqual(song.artist.name, 'Artist')
        self.assertEqual(song.conductor.name, 'Conductor')

        # Now make some changes
        self.update_mp3(filename='song.mp3', conductor='New Conductor')
        self.run_update()

        # Now the real verification
        self.assertEqual(Artist.objects.count(), 3)
        artist = Artist.objects.get(name='New Conductor')
        self.assertEqual(artist.name, 'New Conductor')
        song = Song.objects.get()
        self.assertEqual(song.conductor.name, 'New Conductor')

    def test_basic_composer_update(self):
        """
        Test a simple track update in which the composer name changes
        """
        self.add_mp3(filename='song.mp3', artist='Artist', composer='Composer',
            title='Title', album = 'Album')
        self.run_add()

        # Quick verification
        self.assertEqual(Song.objects.count(), 1)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 3)
        song = Song.objects.get()
        self.assertEqual(song.artist.name, 'Artist')
        self.assertEqual(song.composer.name, 'Composer')

        # Now make some changes
        self.update_mp3(filename='song.mp3', composer='New Composer')
        self.run_update()

        # Now the real verification
        self.assertEqual(Artist.objects.count(), 3)
        artist = Artist.objects.get(name='New Composer')
        self.assertEqual(artist.name, 'New Composer')
        song = Song.objects.get()
        self.assertEqual(song.composer.name, 'New Composer')

    def test_basic_group_update_removed(self):
        """
        Test a simple track update in which the group name gets removed
        """
        self.add_mp3(filename='song.mp3', artist='Artist', group='Group',
            title='Title', album = 'Album')
        self.run_add()

        # Quick verification
        self.assertEqual(Song.objects.count(), 1)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 3)
        song = Song.objects.get()
        self.assertEqual(song.artist.name, 'Artist')
        self.assertEqual(song.group.name, 'Group')

        # Now make some changes
        self.update_mp3(filename='song.mp3', group='')
        self.run_update()

        # Now the real verification
        self.assertEqual(Artist.objects.count(), 2)
        song = Song.objects.get()
        self.assertEqual(song.group, None)

    def test_basic_conductor_update_removed(self):
        """
        Test a simple track update in which the conductor name gets removed
        """
        self.add_mp3(filename='song.mp3', artist='Artist', conductor='Conductor',
            title='Title', album = 'Album')
        self.run_add()

        # Quick verification
        self.assertEqual(Song.objects.count(), 1)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 3)
        song = Song.objects.get()
        self.assertEqual(song.artist.name, 'Artist')
        self.assertEqual(song.conductor.name, 'Conductor')

        # Now make some changes
        self.update_mp3(filename='song.mp3', conductor='')
        self.run_update()

        # Now the real verification
        self.assertEqual(Artist.objects.count(), 2)
        song = Song.objects.get()
        self.assertEqual(song.conductor, None)

    def test_basic_composer_update_removed(self):
        """
        Test a simple track update in which the composer name gets removed
        """
        self.add_mp3(filename='song.mp3', artist='Artist', composer='Composer',
            title='Title', album = 'Album')
        self.run_add()

        # Quick verification
        self.assertEqual(Song.objects.count(), 1)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 3)
        song = Song.objects.get()
        self.assertEqual(song.artist.name, 'Artist')
        self.assertEqual(song.composer.name, 'Composer')

        # Now make some changes
        self.update_mp3(filename='song.mp3', composer='')
        self.run_update()

        # Now the real verification
        self.assertEqual(Artist.objects.count(), 2)
        song = Song.objects.get()
        self.assertEqual(song.composer, None)

    def test_update_change_from_conductor_to_composer(self):
        """
        Test a track update in which a conductor tag moves to composer
        change around.
        """
        self.add_mp3(filename='song.mp3', artist='Artist 1', conductor='Artist 2',
            title='Title', album = 'Album')
        self.run_add()

        # Quick verification
        self.assertEqual(Song.objects.count(), 1)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 3)
        a2 = Artist.objects.get(normname='artist 2')
        a2_pk = a2.pk

        # Now make some changes
        self.update_mp3(filename='song.mp3', composer='artist 2', conductor='')
        self.run_update()

        # Now the real verification
        self.assertEqual(Song.objects.count(), 1)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 3)
        a2 = Artist.objects.get(normname='artist 2')
        self.assertEqual(a2.pk, a2_pk)
        song = Song.objects.get()
        self.assertEqual(song.conductor, None)
        self.assertEqual(song.composer.name, 'Artist 2')

    def test_update_add_classical_fields(self):
        """
        Test a track update in which we add all our classical tag
        fields to a track which previously didn't have them.
        """
        self.add_mp3(filename='song.mp3', artist='Artist',
            title='Title', album = 'Album')
        self.run_add()

        # Quick verification
        self.assertEqual(Song.objects.count(), 1)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)

        # Now make some changes
        self.update_mp3(filename='song.mp3',
            group='test 1', conductor='test 2', composer='test 3')
        self.run_update()

        # Now the real verification
        self.assertEqual(Song.objects.count(), 1)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 5)
        song = Song.objects.get()
        self.assertEqual(song.group.normname, 'test 1')
        self.assertEqual(song.conductor.normname, 'test 2')
        self.assertEqual(song.composer.normname, 'test 3')

    def test_update_classical_fields_swap(self):
        """
        Test a track update in which our classical tag fields all just
        change around.
        """
        self.add_mp3(filename='song.mp3', artist='Artist',
            composer='Test 1', group='Test 2', conductor='Test 3',
            title='Title', album = 'Album')
        self.run_add()

        # Quick verification
        self.assertEqual(Song.objects.count(), 1)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 5)
        t1 = Artist.objects.get(normname='test 1')
        t1_pk = t1.pk
        t2 = Artist.objects.get(normname='test 2')
        t2_pk = t2.pk
        t3 = Artist.objects.get(normname='test 3')
        t3_pk = t3.pk

        # Now make some changes
        self.update_mp3(filename='song.mp3',
            group='test 1', conductor='test 2', composer='test 3')
        self.run_update()

        # Now the real verification
        self.assertEqual(Song.objects.count(), 1)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 5)
        t1 = Artist.objects.get(normname='test 1')
        self.assertEqual(t1.pk, t1_pk)
        t2 = Artist.objects.get(normname='test 2')
        self.assertEqual(t2.pk, t2_pk)
        t3 = Artist.objects.get(normname='test 3')
        self.assertEqual(t3.pk, t3_pk)
        song = Song.objects.get()
        self.assertEqual(song.group.normname, 'test 1')
        self.assertEqual(song.conductor.normname, 'test 2')
        self.assertEqual(song.composer.normname, 'test 3')

    def test_basic_artist_and_album_update(self):
        """
        Test a simple track update in which the artist and album name changes
        """
        self.add_mp3(filename='song.mp3', artist='Artist', title='Title',
            album = 'Album')
        self.run_add()

        # Quick verification
        song = Song.objects.get()
        self.assertEqual(song.artist.name, 'Artist')
        self.assertEqual(song.album.name, 'Album')

        # Now make some changes
        self.update_mp3(filename='song.mp3', artist='New Artist', album='New Album')
        self.run_update()

        # Now the real verification
        self.assertEqual(Artist.objects.count(), 2)
        artist = Artist.objects.get(name='New Artist')
        self.assertEqual(artist.name, 'New Artist')
        self.assertEqual(Album.objects.count(), 1)
        album = Album.objects.get()
        self.assertEqual(album.artist.name, 'New Artist')
        self.assertEqual(album.name, 'New Album')
        self.assertEqual(album.song_set.count(), 1)
        self.assertEqual(Song.objects.count(), 1)
        song = Song.objects.get()
        self.assertEqual(song.title, 'Title')
        self.assertEqual(song.artist.name, 'New Artist')
        self.assertEqual(song.album.name, 'New Album')

    def test_update_change_artist_case_single_track(self):
        """
        Test what happens when a track gets updated with the same artist
        name but with a different case.  Since it's the only track with
        that artist name, we want the case of the artist to get updated.
        """
        self.add_mp3(artist='Artist Name', album='Album',
            title='Title 1', filename='song1.mp3')
        self.run_add()

        # Quick verification
        self.assertEqual(Song.objects.count(), 1)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)
        artist = Artist.objects.get(name='Artist Name')
        artist_pk = artist.pk

        # Update
        self.update_mp3('song1.mp3', artist='artist name')
        self.run_update()

        # Verification
        self.assertEqual(Song.objects.count(), 1)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)
        artist = Artist.objects.get(name__iexact='Artist Name')
        self.assertEqual(artist.pk, artist_pk)
        self.assertEqual(artist.name, 'artist name')

    def test_update_change_group_case_single_track(self):
        """
        Test what happens when a track gets updated with the same group
        name but with a different case.  Since it's the only track with
        that group name, we want the case of the group to get updated.
        """
        self.add_mp3(artist='Artist Name', album='Album', group='Group',
            title='Title 1', filename='song1.mp3')
        self.run_add()

        # Quick verification
        self.assertEqual(Song.objects.count(), 1)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 3)
        artist = Artist.objects.get(name='Group')
        artist_pk = artist.pk

        # Update
        self.update_mp3('song1.mp3', group='group')
        self.run_update()

        # Verification
        self.assertEqual(Song.objects.count(), 1)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 3)
        artist = Artist.objects.get(name__iexact='Group')
        self.assertEqual(artist.pk, artist_pk)
        self.assertEqual(artist.name, 'group')

    def test_update_change_conductor_case_single_track(self):
        """
        Test what happens when a track gets updated with the same conductor
        name but with a different case.  Since it's the only track with
        that conductor name, we want the case of the conductor to get updated.
        """
        self.add_mp3(artist='Artist Name', album='Album', conductor='Conductor',
            title='Title 1', filename='song1.mp3')
        self.run_add()

        # Quick verification
        self.assertEqual(Song.objects.count(), 1)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 3)
        artist = Artist.objects.get(name='Conductor')
        artist_pk = artist.pk

        # Update
        self.update_mp3('song1.mp3', conductor='conductor')
        self.run_update()

        # Verification
        self.assertEqual(Song.objects.count(), 1)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 3)
        artist = Artist.objects.get(name__iexact='Conductor')
        self.assertEqual(artist.pk, artist_pk)
        self.assertEqual(artist.name, 'conductor')

    def test_update_change_composer_case_single_track(self):
        """
        Test what happens when a track gets updated with the same composer
        name but with a different case.  Since it's the only track with
        that composer name, we want the case of the composer to get updated.
        """
        self.add_mp3(artist='Artist Name', album='Album', composer='Composer',
            title='Title 1', filename='song1.mp3')
        self.run_add()

        # Quick verification
        self.assertEqual(Song.objects.count(), 1)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 3)
        artist = Artist.objects.get(name='Composer')
        artist_pk = artist.pk

        # Update
        self.update_mp3('song1.mp3', composer='composer')
        self.run_update()

        # Verification
        self.assertEqual(Song.objects.count(), 1)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 3)
        artist = Artist.objects.get(name__iexact='Composer')
        self.assertEqual(artist.pk, artist_pk)
        self.assertEqual(artist.name, 'composer')

    def test_update_change_artist_aesc_single_track(self):
        """
        Test what happens when a track gets updated with the same artist
        name but with a different usage of æ.  Since it's the only track with
        that artist name, we want the artist name to get updated.
        """
        self.add_mp3(artist='Aertist Name', album='Album',
            title='Title 1', filename='song1.mp3')
        self.run_add()

        # Quick verification
        self.assertEqual(Song.objects.count(), 1)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)
        artist = Artist.objects.get(name='Aertist Name')
        artist_pk = artist.pk

        # Update
        self.update_mp3('song1.mp3', artist='Ærtist Name')
        self.run_update()

        # Verification
        self.assertEqual(Song.objects.count(), 1)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)
        artist = Artist.objects.get(name='Ærtist Name')
        self.assertEqual(artist.pk, artist_pk)
        self.assertEqual(artist.name, 'Ærtist Name')

    def test_update_change_group_aesc_single_track(self):
        """
        Test what happens when a track gets updated with the same group
        name but with a different usage of æ.  Since it's the only track with
        that group name, we want the group name to get updated.
        """
        self.add_mp3(artist='Main Artist', album='Album', group='Group AE',
            title='Title 1', filename='song1.mp3')
        self.run_add()

        # Quick verification
        self.assertEqual(Song.objects.count(), 1)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 3)
        artist = Artist.objects.get(name='Group AE')
        artist_pk = artist.pk

        # Update
        self.update_mp3('song1.mp3', group='Group Æ')
        self.run_update()

        # Verification
        self.assertEqual(Song.objects.count(), 1)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 3)
        artist = Artist.objects.get(normname='group ae')
        self.assertEqual(artist.pk, artist_pk)
        self.assertEqual(artist.name, 'Group Æ')

    def test_update_change_conductor_aesc_single_track(self):
        """
        Test what happens when a track gets updated with the same conductor
        name but with a different usage of æ.  Since it's the only track with
        that conductor name, we want the conductor name to get updated.
        """
        self.add_mp3(artist='Main Artist', album='Album', conductor='Conductor AE',
            title='Title 1', filename='song1.mp3')
        self.run_add()

        # Quick verification
        self.assertEqual(Song.objects.count(), 1)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 3)
        artist = Artist.objects.get(name='Conductor AE')
        artist_pk = artist.pk

        # Update
        self.update_mp3('song1.mp3', conductor='Conductor Æ')
        self.run_update()

        # Verification
        self.assertEqual(Song.objects.count(), 1)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 3)
        artist = Artist.objects.get(normname='conductor ae')
        self.assertEqual(artist.pk, artist_pk)
        self.assertEqual(artist.name, 'Conductor Æ')

    def test_update_change_composer_aesc_single_track(self):
        """
        Test what happens when a track gets updated with the same composer
        name but with a different usage of æ.  Since it's the only track with
        that composer name, we want the composer name to get updated.
        """
        self.add_mp3(artist='Main Artist', album='Album', composer='Composer AE',
            title='Title 1', filename='song1.mp3')
        self.run_add()

        # Quick verification
        self.assertEqual(Song.objects.count(), 1)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 3)
        artist = Artist.objects.get(name='Composer AE')
        artist_pk = artist.pk

        # Update
        self.update_mp3('song1.mp3', composer='Composer Æ')
        self.run_update()

        # Verification
        self.assertEqual(Song.objects.count(), 1)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 3)
        artist = Artist.objects.get(normname='composer ae')
        self.assertEqual(artist.pk, artist_pk)
        self.assertEqual(artist.name, 'Composer Æ')

    def test_update_change_artist_case_two_tracks(self):
        """
        Test what happens when a track gets updated with the same artist
        name but with a different case.  Since it's only one out of the
        two tracks track with that artist name, we want the case of the
        artist to remain unchanged
        """
        self.add_mp3(artist='Artist Name', album='Album',
            title='Title 1', filename='song1.mp3')
        self.add_mp3(artist='Artist Name', album='Album',
            title='Title 2', filename='song2.mp3')
        self.run_add()

        # Quick verification
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)
        artist = Artist.objects.get(name='Artist Name')
        artist_pk = artist.pk

        # Update
        self.update_mp3('song2.mp3', artist='artist name')
        self.run_update()

        # Verification
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)
        artist = Artist.objects.get(name='Artist Name')
        self.assertEqual(artist.pk, artist_pk)
        self.assertEqual(artist.name, 'Artist Name')

    def test_update_change_group_case_two_tracks(self):
        """
        Test what happens when a track gets updated with the same group
        name but with a different case.  Since it's only one out of the
        two tracks track with that group name, we want the case of the
        group to remain unchanged
        """
        self.add_mp3(artist='Artist Name', album='Album', group='Group Name',
            title='Title 1', filename='song1.mp3')
        self.add_mp3(artist='Artist Name', album='Album', group='Group Name',
            title='Title 2', filename='song2.mp3')
        self.run_add()

        # Quick verification
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 3)
        artist = Artist.objects.get(name='Group Name')
        artist_pk = artist.pk

        # Update
        self.update_mp3('song2.mp3', group='group name')
        self.run_update()

        # Verification
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 3)
        artist = Artist.objects.get(name='Group Name')
        self.assertEqual(artist.pk, artist_pk)
        self.assertEqual(artist.name, 'Group Name')

    def test_update_change_conductor_case_two_tracks(self):
        """
        Test what happens when a track gets updated with the same conductor
        name but with a different case.  Since it's only one out of the
        two tracks track with that conductor name, we want the case of the
        conductor to remain unchanged
        """
        self.add_mp3(artist='Artist Name', album='Album', conductor='Conductor Name',
            title='Title 1', filename='song1.mp3')
        self.add_mp3(artist='Artist Name', album='Album', conductor='Conductor Name',
            title='Title 2', filename='song2.mp3')
        self.run_add()

        # Quick verification
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 3)
        artist = Artist.objects.get(name='Conductor Name')
        artist_pk = artist.pk

        # Update
        self.update_mp3('song2.mp3', conductor='conductor name')
        self.run_update()

        # Verification
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 3)
        artist = Artist.objects.get(name='Conductor Name')
        self.assertEqual(artist.pk, artist_pk)
        self.assertEqual(artist.name, 'Conductor Name')

    def test_update_change_composer_case_two_tracks(self):
        """
        Test what happens when a track gets updated with the same composer
        name but with a different case.  Since it's only one out of the
        two tracks track with that composer name, we want the case of the
        composer to remain unchanged
        """
        self.add_mp3(artist='Artist Name', album='Album', composer='Composer Name',
            title='Title 1', filename='song1.mp3')
        self.add_mp3(artist='Artist Name', album='Album', composer='Composer Name',
            title='Title 2', filename='song2.mp3')
        self.run_add()

        # Quick verification
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 3)
        artist = Artist.objects.get(name='Composer Name')
        artist_pk = artist.pk

        # Update
        self.update_mp3('song2.mp3', composer='composer name')
        self.run_update()

        # Verification
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 3)
        artist = Artist.objects.get(name='Composer Name')
        self.assertEqual(artist.pk, artist_pk)
        self.assertEqual(artist.name, 'Composer Name')

    def test_update_change_artist_aesc_two_tracks(self):
        """
        Test what happens when a track gets updated with the same artist
        name but with a different Æ.  Since it's only one out of the
        two tracks track with that artist name, we want the original
        artist to remain unchanged
        """
        self.add_mp3(artist='Ærtist Name', album='Album',
            title='Title 1', filename='song1.mp3')
        self.add_mp3(artist='Ærtist Name', album='Album',
            title='Title 2', filename='song2.mp3')
        self.run_add()

        # Quick verification
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)
        artist = Artist.objects.get(name='Ærtist Name')
        artist_pk = artist.pk

        # Update
        self.update_mp3('song2.mp3', artist='Aertist Name')
        self.run_update()

        # Verification
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)
        artist = Artist.objects.get(name='Ærtist Name')
        self.assertEqual(artist.pk, artist_pk)
        self.assertEqual(artist.name, 'Ærtist Name')

    def test_update_change_group_aesc_two_tracks(self):
        """
        Test what happens when a track gets updated with the same group
        name but with a different Æ.  Since it's only one out of the
        two tracks track with that group name, we want the original
        artist to remain unchanged
        """
        self.add_mp3(artist='Artist Name', album='Album', group='Group Æ',
            title='Title 1', filename='song1.mp3')
        self.add_mp3(artist='Artist Name', album='Album', group='Group Æ',
            title='Title 2', filename='song2.mp3')
        self.run_add()

        # Quick verification
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 3)
        artist = Artist.objects.get(name='Group Æ')
        artist_pk = artist.pk

        # Update
        self.update_mp3('song2.mp3', group='Group AE')
        self.run_update()

        # Verification
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 3)
        artist = Artist.objects.get(normname='group ae')
        self.assertEqual(artist.pk, artist_pk)
        self.assertEqual(artist.name, 'Group Æ')

    def test_update_change_conductor_aesc_two_tracks(self):
        """
        Test what happens when a track gets updated with the same conductor
        name but with a different Æ.  Since it's only one out of the
        two tracks track with that conductor name, we want the original
        artist to remain unchanged
        """
        self.add_mp3(artist='Artist Name', album='Album', conductor='Conductor Æ',
            title='Title 1', filename='song1.mp3')
        self.add_mp3(artist='Artist Name', album='Album', conductor='Conductor Æ',
            title='Title 2', filename='song2.mp3')
        self.run_add()

        # Quick verification
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 3)
        artist = Artist.objects.get(name='Conductor Æ')
        artist_pk = artist.pk

        # Update
        self.update_mp3('song2.mp3', conductor='Conductor AE')
        self.run_update()

        # Verification
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 3)
        artist = Artist.objects.get(normname='conductor ae')
        self.assertEqual(artist.pk, artist_pk)
        self.assertEqual(artist.name, 'Conductor Æ')

    def test_update_change_composer_aesc_two_tracks(self):
        """
        Test what happens when a track gets updated with the same composer
        name but with a different Æ.  Since it's only one out of the
        two tracks track with that composer name, we want the original
        artist to remain unchanged
        """
        self.add_mp3(artist='Artist Name', album='Album', composer='Composer Æ',
            title='Title 1', filename='song1.mp3')
        self.add_mp3(artist='Artist Name', album='Album', composer='Composer Æ',
            title='Title 2', filename='song2.mp3')
        self.run_add()

        # Quick verification
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 3)
        artist = Artist.objects.get(name='Composer Æ')
        artist_pk = artist.pk

        # Update
        self.update_mp3('song2.mp3', composer='Composer AE')
        self.run_update()

        # Verification
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 3)
        artist = Artist.objects.get(normname='composer ae')
        self.assertEqual(artist.pk, artist_pk)
        self.assertEqual(artist.name, 'Composer Æ')

    def test_update_change_album_case_single(self):
        """
        Test what happens when a single-track album gets updated with the
        same album name but with a different case.  The album name should
        be updated, since all tracks in the album have been updated.
        """
        self.add_mp3(artist='Artist Name', album='Album Name',
            title='Title 1', filename='song1.mp3')
        self.run_add()

        # Quick verification
        self.assertEqual(Song.objects.count(), 1)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)
        artist = Artist.objects.get(name='Artist Name')
        artist_pk = artist.pk
        album = Album.objects.get(name='Album Name')
        album_pk = album.pk

        # Update
        self.update_mp3('song1.mp3', album='album name')
        self.run_update()

        # Verification
        self.assertEqual(Song.objects.count(), 1)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)
        artist = Artist.objects.get(name__iexact='Artist Name')
        self.assertEqual(artist.pk, artist_pk)
        self.assertEqual(artist.name, 'Artist Name')
        album = Album.objects.get(name__iexact='Album Name')
        self.assertEqual(album.pk, album_pk)
        self.assertEqual(album.name, 'album name')

    def test_update_change_album_aesc_single(self):
        """
        Test what happens when a single-track album gets updated with the
        same album name but with a different Æ.  The album name should
        be updated, since all tracks in the album have been updated.
        """
        self.add_mp3(artist='Artist Name', album='Aelbum Name',
            title='Title 1', filename='song1.mp3')
        self.run_add()

        # Quick verification
        self.assertEqual(Song.objects.count(), 1)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)
        artist = Artist.objects.get(name='Artist Name')
        artist_pk = artist.pk
        album = Album.objects.get(name='Aelbum Name')
        album_pk = album.pk

        # Update
        self.update_mp3('song1.mp3', album='Ælbum Name')
        self.run_update()

        # Verification
        self.assertEqual(Song.objects.count(), 1)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)
        artist = Artist.objects.get(name='Artist Name')
        self.assertEqual(artist.pk, artist_pk)
        self.assertEqual(artist.name, 'Artist Name')
        album = Album.objects.get(name='Ælbum Name')
        self.assertEqual(album.pk, album_pk)
        self.assertEqual(album.name, 'Ælbum Name')

    def test_update_change_album_case_multiple(self):
        """
        Test what happens when one track in a multi-track album gets updated
        with the same album name but with a different case.  The album name
        should remain the same, since not all tracks in the album have been
        updated.
        """
        self.add_mp3(artist='Artist Name', album='Album Name',
            title='Title 1', filename='song1.mp3')
        self.add_mp3(artist='Artist Name', album='Album Name',
            title='Title 2', filename='song2.mp3')
        self.run_add()

        # Quick verification
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)
        artist = Artist.objects.get(name='Artist Name')
        artist_pk = artist.pk
        album = Album.objects.get(name='Album Name')
        album_pk = album.pk

        # Update
        self.update_mp3('song2.mp3', album='album name')
        self.run_update()

        # Verification
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)
        artist = Artist.objects.get(name='Artist Name')
        self.assertEqual(artist.pk, artist_pk)
        self.assertEqual(artist.name, 'Artist Name')
        album = Album.objects.get(name='Album Name')
        self.assertEqual(album.pk, album_pk)
        self.assertEqual(album.name, 'Album Name')

    def test_update_change_album_aesc_multiple(self):
        """
        Test what happens when one track in a multi-track album gets updated
        with the same album name but with a different Æ.  The album name
        should remain the same, since not all tracks in the album have been
        updated.
        """
        self.add_mp3(artist='Artist Name', album='Aelbum Name',
            title='Title 1', filename='song1.mp3')
        self.add_mp3(artist='Artist Name', album='Aelbum Name',
            title='Title 2', filename='song2.mp3')
        self.run_add()

        # Quick verification
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)
        artist = Artist.objects.get(name='Artist Name')
        artist_pk = artist.pk
        album = Album.objects.get(name='Aelbum Name')
        album_pk = album.pk

        # Update
        self.update_mp3('song2.mp3', album='Ælbum Name')
        self.run_update()

        # Verification
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)
        artist = Artist.objects.get(name='Artist Name')
        self.assertEqual(artist.pk, artist_pk)
        self.assertEqual(artist.name, 'Artist Name')
        album = Album.objects.get(name='Aelbum Name')
        self.assertEqual(album.pk, album_pk)
        self.assertEqual(album.name, 'Aelbum Name')

    def test_update_change_artist_case_on_single_album_track(self):
        """
        Test what happens when a single track from an album gets
        updated with the same artist name but with a different case.
        """
        self.add_mp3(artist='Artist Name', album='Album',
            title='Title 1', filename='song1.mp3')
        self.add_mp3(artist='Artist Name', album='Album',
            title='Title 2', filename='song2.mp3')
        self.run_add()

        # Quick verification
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)
        artist = Artist.objects.get(name='Artist Name')
        artist_pk = artist.pk
        album = Album.objects.get()
        self.assertEqual(album.artist.name, 'Artist Name')
        album_pk = album.pk

        # Update
        self.update_mp3('song1.mp3', artist='artist name')
        self.run_update()

        # Verification
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)
        artist = Artist.objects.get(name='Artist Name')
        self.assertEqual(artist.pk, artist_pk)
        self.assertEqual(artist.name, 'Artist Name')
        album = Album.objects.get()
        self.assertEqual(album.pk, album_pk)
        self.assertEqual(album.artist.name, 'Artist Name')

    def test_update_change_artist_to_other_album_with_different_case(self):
        """
        Setup: three tracks divided into two albums.  The album with
        two tracks has one of its tracks update so that it switches
        to the other album, but the case on the updated track is different
        than the album's.
        """
        tracks = [
            ('Album 1', '1.mp3', 'Artist 1', 'First', 1),
            ('Album 1', '2.mp3', 'Artist 1', 'Second', 2),
            ('Album 2', '3.mp3', 'Artist 2', 'Third', 3),
        ]
        for (album, filename, artist, title, tracknum) in tracks:
            self.add_mp3(filename=filename, artist=artist,
                title=title, tracknum=tracknum, album=album)
        self.run_add()

        # Quick verification
        self.assertEqual(Song.objects.count(), 3)
        self.assertEqual(Album.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 3)
        al1 = Album.objects.get(name='Album 1')
        al1_pk = al1.pk
        self.assertEqual(al1.song_set.count(), 2)
        al2 = Album.objects.get(name='Album 2')
        al2_pk = al2.pk
        self.assertEqual(al2.song_set.count(), 1)
        ar1 = Artist.objects.get(name='Artist 1')
        ar1_pk = ar1.pk
        ar2 = Artist.objects.get(name='Artist 2')
        ar2_pk = ar2.pk

        # Update
        self.update_mp3('2.mp3', artist='artist 2', album='album 2')
        self.run_update()

        # Verification
        self.assertEqual(Song.objects.count(), 3)
        self.assertEqual(Album.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 3)
        al1 = Album.objects.get(name='Album 1')
        self.assertEqual(al1_pk, al1.pk)
        self.assertEqual(al1.song_set.count(), 1)
        self.assertEqual(al1.name, 'Album 1')
        al2 = Album.objects.get(name='Album 2')
        self.assertEqual(al2_pk, al2.pk)
        self.assertEqual(al2.song_set.count(), 2)
        self.assertEqual(al2.name, 'Album 2')
        ar1 = Artist.objects.get(name='Artist 1')
        self.assertEqual(ar1_pk, ar1.pk)
        self.assertEqual(ar1.name, 'Artist 1')
        ar2 = Artist.objects.get(name='Artist 2')
        self.assertEqual(ar2_pk, ar2.pk)
        self.assertEqual(ar2.name, 'Artist 2')

    def test_update_change_various_album_to_single_with_incorrect_case(self):
        """
        Test what happens when a V/A album becomes a single-artist album
        by updating a single track, but when the single track uses a different
        case than the rest.
        """
        self.add_mp3(artist='Artist 1', album='Album',
            title='Title 1', filename='song1.mp3')
        self.add_mp3(artist='Artist 1', album='Album',
            title='Title 2', filename='song2.mp3')
        self.add_mp3(artist='Artist 2', album='Album',
            title='Title 3', filename='song3.mp3')
        self.run_add()

        # Quick verification
        self.assertEqual(Song.objects.count(), 3)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 3)
        artist = Artist.objects.get(name='Artist 1')
        artist_pk = artist.pk
        album = Album.objects.get()
        self.assertEqual(album.artist.name, 'Various')
        album_pk = album.pk

        # Update
        self.update_mp3('song3.mp3', artist='artist 1')
        self.run_update()

        # Verification
        self.assertEqual(Song.objects.count(), 3)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)
        artist = Artist.objects.get(name='Artist 1')
        self.assertEqual(artist.pk, artist_pk)
        self.assertEqual(artist.name, 'Artist 1')
        album = Album.objects.get()
        self.assertEqual(album.artist.name, 'Artist 1')
        # Eh, let's not care about PK conservation here, this
        # is a ridiculous corner case.
        #self.assertEqual(album.pk, album_pk)

    def test_update_differing_umlaut_artist(self):
        """
        Update one of two files to get rid of an umlaut in the artist name,
        where there used to be one previously.
        """
        self.add_mp3(artist='Umläut', album='Album',
            title='Title 1', filename='song1.mp3')
        self.add_mp3(artist='Umläut', album='Album',
            title='Title 2', filename='song2.mp3')
        self.run_add()

        # Quick checks
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        artist = Artist.objects.get(normname__iexact='umlaut')
        artist_pk = artist.pk
        self.assertEqual(artist.name, 'Umläut')
        
        # Update
        self.update_mp3('song2.mp3', artist='Umlaut')
        self.run_update()

        # Actual checks
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        artist = Artist.objects.get(normname__iexact='umlaut')
        self.assertEqual(artist_pk, artist.pk)
        self.assertEqual(artist.name, 'Umläut')

    def test_update_differing_umlaut_group(self):
        """
        Update one of two files to get rid of an umlaut in the group name,
        where there used to be one previously.
        """
        self.add_mp3(artist='Artist', album='Album', group='Group Ä',
            title='Title 1', filename='song1.mp3')
        self.add_mp3(artist='Artist', album='Album', group='Group Ä',
            title='Title 2', filename='song2.mp3')
        self.run_add()

        # Quick checks
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 3)
        self.assertEqual(Album.objects.count(), 1)
        artist = Artist.objects.get(normname='group a')
        artist_pk = artist.pk
        self.assertEqual(artist.name, 'Group Ä')
        
        # Update
        self.update_mp3('song2.mp3', group='Group A')
        self.run_update()

        # Actual checks
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 3)
        self.assertEqual(Album.objects.count(), 1)
        artist = Artist.objects.get(normname='group a')
        self.assertEqual(artist_pk, artist.pk)
        self.assertEqual(artist.name, 'Group Ä')

    def test_update_differing_umlaut_conductor(self):
        """
        Update one of two files to get rid of an umlaut in the conductor name,
        where there used to be one previously.
        """
        self.add_mp3(artist='Artist', album='Album', conductor='Conductor Ä',
            title='Title 1', filename='song1.mp3')
        self.add_mp3(artist='Artist', album='Album', conductor='Conductor Ä',
            title='Title 2', filename='song2.mp3')
        self.run_add()

        # Quick checks
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 3)
        self.assertEqual(Album.objects.count(), 1)
        artist = Artist.objects.get(normname='conductor a')
        artist_pk = artist.pk
        self.assertEqual(artist.name, 'Conductor Ä')
        
        # Update
        self.update_mp3('song2.mp3', conductor='Conductor A')
        self.run_update()

        # Actual checks
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 3)
        self.assertEqual(Album.objects.count(), 1)
        artist = Artist.objects.get(normname='conductor a')
        self.assertEqual(artist_pk, artist.pk)
        self.assertEqual(artist.name, 'Conductor Ä')

    def test_update_differing_umlaut_composer(self):
        """
        Update one of two files to get rid of an umlaut in the composer name,
        where there used to be one previously.
        """
        self.add_mp3(artist='Artist', album='Album', composer='Composer Ä',
            title='Title 1', filename='song1.mp3')
        self.add_mp3(artist='Artist', album='Album', composer='Composer Ä',
            title='Title 2', filename='song2.mp3')
        self.run_add()

        # Quick checks
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 3)
        self.assertEqual(Album.objects.count(), 1)
        artist = Artist.objects.get(normname='composer a')
        artist_pk = artist.pk
        self.assertEqual(artist.name, 'Composer Ä')
        
        # Update
        self.update_mp3('song2.mp3', composer='Composer A')
        self.run_update()

        # Actual checks
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 3)
        self.assertEqual(Album.objects.count(), 1)
        artist = Artist.objects.get(normname='composer a')
        self.assertEqual(artist_pk, artist.pk)
        self.assertEqual(artist.name, 'Composer Ä')

    def test_update_differing_aesc_artist(self):
        """
        Update one of two files to get rid of an Æ in the artist name,
        where there used to be one previously.
        """
        self.add_mp3(artist='Ærtist', album='Album',
            title='Title 1', filename='song1.mp3')
        self.add_mp3(artist='Ærtist', album='Album',
            title='Title 2', filename='song2.mp3')
        self.run_add()

        # Quick checks
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        artist = Artist.objects.get(name='Ærtist')
        artist_pk = artist.pk
        
        # Update
        self.update_mp3('song2.mp3', artist='Aertist')
        self.run_update()

        # Actual checks
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        artist = Artist.objects.get(name='Ærtist')
        self.assertEqual(artist_pk, artist.pk)
        self.assertEqual(artist.name, 'Ærtist')

    def test_update_differing_aesc_group(self):
        """
        Update one of two files to get rid of an Æ in the group name,
        where there used to be one previously.
        """
        self.add_mp3(artist='Artist', album='Album', group='Group Æ',
            title='Title 1', filename='song1.mp3')
        self.add_mp3(artist='Artist', album='Album', group='Group Æ',
            title='Title 2', filename='song2.mp3')
        self.run_add()

        # Quick checks
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 3)
        self.assertEqual(Album.objects.count(), 1)
        artist = Artist.objects.get(name='Group Æ')
        artist_pk = artist.pk
        
        # Update
        self.update_mp3('song2.mp3', group='Group AE')
        self.run_update()

        # Actual checks
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 3)
        self.assertEqual(Album.objects.count(), 1)
        artist = Artist.objects.get(normname='group ae')
        self.assertEqual(artist_pk, artist.pk)
        self.assertEqual(artist.name, 'Group Æ')

    def test_update_differing_aesc_conductor(self):
        """
        Update one of two files to get rid of an Æ in the conductor name,
        where there used to be one previously.
        """
        self.add_mp3(artist='Artist', album='Album', conductor='Conductor Æ',
            title='Title 1', filename='song1.mp3')
        self.add_mp3(artist='Artist', album='Album', conductor='Conductor Æ',
            title='Title 2', filename='song2.mp3')
        self.run_add()

        # Quick checks
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 3)
        self.assertEqual(Album.objects.count(), 1)
        artist = Artist.objects.get(name='Conductor Æ')
        artist_pk = artist.pk
        
        # Update
        self.update_mp3('song2.mp3', conductor='Conductor AE')
        self.run_update()

        # Actual checks
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 3)
        self.assertEqual(Album.objects.count(), 1)
        artist = Artist.objects.get(normname='conductor ae')
        self.assertEqual(artist_pk, artist.pk)
        self.assertEqual(artist.name, 'Conductor Æ')

    def test_update_differing_aesc_composer(self):
        """
        Update one of two files to get rid of an Æ in the composer name,
        where there used to be one previously.
        """
        self.add_mp3(artist='Artist', album='Album', composer='Composer Æ',
            title='Title 1', filename='song1.mp3')
        self.add_mp3(artist='Artist', album='Album', composer='Composer Æ',
            title='Title 2', filename='song2.mp3')
        self.run_add()

        # Quick checks
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 3)
        self.assertEqual(Album.objects.count(), 1)
        artist = Artist.objects.get(name='Composer Æ')
        artist_pk = artist.pk
        
        # Update
        self.update_mp3('song2.mp3', composer='Composer AE')
        self.run_update()

        # Actual checks
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 3)
        self.assertEqual(Album.objects.count(), 1)
        artist = Artist.objects.get(normname='composer ae')
        self.assertEqual(artist_pk, artist.pk)
        self.assertEqual(artist.name, 'Composer Æ')

    def test_update_differing_umlaut_album(self):
        """
        Update one of two files to get rid of an umlaut in the album name,
        where there used to be one previously.
        """
        self.add_mp3(artist='Umlaut', album='Albüm',
            title='Title 1', filename='song1.mp3')
        self.add_mp3(artist='Umlaut', album='Albüm',
            title='Title 2', filename='song2.mp3')
        self.run_add()

        # Quick checks
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        album = Album.objects.get(normname='album')
        album_pk = album.pk
        self.assertEqual(album.name, 'Albüm')
        
        # Update
        self.update_mp3('song2.mp3', album='Album')
        self.run_update()

        # Actual checks
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        album = Album.objects.get(normname='album')
        self.assertEqual(album_pk, album.pk)
        self.assertEqual(album.song_set.count(), 2)
        self.assertEqual(album.name, 'Albüm')

    def test_update_differing_aesc_album(self):
        """
        Update one of two files to get rid of an Æ in the album name,
        where there used to be one previously.
        """
        self.add_mp3(artist='Artist', album='Ælbum',
            title='Title 1', filename='song1.mp3')
        self.add_mp3(artist='Artist', album='Ælbum',
            title='Title 2', filename='song2.mp3')
        self.run_add()

        # Quick checks
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        album = Album.objects.get(name='Ælbum')
        album_pk = album.pk
        self.assertEqual(album.name, 'Ælbum')
        
        # Update
        self.update_mp3('song2.mp3', album='Aelbum')
        self.run_update()

        # Actual checks
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        album = Album.objects.get(name='Ælbum')
        self.assertEqual(album_pk, album.pk)
        self.assertEqual(album.song_set.count(), 2)
        self.assertEqual(album.name, 'Ælbum')

    def test_update_mismatched_japanese_artists(self):
        """
        Tests an update where two previously distinct Japanese-named artists
        should update to become one artist.
        """
        self.add_mp3(artist='\u81EA\u52D5\u8ABF', album='Album 1',
            title='Title 1', filename='song1.mp3')
        self.add_mp3(artist='\u30AB\u30CA\u30C0', album='Album 2',
            title='Title 2', filename='song2.mp3')
        self.run_add()

        # Quick checks
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 3)
        self.assertEqual(Album.objects.count(), 2)

        # Now update
        self.update_mp3('song2.mp3', artist='\u81EA\u52D5\u8ABF')
        self.run_update()

        # Real checks
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 2)
        artist = Artist.objects.get(name='\u81EA\u52D5\u8ABF')
        self.assertEqual(artist.name, '\u81EA\u52D5\u8ABF')

    def test_update_mismatched_japanese_group(self):
        """
        Tests an update where two previously distinct Japanese-named artists
        should update to become one artist, keyed off of the group field
        """
        self.add_mp3(artist='Artist', group='\u81EA\u52D5\u8ABF', album='Album 1',
            title='Title 1', filename='song1.mp3')
        self.add_mp3(artist='Artist', group='\u30AB\u30CA\u30C0', album='Album 2',
            title='Title 2', filename='song2.mp3')
        self.run_add()

        # Quick checks
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 4)
        self.assertEqual(Album.objects.count(), 2)

        # Now update
        self.update_mp3('song2.mp3', group='\u81EA\u52D5\u8ABF')
        self.run_update()

        # Real checks
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 3)
        self.assertEqual(Album.objects.count(), 2)
        artist = Artist.objects.get(name='\u81EA\u52D5\u8ABF')
        self.assertEqual(artist.name, '\u81EA\u52D5\u8ABF')

    def test_update_mismatched_japanese_conductor(self):
        """
        Tests an update where two previously distinct Japanese-named artists
        should update to become one artist, keyed off of the conductor field
        """
        self.add_mp3(artist='Artist', conductor='\u81EA\u52D5\u8ABF', album='Album 1',
            title='Title 1', filename='song1.mp3')
        self.add_mp3(artist='Artist', conductor='\u30AB\u30CA\u30C0', album='Album 2',
            title='Title 2', filename='song2.mp3')
        self.run_add()

        # Quick checks
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 4)
        self.assertEqual(Album.objects.count(), 2)

        # Now update
        self.update_mp3('song2.mp3', conductor='\u81EA\u52D5\u8ABF')
        self.run_update()

        # Real checks
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 3)
        self.assertEqual(Album.objects.count(), 2)
        artist = Artist.objects.get(name='\u81EA\u52D5\u8ABF')
        self.assertEqual(artist.name, '\u81EA\u52D5\u8ABF')

    def test_update_mismatched_japanese_composer(self):
        """
        Tests an update where two previously distinct Japanese-named artists
        should update to become one artist, keyed off of the composer field
        """
        self.add_mp3(artist='Artist', composer='\u81EA\u52D5\u8ABF', album='Album 1',
            title='Title 1', filename='song1.mp3')
        self.add_mp3(artist='Artist', composer='\u30AB\u30CA\u30C0', album='Album 2',
            title='Title 2', filename='song2.mp3')
        self.run_add()

        # Quick checks
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 4)
        self.assertEqual(Album.objects.count(), 2)

        # Now update
        self.update_mp3('song2.mp3', composer='\u81EA\u52D5\u8ABF')
        self.run_update()

        # Real checks
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 3)
        self.assertEqual(Album.objects.count(), 2)
        artist = Artist.objects.get(name='\u81EA\u52D5\u8ABF')
        self.assertEqual(artist.name, '\u81EA\u52D5\u8ABF')

    def test_update_mismatched_japanese_artists_backwards(self):
        """
        Tests an update where two previously joined Japanese-named artist
        tracks should update to become two artists.
        """
        self.add_mp3(artist='\u81EA\u52D5\u8ABF', album='Album',
            title='Title 1', filename='song1.mp3')
        self.add_mp3(artist='\u81EA\u52D5\u8ABF', album='Album',
            title='Title 2', filename='song2.mp3')
        self.run_add()

        # Quick checks
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)

        # Now update
        self.update_mp3('song2.mp3', artist='\u30AB\u30CA\u30C0')
        self.run_update()

        # Real checks
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 3)
        self.assertEqual(Album.objects.count(), 1)
        al1 = Album.objects.get()
        self.assertEqual(al1.artist.name, 'Various')
        self.assertEqual(al1.song_set.count(), 2)

    def test_update_mismatched_japanese_group_backwards(self):
        """
        Tests an update where two previously joined Japanese-named group
        tracks should update to become two artists.  Keyed off of group.
        """
        self.add_mp3(artist='Artist', group='\u81EA\u52D5\u8ABF', album='Album',
            title='Title 1', filename='song1.mp3')
        self.add_mp3(artist='Artist', group='\u81EA\u52D5\u8ABF', album='Album',
            title='Title 2', filename='song2.mp3')
        self.run_add()

        # Quick checks
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 3)
        self.assertEqual(Album.objects.count(), 1)

        # Now update
        self.update_mp3('song2.mp3', group='\u30AB\u30CA\u30C0')
        self.run_update()

        # Real checks
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 4)
        self.assertEqual(Album.objects.count(), 1)

    def test_update_mismatched_japanese_conductor_backwards(self):
        """
        Tests an update where two previously joined Japanese-named conductor
        tracks should update to become two artists.  Keyed off of conductor.
        """
        self.add_mp3(artist='Artist', conductor='\u81EA\u52D5\u8ABF', album='Album',
            title='Title 1', filename='song1.mp3')
        self.add_mp3(artist='Artist', conductor='\u81EA\u52D5\u8ABF', album='Album',
            title='Title 2', filename='song2.mp3')
        self.run_add()

        # Quick checks
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 3)
        self.assertEqual(Album.objects.count(), 1)

        # Now update
        self.update_mp3('song2.mp3', conductor='\u30AB\u30CA\u30C0')
        self.run_update()

        # Real checks
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 4)
        self.assertEqual(Album.objects.count(), 1)

    def test_update_mismatched_japanese_composer_backwards(self):
        """
        Tests an update where two previously joined Japanese-named composer
        tracks should update to become two artists.  Keyed off of composer.
        """
        self.add_mp3(artist='Artist', composer='\u81EA\u52D5\u8ABF', album='Album',
            title='Title 1', filename='song1.mp3')
        self.add_mp3(artist='Artist', composer='\u81EA\u52D5\u8ABF', album='Album',
            title='Title 2', filename='song2.mp3')
        self.run_add()

        # Quick checks
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 3)
        self.assertEqual(Album.objects.count(), 1)

        # Now update
        self.update_mp3('song2.mp3', composer='\u30AB\u30CA\u30C0')
        self.run_update()

        # Real checks
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 4)
        self.assertEqual(Album.objects.count(), 1)

    def test_update_miscellaneous_tracks_to_different_artist_name(self):
        """
        Add two albumless tracks and then update the artist name.  The
        reported non-album-track album should reflect the new name.
        """
        self.add_mp3(artist='Artist', title='Title 1', filename='song1.mp3')
        self.add_mp3(artist='Artist', title='Title 2', filename='song2.mp3')
        self.run_add()

        # Preliminary checks
        album_title = Album.miscellaneous_format_str % ('Artist')
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)
        album = Album.objects.get()
        self.assertEqual(album.miscellaneous, True)
        self.assertEqual(str(album), album_title)
        album_pk = album.pk

        # Updates
        self.update_mp3('song1.mp3', artist='New Artist')
        self.update_mp3('song2.mp3', artist='New Artist')
        self.run_update()

        # Now the real checks
        new_album_title = Album.miscellaneous_format_str % ('New Artist')
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)
        album = Album.objects.get()
        self.assertEqual(album.pk, album_pk)
        self.assertEqual(album.miscellaneous, True)
        self.assertEqual(str(album), new_album_title)
        self.assertEqual(album.song_set.count(), 2)
        self.assertEqual(album.name, new_album_title)

    def test_update_one_miscellaneous_track_to_different_artist_name(self):
        """
        Add two albumless tracks and then update the artist name on one of
        them.  We should end up with two non-album-track albums, one for each
        artist.
        """
        self.add_mp3(artist='Artist', title='Title 1', filename='song1.mp3')
        self.add_mp3(artist='Artist', title='Title 2', filename='song2.mp3')
        self.run_add()

        # Preliminary checks
        album_title = Album.miscellaneous_format_str % ('Artist')
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)
        album = Album.objects.get()
        self.assertEqual(album.miscellaneous, True)
        self.assertEqual(str(album), album_title)
        album_pk = album.pk

        # Updates
        self.update_mp3('song2.mp3', artist='New Artist')
        self.run_update()

        # Now the real checks
        new_album_title = Album.miscellaneous_format_str % ('New Artist')
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 3)
        album = Album.objects.get(artist__name='Artist', miscellaneous=True)
        self.assertEqual(album.miscellaneous, True)
        self.assertEqual(str(album), album_title)
        self.assertEqual(album.song_set.count(), 1)
        self.assertEqual(album.pk, album_pk)
        self.assertEqual(album.song_set.get().filename, 'song1.mp3')
        album = Album.objects.get(artist__name='New Artist', miscellaneous=True)
        self.assertEqual(album.miscellaneous, True)
        self.assertEqual(str(album), new_album_title)
        self.assertEqual(album.song_set.count(), 1)
        self.assertEqual(album.song_set.get().filename, 'song2.mp3')

    def test_update_album_track_to_non_album_track(self):
        """
        An album track is updated to become a non-album track by clearing
        out the Album tag.
        """
        self.add_mp3(artist='Artist', album='Album',
            title='Title 1', filename='song1.mp3')
        self.run_add()

        # Preliminary checks
        self.assertEqual(Song.objects.count(), 1)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)
        album = Album.objects.get()
        self.assertEqual(album.miscellaneous, False)
        self.assertEqual(str(album), 'Album')
        album_pk = album.pk

        # Updates
        self.update_mp3('song1.mp3', album='')
        self.run_update()

        # Now the real checks
        new_album_title = Album.miscellaneous_format_str % ('Artist')
        self.assertEqual(Song.objects.count(), 1)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)
        album = Album.objects.get()
        self.assertEqual(album.miscellaneous, True)
        self.assertEqual(str(album), new_album_title)
        self.assertEqual(album.song_set.count(), 1)

    def test_update_album_track_to_non_album_track_with_multitrack_album(self):
        """
        An album track is updated to become a non-album track by clearing
        out the Album tag.  The original album should still exist, though,
        since only one track was changed
        """
        self.add_mp3(artist='Artist', album='Album',
            title='Title 1', filename='song1.mp3')
        self.add_mp3(artist='Artist', album='Album',
            title='Title 2', filename='song2.mp3')
        self.run_add()

        # Preliminary checks
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)
        album = Album.objects.get()
        self.assertEqual(album.miscellaneous, False)
        self.assertEqual(str(album), 'Album')
        album_pk = album.pk

        # Updates
        self.update_mp3('song1.mp3', album='')
        self.run_update()

        # Now the real checks
        new_album_title = Album.miscellaneous_format_str % ('Artist')
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 2)
        album = Album.objects.get(artist__name='Artist', miscellaneous=True)
        self.assertEqual(album.miscellaneous, True)
        self.assertEqual(str(album), new_album_title)
        self.assertEqual(album.song_set.count(), 1)
        self.assertEqual(album.song_set.get().filename, 'song1.mp3')
        album = Album.objects.get(name='Album')
        self.assertEqual(album.miscellaneous, False)
        self.assertEqual(str(album), 'Album')
        self.assertEqual(album.song_set.count(), 1)
        self.assertEqual(album.song_set.get().filename, 'song2.mp3')

    def test_update_non_album_track_to_album_track(self):
        """
        A non-album track is updated to become an album track by adding
        an Album tag.
        """
        self.add_mp3(artist='Artist', title='Title 1', filename='song1.mp3')
        self.run_add()

        # Preliminary checks
        album_title = Album.miscellaneous_format_str % ('Artist')
        self.assertEqual(Song.objects.count(), 1)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)
        album = Album.objects.get()
        self.assertEqual(album.miscellaneous, True)
        self.assertEqual(str(album), album_title)

        # Updates
        self.update_mp3('song1.mp3', album='Album')
        self.run_update()

        # Now the real checks
        self.assertEqual(Song.objects.count(), 1)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)
        album = Album.objects.get()
        self.assertEqual(album.miscellaneous, False)
        self.assertEqual(str(album), 'Album')
        self.assertEqual(album.song_set.count(), 1)

    def test_update_non_album_track_to_album_track_with_multitrack_album(self):
        """
        A non-album track is updated to become an album track by adding
        an Album tag.  The original album should be used.
        """
        self.add_mp3(artist='Artist', album='Album',
            title='Title 1', filename='song1.mp3')
        self.add_mp3(artist='Artist', album='',
            title='Title 2', filename='song2.mp3')
        self.run_add()

        # Preliminary checks
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 2)
        album = Album.objects.get(name='Album')
        self.assertEqual(album.miscellaneous, False)
        self.assertEqual(str(album), 'Album')
        self.assertEqual(album.song_set.count(), 1)
        album_pk = album.pk
        album_title = Album.miscellaneous_format_str % ('Artist')
        album = Album.objects.get(artist__name='Artist', miscellaneous=True)
        self.assertEqual(album.miscellaneous, True)
        self.assertEqual(str(album), album_title)
        self.assertEqual(album.song_set.count(), 1)

        # Updates
        self.update_mp3('song2.mp3', album='Album')
        self.run_update()

        # Now the real checks
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)
        album = Album.objects.get()
        self.assertEqual(album.miscellaneous, False)
        self.assertEqual(str(album), 'Album')
        self.assertEqual(album.song_set.count(), 2)
        self.assertEqual(album.pk, album_pk)

    def test_update_song_delete(self):
        """
        Test a track deletion (also ensures that album+artist records get cleared out)
        """
        self.add_mp3(filename='song.mp3', artist='Artist', title='Title',
            group='Group', conductor='Conductor', composer='Composer',
            album = 'Album')
        self.run_add()

        # Quick verification
        self.assertEqual(Song.objects.count(), 1)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 5)

        # Do the delete
        self.delete_file('song.mp3')
        self.run_update()

        # Now the real checks
        self.assertEqual(Song.objects.count(), 0)
        self.assertEqual(Album.objects.count(), 0)
        self.assertEqual(Artist.objects.count(), 1)

    def test_update_song_delete_keep_album(self):
        """
        Test a track deletion with an album which stays in place
        """
        self.add_mp3(filename='song.mp3', artist='Artist', title='Title',
            group='Group', conductor='Conductor', composer='Composer',
            album = 'Album')
        self.add_mp3(filename='song2.mp3', artist='Artist', title='Title 2',
            group='Group', conductor='Conductor', composer='Composer',
            album = 'Album')
        self.run_add()

        # Quick verification
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 5)

        # Do the delete
        self.delete_file('song2.mp3')
        self.run_update()

        # Now the real checks
        self.assertEqual(Song.objects.count(), 1)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 5)
        album = Album.objects.get()
        self.assertEqual(album.song_set.count(), 1)
        song = album.song_set.get()
        self.assertEqual(song.title, 'Title')

    def test_update_song_move(self):
        """
        Test a move of a file from one location to another other.
        """
        self.add_mp3(path='starting', filename='song.mp3',
            artist='Artist', title='Title', album = 'Album',
            group='Group', conductor='Conductor', composer='Composer',
            )
        self.run_add()

        # Quick verification
        self.assertEqual(Song.objects.count(), 1)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 5)

        artist = Artist.objects.get(name='Artist')
        artist_pk = artist.pk
        artist_name = artist.name

        album = Album.objects.get()
        album_pk = album.pk
        album_name = album.name

        song = Song.objects.get()
        song_pk = song.pk
        song_album = song.album.name
        song_artist = song.artist.name
        song_group = song.group.name
        song_conductor = song.conductor.name
        song_composer = song.composer.name
        song_title = song.title
        song_year = song.year
        song_tracknum = song.tracknum
        song_filetype = song.filetype
        song_bitrate = song.bitrate
        song_mode = song.mode
        song_size = song.size
        song_length = song.length
        song_time_added = song.time_added
        song_time_updated = song.time_updated
        song_sha256sum = song.sha256sum

        # Move the file
        self.move_file(song.filename, 'ending')
        self.run_update()

        # Check the data
        self.assertEqual(Song.objects.count(), 1)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 5)

        artist = Artist.objects.get(name='Artist')
        self.assertEqual(artist_pk, artist.pk)
        self.assertEqual(artist_name, artist.name)

        album = Album.objects.get()
        self.assertEqual(album_pk, album.pk)
        self.assertEqual(album_name, album.name)

        song = Song.objects.get()
        self.assertEqual('ending/song.mp3', song.filename)
        self.assertEqual(song_pk, song.pk)
        self.assertEqual(song_album, song.album.name)
        self.assertEqual(song_artist, song.artist.name)
        self.assertEqual(song_group, song.group.name)
        self.assertEqual(song_conductor, song.conductor.name)
        self.assertEqual(song_composer, song.composer.name)
        self.assertEqual(song_title, song.title)
        self.assertEqual(song_year, song.year)
        self.assertEqual(song_tracknum, song.tracknum)
        self.assertEqual(song_filetype, song.filetype)
        self.assertEqual(song_bitrate, song.bitrate)
        self.assertEqual(song_mode, song.mode)
        self.assertEqual(song_size, song.size)
        self.assertEqual(song_length, song.length)
        self.assertEqual(song_time_added, song.time_added)
        self.assertEqual(song_time_updated, song.time_updated)
        self.assertEqual(song_sha256sum, song.sha256sum)

    def test_update_change_prefix(self):
        """
        Test an update of a file which adds a previously-unknown
        prefix to an artist.
        """
        self.add_mp3(filename='1-first.mp3',
            artist='Artist', title='Title 1', album = 'Album')
        self.add_mp3(filename='2-second.mp3',
            artist='Artist', title='Title 1', album = 'Album')
        self.run_add()

        # Quick verification
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)
        artist = Artist.objects.get(name='Artist')
        self.assertEqual(artist.name, 'Artist')
        self.assertEqual(artist.prefix, '')

        # Do the update
        self.update_mp3('2-second.mp3', artist='The Artist')
        self.run_update()

        # Check
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)
        artist = Artist.objects.get(name='Artist')
        self.assertEqual(artist.name, 'Artist')
        self.assertEqual(artist.prefix, 'The')

    def test_update_change_prefix_different_artist(self):
        """
        Test an update to a file which changes to a different artist
        and also adds a prefix to that second artist.
        """
        self.add_mp3(filename='1-first.mp3',
            artist='Artist', title='Title 1', album = 'Album')
        self.add_mp3(filename='2-second.mp3',
            artist='Artist', title='Title 2', album = 'Album')
        self.add_mp3(filename='3-third.mp3',
            artist='Other', title='Title 3', album = 'Other')
        self.run_add()

        # Quick verification
        self.assertEqual(Song.objects.count(), 3)
        self.assertEqual(Album.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 3)
        artist = Artist.objects.get(name='Other')
        artist_pk = artist.pk
        self.assertEqual(artist.name, 'Other')
        self.assertEqual(artist.prefix, '')

        # Do the update
        self.update_mp3('2-second.mp3', artist='The Other')
        self.run_update()

        # Check
        self.assertEqual(Song.objects.count(), 3)
        self.assertEqual(Album.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 3)
        artist = Artist.objects.get(name='Other')
        self.assertEqual(artist.name, 'Other')
        self.assertEqual(artist.prefix, 'The')

    def test_update_change_prefix_group(self):
        """
        Test an update of a file which adds a previously-unknown
        prefix to an artist, on the group record
        """
        self.add_mp3(filename='1-first.mp3',
            artist='Artist', title='Title 1', album = 'Album', group='Artist')
        self.add_mp3(filename='2-second.mp3',
            artist='Artist', title='Title 1', album = 'Album', group='Artist')
        self.run_add()

        # Quick verification
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)
        artist = Artist.objects.get(name='Artist')
        self.assertEqual(artist.name, 'Artist')
        self.assertEqual(artist.prefix, '')

        # Do the update
        self.update_mp3('2-second.mp3', group='The Artist')
        self.run_update()

        # Check
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)
        artist = Artist.objects.get(name='Artist')
        self.assertEqual(artist.name, 'Artist')
        self.assertEqual(artist.prefix, 'The')

    def test_update_change_prefix_conductor(self):
        """
        Test an update of a file which adds a previously-unknown
        prefix to an artist, on the conductor record
        """
        self.add_mp3(filename='1-first.mp3',
            artist='Artist', title='Title 1', album = 'Album', conductor='Artist')
        self.add_mp3(filename='2-second.mp3',
            artist='Artist', title='Title 1', album = 'Album', conductor='Artist')
        self.run_add()

        # Quick verification
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)
        artist = Artist.objects.get(name='Artist')
        self.assertEqual(artist.name, 'Artist')
        self.assertEqual(artist.prefix, '')

        # Do the update
        self.update_mp3('2-second.mp3', conductor='The Artist')
        self.run_update()

        # Check
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)
        artist = Artist.objects.get(name='Artist')
        self.assertEqual(artist.name, 'Artist')
        self.assertEqual(artist.prefix, 'The')

    def test_update_change_prefix_composer(self):
        """
        Test an update of a file which adds a previously-unknown
        prefix to an artist, on the composer record
        """
        self.add_mp3(filename='1-first.mp3',
            artist='Artist', title='Title 1', album = 'Album', composer='Artist')
        self.add_mp3(filename='2-second.mp3',
            artist='Artist', title='Title 1', album = 'Album', composer='Artist')
        self.run_add()

        # Quick verification
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)
        artist = Artist.objects.get(name='Artist')
        self.assertEqual(artist.name, 'Artist')
        self.assertEqual(artist.prefix, '')

        # Do the update
        self.update_mp3('2-second.mp3', composer='The Artist')
        self.run_update()

        # Check
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)
        artist = Artist.objects.get(name='Artist')
        self.assertEqual(artist.name, 'Artist')
        self.assertEqual(artist.prefix, 'The')

    def test_update_no_change_prefix(self):
        """
        Test an update of a file which removes the artist prefix on the
        tags - initial prefix on artist should remain in place.
        """
        self.add_mp3(filename='1-first.mp3',
            artist='The Artist', title='Title 1', album = 'Album')
        self.add_mp3(filename='2-second.mp3',
            artist='The Artist', title='Title 1', album = 'Album')
        self.run_add()

        # Quick verification
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)
        artist = Artist.objects.get(name='Artist')
        self.assertEqual(artist.name, 'Artist')
        self.assertEqual(artist.prefix, 'The')

        # Do the update
        self.update_mp3('2-second.mp3', artist='Artist')
        self.run_update()

        # Check
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)
        artist = Artist.objects.get(name='Artist')
        self.assertEqual(artist.name, 'Artist')
        self.assertEqual(artist.prefix, 'The')
        song = Song.objects.get(filename='2-second.mp3')
        self.assertEqual(song.artist.name, 'Artist')
        self.assertEqual(song.artist.prefix, 'The')

    def test_update_no_change_prefix_group(self):
        """
        Test an update of a file which removes the group prefix on the
        tags - initial prefix on group should remain in place.
        """
        self.add_mp3(filename='1-first.mp3',
            artist='The Artist', title='Title 1', album = 'Album', group='The Artist')
        self.add_mp3(filename='2-second.mp3',
            artist='The Artist', title='Title 1', album = 'Album', group='The Artist')
        self.run_add()

        # Quick verification
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)
        artist = Artist.objects.get(name='Artist')
        self.assertEqual(artist.name, 'Artist')
        self.assertEqual(artist.prefix, 'The')

        # Do the update
        self.update_mp3('2-second.mp3', group='Artist')
        self.run_update()

        # Check
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)
        artist = Artist.objects.get(name='Artist')
        self.assertEqual(artist.name, 'Artist')
        self.assertEqual(artist.prefix, 'The')
        song = Song.objects.get(filename='2-second.mp3')
        self.assertEqual(song.group.name, 'Artist')
        self.assertEqual(song.group.prefix, 'The')

    def test_update_no_change_prefix_conductor(self):
        """
        Test an update of a file which removes the conductor prefix on the
        tags - initial prefix on conductor should remain in place.
        """
        self.add_mp3(filename='1-first.mp3',
            artist='The Artist', title='Title 1', album = 'Album', conductor='The Artist')
        self.add_mp3(filename='2-second.mp3',
            artist='The Artist', title='Title 1', album = 'Album', conductor='The Artist')
        self.run_add()

        # Quick verification
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)
        artist = Artist.objects.get(name='Artist')
        self.assertEqual(artist.name, 'Artist')
        self.assertEqual(artist.prefix, 'The')

        # Do the update
        self.update_mp3('2-second.mp3', conductor='Artist')
        self.run_update()

        # Check
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)
        artist = Artist.objects.get(name='Artist')
        self.assertEqual(artist.name, 'Artist')
        self.assertEqual(artist.prefix, 'The')
        song = Song.objects.get(filename='2-second.mp3')
        self.assertEqual(song.conductor.name, 'Artist')
        self.assertEqual(song.conductor.prefix, 'The')

    def test_update_no_change_prefix_composer(self):
        """
        Test an update of a file which removes the composer prefix on the
        tags - initial prefix on composer should remain in place.
        """
        self.add_mp3(filename='1-first.mp3',
            artist='The Artist', title='Title 1', album = 'Album', composer='The Artist')
        self.add_mp3(filename='2-second.mp3',
            artist='The Artist', title='Title 1', album = 'Album', composer='The Artist')
        self.run_add()

        # Quick verification
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)
        artist = Artist.objects.get(name='Artist')
        self.assertEqual(artist.name, 'Artist')
        self.assertEqual(artist.prefix, 'The')

        # Do the update
        self.update_mp3('2-second.mp3', composer='Artist')
        self.run_update()

        # Check
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)
        artist = Artist.objects.get(name='Artist')
        self.assertEqual(artist.name, 'Artist')
        self.assertEqual(artist.prefix, 'The')
        song = Song.objects.get(filename='2-second.mp3')
        self.assertEqual(song.composer.name, 'Artist')
        self.assertEqual(song.composer.prefix, 'The')

    def test_update_single_artist_to_various(self):
        """
        Tests an update which should transform a single-artist album
        to a Various album.
        """
        tracks = [
            ('Album', '1-first.mp3', 'Artist 1', 'First', 1),
            ('Album', '2-second.mp3', 'Artist 1', 'Second', 2),
        ]
        for (path, filename, artist, title, tracknum) in tracks:
            self.add_mp3(path=path, filename=filename, artist=artist,
                title=title, tracknum=tracknum, album=path)
        self.run_add()

        # Some quick sanity checks
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)
        album = Album.objects.get()
        self.assertEqual(album.artist.name, 'Artist 1')

        # Now make the change
        self.update_mp3('Album/2-second.mp3', artist='Artist 2')
        self.run_update()

        # Now checks
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 3)
        album = Album.objects.get()
        self.assertEqual(album.artist.name, 'Various')

    def test_update_various_artist_to_single(self):
        """
        Tests an update which should transform a various-artist album
        to a single-artist album.
        """
        tracks = [
            ('Album', '1-first.mp3', 'Artist 1', 'First', 1),
            ('Album', '2-second.mp3', 'Artist 2', 'Second', 2),
        ]
        for (path, filename, artist, title, tracknum) in tracks:
            self.add_mp3(path=path, filename=filename, artist=artist,
                title=title, tracknum=tracknum, album=path)
        self.run_add()

        # Some quick sanity checks
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 3)
        album = Album.objects.get()
        self.assertEqual(album.artist.name, 'Various')

        # Now make the change
        self.update_mp3('Album/2-second.mp3', artist='Artist 1')
        self.run_update()

        # Now checks
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)
        album = Album.objects.get()
        self.assertEqual(album.artist.name, 'Artist 1')

    def test_update_various_artist_to_various(self):
        """
        Tests an update which should keep a various-artist album
        as a various-artist album (though with a different artist)
        """
        tracks = [
            ('Album', '1-first.mp3', 'Artist 1', 'First', 1),
            ('Album', '2-second.mp3', 'Artist 2', 'Second', 2),
        ]
        for (path, filename, artist, title, tracknum) in tracks:
            self.add_mp3(path=path, filename=filename, artist=artist,
                title=title, tracknum=tracknum, album=path)
        self.run_add()

        # Some quick sanity checks
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 3)
        album = Album.objects.get()
        self.assertEqual(album.artist.name, 'Various')

        # Now make the change
        self.update_mp3('Album/2-second.mp3', artist='Artist 3')
        self.run_update()

        # Now checks
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 3)
        album = Album.objects.get()
        self.assertEqual(album.artist.name, 'Various')
        for artist in Artist.objects.all():
            self.assertNotEqual(artist.name, 'Artist 2')

    def test_update_song_delete_from_various_to_single(self):
        """
        Test a track deletion with an album which will go from being
        Various Artsits to a single-artist
        """
        self.add_mp3(filename='song.mp3', artist='Artist 1', title='Title',
            album = 'Album')
        self.add_mp3(filename='song2.mp3', artist='Artist 1', title='Title 2',
            album = 'Album')
        self.add_mp3(filename='song3.mp3', artist='Artist 2', title='Title 3',
            album = 'Album')
        self.run_add()

        # Quick verification
        self.assertEqual(Song.objects.count(), 3)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 3)
        album = Album.objects.get()
        self.assertEqual(album.artist.name, 'Various')

        # Now delete
        self.delete_file('song3.mp3')
        self.run_update()

        # Now verify
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)
        album = Album.objects.get()
        self.assertEqual(album.song_set.count(), 2)
        self.assertEqual(album.artist.name, 'Artist 1')
        for song in album.song_set.all():
            self.assertEqual(song.artist.name, 'Artist 1')

    def test_update_entire_album_name_pk_stays_the_same(self):
        """
        Test an update of the album name from all tracks in an
        album.  The primary key of the album should remain the
        same.
        """
        self.add_mp3(filename='song.mp3', artist='Artist 1', title='Title',
            album = 'Old Album')
        self.add_mp3(filename='song2.mp3', artist='Artist 1', title='Title 2',
            album = 'Old Album')
        self.run_add()

        # Some quick checks
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)
        album = Album.objects.get()
        self.assertEqual(album.name, 'Old Album')
        album_pk = album.pk

        # Now do the updates
        self.update_mp3('song.mp3', album='New Album')
        self.update_mp3('song2.mp3', album='New Album')
        self.run_update()

        # Checks
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)
        album = Album.objects.get()
        self.assertEqual(album.name, 'New Album')
        self.assertEqual(album.pk, album_pk)

    def test_update_entire_album_name_umlaut_pk_stays_the_same(self):
        """
        Test an update of the album name from all tracks in an
        album.  The primary key of the album should remain the
        same.
        """
        self.add_mp3(filename='song.mp3', artist='Artist 1', title='Title',
            album = 'Album')
        self.add_mp3(filename='song2.mp3', artist='Artist 1', title='Title 2',
            album = 'Album')
        self.run_add()

        # Some quick checks
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)
        album = Album.objects.get()
        self.assertEqual(album.name, 'Album')
        album_pk = album.pk

        # Now do the updates
        self.update_mp3('song.mp3', album='Albüm')
        self.update_mp3('song2.mp3', album='Albüm')
        self.run_update()

        # Checks
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)
        album = Album.objects.get()
        self.assertEqual(album.name, 'Albüm')
        self.assertEqual(album.pk, album_pk)

    def test_update_entire_album_name_aesc_pk_stays_the_same(self):
        """
        Test an update of the album name from all tracks in an
        album.  The primary key of the album should remain the
        same.
        """
        self.add_mp3(filename='song.mp3', artist='Artist 1', title='Title',
            album = 'Ælbum')
        self.add_mp3(filename='song2.mp3', artist='Artist 1', title='Title 2',
            album = 'Ælbum')
        self.run_add()

        # Some quick checks
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)
        album = Album.objects.get()
        self.assertEqual(album.name, 'Ælbum')
        album_pk = album.pk

        # Now do the updates
        self.update_mp3('song.mp3', album='Aelbum')
        self.update_mp3('song2.mp3', album='Aelbum')
        self.run_update()

        # Checks
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)
        album = Album.objects.get()
        self.assertEqual(album.name, 'Aelbum')
        self.assertEqual(album.pk, album_pk)

    def test_update_split_into_two_albums(self):
        """
        Test an update where a previously-single album is now split into
        two separate albums.
        """
        self.add_mp3(filename='song1.mp3', artist='Artist 1', title='Title 1',
            album = 'Album 1')
        self.add_mp3(filename='song2.mp3', artist='Artist 1', title='Title 2',
            album = 'Album 1')
        self.run_add()

        # Some quick checks
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)

        # Now updates
        self.update_mp3('song1.mp3', album='Album 2')
        self.update_mp3('song2.mp3', album='Album 3')
        self.run_update()

        # Checks
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 2)
        a2 = Album.objects.get(name='Album 2')
        self.assertEqual(a2.name, 'Album 2')
        self.assertEqual(a2.song_set.count(), 1)
        self.assertEqual(a2.song_set.get().title, 'Title 1')
        a3 = Album.objects.get(name='Album 3')
        self.assertEqual(a3.name, 'Album 3')
        self.assertEqual(a3.song_set.count(), 1)
        self.assertEqual(a3.song_set.get().title, 'Title 2')

    def test_update_split_into_extra_album(self):
        """
        Test an update where an album with two tracks is split into two
        albums (but the first track remains in the first album).  In
        this case we expect the "Album 1" album to remain itself (same pk).
        """
        self.add_mp3(filename='song1.mp3', artist='Artist 1', title='Title 1',
            album = 'Album 1')
        self.add_mp3(filename='song2.mp3', artist='Artist 1', title='Title 2',
            album = 'Album 1')
        self.run_add()

        # Some quick checks
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)
        album = Album.objects.get()
        album_pk = album.pk

        # Now updates
        self.update_mp3('song2.mp3', album='Album 2')
        self.run_update()

        # Checks
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 2)
        a1 = Album.objects.get(name='Album 1')
        self.assertEqual(a1.name, 'Album 1')
        self.assertEqual(a1.song_set.count(), 1)
        self.assertEqual(a1.song_set.get().title, 'Title 1')
        a2 = Album.objects.get(name='Album 2')
        self.assertEqual(a1.pk, album_pk)
        self.assertEqual(a2.name, 'Album 2')
        self.assertEqual(a2.song_set.count(), 1)
        self.assertEqual(a2.song_set.get().title, 'Title 2')

    def test_update_split_into_extra_album_2(self):
        """
        Test an update where an album with two tracks is split into two
        albums (but the first track remains in the first album), this
        time with a reversed album title to trigger two different scenarios
        in the update code.  In this case, "Album 1" will get renamed "Album 2"
        and then a new "Album 1" album will be created.  This is subpar, but
        this should only ever happen accidentally anyway, so we'll just Not
        Care.
        """
        self.add_mp3(filename='song1.mp3', artist='Artist 1', title='Title 1',
            album = 'Album 2')
        self.add_mp3(filename='song2.mp3', artist='Artist 1', title='Title 2',
            album = 'Album 2')
        self.run_add()

        # Some quick checks
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)

        # Now updates
        self.update_mp3('song2.mp3', album='Album 1')
        self.run_update()

        # Checks
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 2)
        a2 = Album.objects.get(name='Album 2')
        self.assertEqual(a2.name, 'Album 2')
        self.assertEqual(a2.song_set.count(), 1)
        self.assertEqual(a2.song_set.get().title, 'Title 1')
        a1 = Album.objects.get(name='Album 1')
        self.assertEqual(a1.name, 'Album 1')
        self.assertEqual(a1.song_set.count(), 1)
        self.assertEqual(a1.song_set.get().title, 'Title 2')

    def test_update_two_albums_different_artists_become_one_artist(self):
        """
        Tests having two albums by two different artists, one of which then
        gets updated to have the same artist as the first.
        """
        tracks = [
            ('Album 1', '1-first.mp3', 'Artist 1', 'First', 1),
            ('Album 1', '2-second.mp3', 'Artist 1', 'Second', 2),
            ('Album 2', '1-first.mp3', 'Artist 2', 'First', 1),
            ('Album 2', '2-second.mp3', 'Artist 2', 'Second', 2),
        ]
        for (path, filename, artist, title, tracknum) in tracks:
            self.add_mp3(path=path, filename=filename, artist=artist,
                title=title, tracknum=tracknum, album=path)
        self.run_add()

        # Quick checks
        self.assertEqual(Song.objects.count(), 4)
        self.assertEqual(Album.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 3)

        # Now the update
        self.update_mp3('Album 2/1-first.mp3', artist='Artist 1')
        self.update_mp3('Album 2/2-second.mp3', artist='Artist 1')
        self.run_update()

        # Checks
        self.assertEqual(Song.objects.count(), 4)
        self.assertEqual(Album.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 2)
        artist = Artist.objects.get(name='Artist 1')
        self.assertEqual(artist.album_set.count(), 2)
        album = Album.objects.get(name='Album 2')
        self.assertEqual(album.artist.name, 'Artist 1')

    def test_update_both_new_and_updated_files_to_single_album(self):
        """
        Test a situation where we have a directory with two songs (each
        in their own album), one gets updated to be an album with the
        first, and also a new file is added which is a third track on
        the album.
        """
        self.add_mp3(filename='song1.mp3', artist='Artist 1', title='Title 1',
            album = 'Album 1')
        self.add_mp3(filename='song2.mp3', artist='Artist 1', title='Title 2',
            album = 'Album 2')
        self.run_add()

        # Quick checks
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 2)
        album = Album.objects.get(name='Album 1')
        album_pk = album.pk

        # Now the updates
        self.update_mp3('song2.mp3', album='Album 1')
        self.add_mp3(filename='song3.mp3', artist='Artist 1', title='Title 3',
            album = 'Album 1')
        self.run_update()

        # Now the real checks
        self.assertEqual(Song.objects.count(), 3)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)
        album = Album.objects.get()
        self.assertEqual(album.pk, album_pk)
        self.assertEqual(album.song_set.count(), 3)
        for filename in ['song1.mp3', 'song2.mp3', 'song3.mp3']:
            song = Song.objects.get(filename=filename)
            self.assertEqual(song.album.name, 'Album 1')
            self.assertEqual(song.artist.name, 'Artist 1')

    def test_update_live_album_to_regular_album(self):
        """
        Test updating an album from one which should be live to one that's not
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='2016-09-20 - Live at Somewhere',
            filename='song1.mp3')
        self.run_add()

        self.assertEqual(Song.objects.count(), 1)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)
        album = Album.objects.get()
        album_pk = album.pk
        self.assertEqual(album.live, True)

        self.update_mp3('song1.mp3', album='Album')
        self.run_update()

        self.assertEqual(Song.objects.count(), 1)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)
        album = Album.objects.get()
        self.assertEqual(album_pk, album.pk)
        self.assertEqual(album.live, False)

    def test_update_regular_album_to_live_album(self):
        """
        Test updating an album from one which isn't live to one that's is
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3')
        self.run_add()

        self.assertEqual(Song.objects.count(), 1)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)
        album = Album.objects.get()
        album_pk = album.pk
        self.assertEqual(album.live, False)

        self.update_mp3('song1.mp3', album='2016-09-20 - Live at Somewhere')
        self.run_update()

        self.assertEqual(Song.objects.count(), 1)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)
        album = Album.objects.get()
        self.assertEqual(album_pk, album.pk)
        self.assertEqual(album.live, True)

    def test_update_album_art_empty_string_manually(self):
        """
        This is actually something which would only happen through the admin
        interface, but I don't feel like figuring out how to test admin
        submissions, so we'll just fudge it.  Basically, if empty strings get
        put in for an album's album art fields, we'd like to be sure to save
        them as NULL for consistency's sake.
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3')
        self.run_add()

        self.assertEqual(Song.objects.count(), 1)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Artist.objects.count(), 2)
        album = Album.objects.get()
        self.assertEqual(album.art_filename, None)
        self.assertEqual(album.art_mime, None)
        self.assertEqual(album.art_ext, None)

        # Simulate submitting via the admin area, which will try to
        # use empty strings rather than None/NULL
        album.art_filename = ''
        album.art_mime = ''
        album.art_ext = ''
        album.save()

        # Load again, to be sure, and check.
        album = Album.objects.get()
        self.assertEqual(album.art_filename, None)
        self.assertEqual(album.art_mime, None)
        self.assertEqual(album.art_ext, None)

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

class AlbumModelTests(TestCase):
    """
    Tests for our Album model which don't require our full fake
    library test setup.
    """

    def test_get_total_size_str_zero_bytes(self):
        """
        ``Album.get_total_size_str()`` should return the string "0 B" when the
        total size is zero bytes.  In reality this would never actually happen,
        but we'll test anyway.
        """
        ar = Artist.objects.create(name='Artist', normname='artist')
        al = Album.objects.create(artist = ar, name = 'Album', normname = 'album')
        self.assertEqual(al.get_total_size_str(), '0 B')

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

class IndexViewTests(ExordiumUserTests):
    """
    Tests of our main index view.  (Not a whole lot going on, really)
    """

    def test_no_albums(self):
        """
        Test what happens if there are no albums defined.  (No albums should
        be found in the view's context.)  This test also tests for the various
        links which are supposed to be present on the main page.
        """
        response = self.client.get(reverse('exordium:index'))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['album_list'].data, [])

        self.assertContains(response, 'AnonymousUser')
        self.assertContains(response, reverse('exordium:browse_artist'))
        self.assertContains(response, reverse('exordium:browse_album'))
        self.assertContains(response, reverse('exordium:updateprefs'))

        # We are not authenticated, so we should NOT see any of the admin
        # links anywhere.
        self.assertNotContains(response, reverse('exordium:library'))
        self.assertNotContains(response, reverse('admin:dynamic_preferences_globalpreferencemodel_changelist'))
        self.assertNotContains(response, '%s"' % (reverse('admin:index')))

        # But we SHOULD see a login link
        self.assertContains(response, reverse('admin:login'))

    def test_no_albums_admin(self):
        """
        Test what happens if there are no albums defined.  (No albums should
        be found in the view's context.)  This test also tests for the various
        links which are supposed to be present on the main page.  This time,
        request as if we're an admin.
        """
        self.login()
        response = self.client.get(reverse('exordium:index'))
        self.assertContains(response, 'mainuser')
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['album_list'].data, [])

        self.assertContains(response, 'mainuser')
        self.assertContains(response, reverse('exordium:browse_artist'))
        self.assertContains(response, reverse('exordium:browse_album'))
        self.assertContains(response, reverse('exordium:updateprefs'))

        # We are authenticated, so we should see the admin links.
        self.assertContains(response, reverse('exordium:library'))
        self.assertContains(response, reverse('admin:dynamic_preferences_globalpreferencemodel_changelist'))
        self.assertContains(response, reverse('admin:index'))

        # But we should NOT see a login link
        self.assertNotContains(response, reverse('admin:login'))

    def test_single_album(self):
        """
        Test what happens when there's a single album.  We should see that
        album!
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Test Album', filename='song1.mp3')
        self.run_add()
        self.assertEqual(Album.objects.count(), 1)
        album = Album.objects.get()

        response = self.client.get(reverse('exordium:index'))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['album_list'].data, [repr(album)])
        self.assertContains(response, 'Test Album')
        self.assertContains(response, reverse('exordium:album', args=(album.pk,)))
        self.assertContains(response, reverse('exordium:artist', args=(album.artist.normname,)))
        self.assertContains(response, '1 album')

        # May as well verify that we're seeing the no-album-art cover, as well
        self.assertContains(response, '"%s"' % (static('exordium/no_album_art_small.png')))

    def test_album_art(self):
        """
        Make sure that an album with album art has its art showing in the table.
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Test Album', filename='song1.mp3')
        self.add_art()
        self.run_add()
        self.assertEqual(Album.objects.count(), 1)
        album = Album.objects.get()

        response = self.client.get(reverse('exordium:index'))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['album_list'].data, [repr(album)])
        self.assertContains(response, 'Test Album')
        self.assertContains(response, reverse('exordium:album', args=(album.pk,)))
        self.assertContains(response, reverse('exordium:artist', args=(album.artist.normname,)))
        self.assertContains(response, reverse('exordium:albumart', args=(album.pk, 'list',)))

    def test_four_albums(self):
        """
        Test what happens when there's four albums.  Ensure that they are
        sorted properly.
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album 1', filename='song1.mp3')
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album 2', filename='song2.mp3')
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album 3', filename='song3.mp3')
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album 4', filename='song4.mp3')
        self.run_add()
        album_2 = self.age_album('Artist', 'Album 2', 2)
        album_3 = self.age_album('Artist', 'Album 3', 4)
        album_4 = self.age_album('Artist', 'Album 4', 6)
        self.assertEqual(Album.objects.count(), 4)
        album_1 = Album.objects.get(name='Album 1')

        response = self.client.get(reverse('exordium:index'))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['album_list'].data,
            [repr(al) for al in [album_1, album_2, album_3, album_4]])
        self.assertContains(response, 'Album 1')
        self.assertContains(response, 'Album 2')
        self.assertContains(response, 'Album 3')
        self.assertContains(response, 'Album 4')
        self.assertContains(response, '4 albums')

    def test_classical_album(self):
        """
        Test the display of an album with classical tags
        """
        self.add_mp3(artist='Artist', title='Title 1',
            group='Group', conductor='Conductor', composer='Composer',
            album='Album 1', filename='song1.mp3')
        self.run_add()

        self.assertEqual(Artist.objects.count(), 5)
        self.assertEqual(Album.objects.count(), 1)

        album = Album.objects.get()
        artists = []

        response = self.client.get(reverse('exordium:index'))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['album_list'].data, [repr(album)])
        self.assertContains(response, 'Album 1')
        self.assertContains(response, reverse('exordium:album', args=(album.pk,)))
        self.assertContains(response, reverse('exordium:artist', args=(album.artist.normname,)))
        for artist in Artist.objects.exclude(name='Various'):
            self.assertContains(response, str(artist))
            self.assertContains(response, reverse('exordium:artist', args=(artist.normname,)))

    def test_classical_album_two_tracks(self):
        """
        Test the display of an album with classical tags.  Two tracks, where
        the artist stays the same but the other classical tags differ.
        """
        self.add_mp3(artist='Artist', title='Title 1',
            group='Group', conductor='Conductor', composer='Composer',
            album='Album 1', filename='song1.mp3')
        self.add_mp3(artist='Artist', title='Title 2',
            group='Group 2', conductor='Conductor 2', composer='Composer 2',
            album='Album 1', filename='song2.mp3')
        self.run_add()

        self.assertEqual(Artist.objects.count(), 8)
        self.assertEqual(Album.objects.count(), 1)

        album = Album.objects.get()
        artists = []

        response = self.client.get(reverse('exordium:index'))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['album_list'].data, [repr(album)])
        self.assertContains(response, 'Album 1')
        self.assertContains(response, reverse('exordium:album', args=(album.pk,)))
        self.assertContains(response, reverse('exordium:artist', args=(album.artist.normname,)))
        for artist in Artist.objects.exclude(name='Various'):
            self.assertContains(response, str(artist))
            self.assertContains(response, reverse('exordium:artist', args=(artist.normname,)))

    def test_various_album(self):
        """
        Test display of a Various Artists album
        """
        self.add_mp3(artist='Artist 1', title='Title 1',
            album='Album', filename='song1.mp3')
        self.add_mp3(artist='Artist 2', title='Title 2',
            album='Album', filename='song2.mp3')
        self.run_add()

        self.assertEqual(Artist.objects.count(), 3)
        self.assertEqual(Album.objects.count(), 1)
        artist_1 = Artist.objects.get(name='Artist 1')
        artist_2 = Artist.objects.get(name='Artist 2')
        various = Artist.objects.get(name='Various')
        album = Album.objects.get()

        response = self.client.get(reverse('exordium:index'))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['album_list'].data, [repr(album)])
        self.assertContains(response, 'Album')
        self.assertContains(response, reverse('exordium:album', args=(album.pk,)))
        self.assertContains(response, reverse('exordium:artist', args=(album.artist.normname,)))
        self.assertContains(response, reverse('exordium:artist', args=(various.normname,)))
        for artist in [artist_1, artist_2]:
            self.assertNotContains(response, str(artist_1))
            self.assertNotContains(response, reverse('exordium:artist', args=(artist.normname,)))

    def test_classical_album_two_tracks_various(self):
        """
        Test the display of an album with classical tags.  Two tracks, where
        all artist fields change, so it's a Various Artists album.
        """
        self.add_mp3(artist='Artist 1', title='Title 1',
            group='Group', conductor='Conductor', composer='Composer',
            album='Album 1', filename='song1.mp3')
        self.add_mp3(artist='Artist 2', title='Title 2',
            group='Group 2', conductor='Conductor 2', composer='Composer 2',
            album='Album 1', filename='song2.mp3')
        self.run_add()

        self.assertEqual(Artist.objects.count(), 9)
        self.assertEqual(Album.objects.count(), 1)

        album = Album.objects.get()
        artists = []

        various = Artist.objects.get(name='Various')

        response = self.client.get(reverse('exordium:index'))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['album_list'].data, [repr(album)])
        self.assertContains(response, 'Album 1')
        self.assertContains(response, reverse('exordium:album', args=(album.pk,)))
        self.assertContains(response, reverse('exordium:artist', args=(album.artist.normname,)))
        self.assertContains(response, reverse('exordium:artist', args=(various.normname,)))
        for artist in Artist.objects.exclude(Q(name='Artist 1') | Q(name='Artist 2')):
            self.assertContains(response, str(artist))
            self.assertContains(response, reverse('exordium:artist', args=(artist.normname,)))
        for artist in Artist.objects.filter(Q(name='Artist 1') | Q(name='Artist 2')):
            self.assertNotContains(response, str(artist))
            self.assertNotContains(response, reverse('exordium:artist', args=(artist.normname,)))

    def test_pagination(self):
        """
        Test to make sure that our pagination is working properly.
        The index page will show a total of 20 albums
        """
        for num in range(30):
            self.add_mp3(artist='Artist', title='Title %d' % (num+1),
                album='Album %d' % (num+1), filename='song%d.mp3' % (num+1))
        self.run_add()
        self.assertEqual(Album.objects.count(), 30)

        albums = {}
        for num in range(30):
            self.age_album(artist='Artist',
                album='Album %d' % (num+1),
                age_days=num+1)
            albums[num] = Album.objects.get(name='Album %d' % (num+1))

        response = self.client.get(reverse('exordium:index'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['album_list'].data), 30)
        for num in range(20):
            self.assertContains(response, '%s<' % (albums[num]))
            self.assertContains(response, reverse('exordium:album', args=(albums[num].pk,)))
        for num in range(20, 30):
            self.assertNotContains(response, '%s<' % (albums[num]))
            self.assertNotContains(response, reverse('exordium:album', args=(albums[num].pk,)))
        self.assertContains(response, '20 of 30 albums')
        self.assertContains(response, '"?page=2"')

        # test page 2
        response = self.client.get(reverse('exordium:index'), {'page': 2})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['album_list'].data), 30)
        for num in range(20):
            self.assertNotContains(response, '%s<' % (albums[num]))
            self.assertNotContains(response, reverse('exordium:album', args=(albums[num].pk,)))
        for num in range(20, 30):
            self.assertContains(response, '%s<' % (albums[num]))
            self.assertContains(response, reverse('exordium:album', args=(albums[num].pk,)))
        self.assertContains(response, '10 of 30 albums')
        self.assertContains(response, '"?page=1"')

    def test_sorting(self):
        """
        Test for at least one sorting link
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album 1', filename='song1.mp3', year=2016)
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album 2', filename='song2.mp3', year=2006)
        self.run_add()

        self.assertEqual(Album.objects.count(), 2)
        album_2 = self.age_album('Artist', 'Album 2', 2)
        album_1 = Album.objects.get(name='Album 1')

        # Initial view, should be sorted by addition time
        response = self.client.get(reverse('exordium:index'))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['album_list'].data,
            [repr(al) for al in [album_1, album_2]])
        self.assertContains(response, 'Album 1')
        self.assertContains(response, 'Album 2')
        self.assertContains(response, '"?sort=year"')

        # Now sort by year
        response = self.client.get(reverse('exordium:index'), {'sort': 'year'})
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['album_list'].data,
            [repr(al) for al in [album_2, album_1]])
        self.assertContains(response, 'Album 1')
        self.assertContains(response, 'Album 2')
        self.assertContains(response, '"?sort=-year"')

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

        # Next: submit our preferences form to enable show_live.
        response = self.client.post(reverse('exordium:updateprefs'), {'show_live': 'yes'})
        self.assertRedirects(response, reverse('exordium:index'), fetch_redirect_response=False)
        response = self.client.get(reverse('exordium:index'))
        self.assertEqual(UserAwareView.get_preference_static(response.wsgi_request, 'show_live'), True)
        self.assertIn('exordium__show_live', response.wsgi_request.session)
        self.assertEqual(response.wsgi_request.session['exordium__show_live'], True)
        self.assertContains(response, 'Set user preferences')

        # And now, submit one more, flipping back to False.
        response = self.client.post(reverse('exordium:updateprefs'), {})
        self.assertRedirects(response, reverse('exordium:index'), fetch_redirect_response=False)
        response = self.client.get(reverse('exordium:index'))
        self.assertEqual(UserAwareView.get_preference_static(response.wsgi_request, 'show_live'), False)
        self.assertIn('exordium__show_live', response.wsgi_request.session)
        self.assertEqual(response.wsgi_request.session['exordium__show_live'], False)
        self.assertContains(response, 'Set user preferences')

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

        # And now, submit one more, flipping back to False.  Once again, the extra
        # redirect to index is a bit gratuitous.
        response = self.client.post(reverse('exordium:updateprefs'), {})
        self.assertRedirects(response, reverse('exordium:index'), fetch_redirect_response=False)
        response = self.client.get(reverse('exordium:index'))
        self.assertEqual(UserAwareView.get_preference_static(response.wsgi_request, 'show_live'), False)
        self.assertNotIn('exordium__show_live', response.wsgi_request.session)
        self.assertEqual(response.wsgi_request.user.preferences['exordium__show_live'], False)
        self.assertContains(response, 'Set user preferences')

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

class BrowseArtistViewTests(ExordiumTests):
    """
    Tests of our Browse Artists page
    """

    def test_no_artists(self):
        """
        Test the view when there are no artists (except for Various)
        """
        various = Artist.objects.get()

        response = self.client.get(reverse('exordium:browse_artist'))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['table'].data, [repr(various)])
        self.assertContains(response, '1 artist')
        self.assertContains(response, reverse('exordium:artist', args=(various.normname,)))

    def test_one_artists(self):
        """
        Test the view when there is one artist (and Various)
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album 1', filename='song1.mp3')
        self.run_add()

        various = Artist.objects.get(normname='various')
        artist = Artist.objects.get(normname='artist')

        response = self.client.get(reverse('exordium:browse_artist'))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['table'].data, [repr(artist), repr(various)])
        self.assertContains(response, '2 artists')
        for a in [various, artist]:
            self.assertContains(response, reverse('exordium:artist', args=(a.normname,)))

    def test_ten_artists(self):
        """
        Test the view when there are a bunch of artists
        """
        artists = ['Adipiscing',
            'Amet',
            'Congue',
            'Consectetur',
            'Dolor',
            'Elit',
            'Ipsum',
            'Lorem',
            'Sit',
            'Vivamus',
        ]
        for (idx, artist) in enumerate(artists):
            self.add_mp3(artist=artist, title='Title %d' % (idx+1),
                album='Album', filename='song%d.mp3' % (idx+1))
        self.run_add()

        # add Various to our list, in the properly-sorted place.
        artists.insert(9, 'Various')
        artist_objs = []
        for artist in artists:
            artist_objs.append(Artist.objects.get(name=artist))

        response = self.client.get(reverse('exordium:browse_artist'))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['table'].data,
            [repr(artist) for artist in artist_objs])
        self.assertContains(response, '11 artists')
        for artist in artist_objs:
            self.assertContains(response, reverse('exordium:artist',
                args=(artist.normname,)))

    def test_classical_song(self):
        """
        Test the view when a single song created multiple artists
        """
        self.add_mp3(artist='Artist', group='Group',
            conductor='Conductor', composer='Composer',
            title='Title', album='Album', filename='song1.mp3')
        self.run_add()

        self.assertEqual(Artist.objects.count(), 5)
        artists = [
            Artist.objects.get(name='Artist'),
            Artist.objects.get(name='Composer'),
            Artist.objects.get(name='Conductor'),
            Artist.objects.get(name='Group'),
            Artist.objects.get(name='Various'),
        ]

        response = self.client.get(reverse('exordium:browse_artist'))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['table'].data,
            [repr(artist) for artist in artists])
        self.assertContains(response, '5 artists')
        for artist in artists:
            self.assertContains(response, str(artist))
            self.assertContains(response, reverse('exordium:artist',
                args=(artist.normname,)))

    def test_pagination(self):
        """
        Test to make sure that our pagination is working properly.
        The Browse Artists page will show a total of 25 artists
        """
        for num in range(30):
            self.add_mp3(artist='Artist %02d' % (num+1), title='Title %d' % (num+1),
                album='Album %d' % (num+1), filename='song%d.mp3' % (num+1))
        self.run_add()
        self.assertEqual(Artist.objects.count(), 31)

        artists = {}
        for num in range(30):
            artists[num] = Artist.objects.get(name='Artist %02d' % (num+1))

        response = self.client.get(reverse('exordium:browse_artist'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['table'].data), 31)
        for num in range(25):
            self.assertContains(response, '%s<' % (artists[num]))
            self.assertContains(response, reverse('exordium:artist', args=(artists[num].normname,)))
        for num in range(25, 30):
            self.assertNotContains(response, '%s<' % (artists[num]))
            self.assertNotContains(response, reverse('exordium:artist', args=(artists[num].normname,)))
        self.assertNotContains(response, 'Various<')
        self.assertContains(response, '25 of 31 artists')
        self.assertContains(response, '"?page=2"')

        # test page 2
        response = self.client.get(reverse('exordium:browse_artist'), {'page': 2})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['table'].data), 31)
        for num in range(25):
            self.assertNotContains(response, '%s<' % (artists[num]))
            self.assertNotContains(response, reverse('exordium:artist', args=(artists[num].normname,)))
        for num in range(25, 30):
            self.assertContains(response, '%s<' % (artists[num]))
            self.assertContains(response, reverse('exordium:artist', args=(artists[num].normname,)))
        self.assertContains(response, 'Various<')
        self.assertContains(response, '6 of 31 artists')
        self.assertContains(response, '"?page=1"')

    def test_sorting(self):
        """
        Test at least one sort
        """
        self.add_mp3(artist='A Artist', title='Title 1',
            album='Album 1', filename='song1.mp3')
        self.add_mp3(artist='B Artist', title='Title 2',
            album='Album 2', filename='song2.mp3')
        self.run_add()

        various = Artist.objects.get(normname='various')
        artist_a = Artist.objects.get(normname='a artist')
        artist_b = Artist.objects.get(normname='b artist')

        # Initial view, artist name.
        response = self.client.get(reverse('exordium:browse_artist'))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['table'].data,
            [repr(artist_a), repr(artist_b), repr(various)])
        self.assertContains(response, "?sort=-name")

        # Now sort by name descending
        response = self.client.get(reverse('exordium:browse_artist'), {'sort': '-name'})
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['table'].data,
            [repr(various), repr(artist_b), repr(artist_a)])
        self.assertContains(response, "?sort=name")

class BrowseAlbumViewTests(ExordiumTests):
    """
    Tests of our Browse Album page
    """

    def test_no_albums(self):
        """
        Test the view when there are no albums
        """
        response = self.client.get(reverse('exordium:browse_album'))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['table'].data, [])

    def test_one_album(self):
        """
        Test the view when there is one album
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3')
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        album = Album.objects.get()

        response = self.client.get(reverse('exordium:browse_album'))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['table'].data, [repr(album)])
        self.assertContains(response, '1 album')
        self.assertContains(response, reverse('exordium:album', args=(album.pk,)))
        self.assertContains(response, reverse('exordium:artist', args=(album.artist.normname,)))
        self.assertContains(response, '"%s"' % (static('exordium/no_album_art_small.png')))

    def test_one_album_with_art(self):
        """
        Test the view when there is one album, with album art
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3')
        self.add_art()
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        album = Album.objects.get()

        response = self.client.get(reverse('exordium:browse_album'))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['table'].data, [repr(album)])
        self.assertContains(response, '1 album')
        self.assertContains(response, reverse('exordium:album', args=(album.pk,)))
        self.assertContains(response, reverse('exordium:artist', args=(album.artist.normname,)))
        self.assertContains(response, reverse('exordium:albumart', args=(album.pk, 'list',)))

    def test_ordering_three_regular_albums(self):
        """
        Test ordering with three "regular" albums.  Should be alphabetical by
        album name.
        """
        self.add_mp3(artist='Zebra', title='Title 1',
            album='Z Album', filename='song1.mp3')
        self.add_mp3(artist='Artist', title='Title 1',
            album='R Album', filename='song2.mp3')
        self.add_mp3(artist='Zebra', title='Title 1',
            album='Album', filename='song3.mp3')
        self.run_add()

        self.assertEqual(Album.objects.count(), 3)
        albums = [
            Album.objects.get(normname='album'),
            Album.objects.get(normname='r album'),
            Album.objects.get(normname='z album'),
        ]

        response = self.client.get(reverse('exordium:browse_album'))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['table'].data, [repr(al) for al in albums])
        self.assertContains(response, '3 albums')
        for al in albums:
            self.assertContains(response, reverse('exordium:album', args=(al.pk,)))
            self.assertContains(response, reverse('exordium:artist', args=(al.artist.normname,)))

    def test_ordering_miscellaneous_albums(self):
        """
        By default, "miscellaneous" (non-album) albums should come at
        the end of the list.
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Z Album', filename='song1.mp3')
        self.add_mp3(artist='Artist', title='Title 2',
            album='S Album', filename='song2.mp3')
        self.add_mp3(artist='Artist', title='Title 3',
            filename='song3.mp3')
        self.add_mp3(artist='Zebra', title='Title 4',
            album='C Album', filename='song4.mp3')
        self.add_mp3(artist='Zebra', title='Title 5',
            album='V Album', filename='song5.mp3')
        self.add_mp3(artist='Zebra', title='Title 6',
            filename='song6.mp3')
        self.add_mp3(artist='Yellow', title='Title 7',
            filename='song7.mp3')
        self.run_add()

        self.assertEqual(Album.objects.count(), 7)
        albums = []
        for albumname in [
                'C Album',
                'S Album',
                'V Album',
                'Z Album',
                Album.miscellaneous_format_str % ('Artist'),
                Album.miscellaneous_format_str % ('Yellow'),
                Album.miscellaneous_format_str % ('Zebra'),
                ]:
            albums.append(Album.objects.get(name=albumname))

        response = self.client.get(reverse('exordium:browse_album'))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['table'].data, [repr(al) for al in albums])
        self.assertContains(response, '7 albums')
        for al in albums:
            self.assertContains(response, reverse('exordium:album', args=(al.pk,)))
            self.assertContains(response, reverse('exordium:artist', args=(al.artist.normname,)))

    def test_classical_album(self):
        """
        Test the display of an album with classical tags
        """
        self.add_mp3(artist='Artist', title='Title 1',
            group='Group', conductor='Conductor', composer='Composer',
            album='Album 1', filename='song1.mp3')
        self.run_add()

        self.assertEqual(Artist.objects.count(), 5)
        self.assertEqual(Album.objects.count(), 1)

        album = Album.objects.get()
        artists = []

        response = self.client.get(reverse('exordium:browse_album'))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['table'].data, [repr(album)])
        self.assertContains(response, 'Album 1')
        self.assertContains(response, reverse('exordium:album', args=(album.pk,)))
        self.assertContains(response, reverse('exordium:artist', args=(album.artist.normname,)))
        for artist in Artist.objects.exclude(name='Various'):
            self.assertContains(response, str(artist))
            self.assertContains(response, reverse('exordium:artist', args=(artist.normname,)))

    def test_classical_album_two_tracks(self):
        """
        Test the display of an album with classical tags.  Two tracks, where
        the artist stays the same but the other classical tags differ.
        """
        self.add_mp3(artist='Artist', title='Title 1',
            group='Group', conductor='Conductor', composer='Composer',
            album='Album 1', filename='song1.mp3')
        self.add_mp3(artist='Artist', title='Title 2',
            group='Group 2', conductor='Conductor 2', composer='Composer 2',
            album='Album 1', filename='song2.mp3')
        self.run_add()

        self.assertEqual(Artist.objects.count(), 8)
        self.assertEqual(Album.objects.count(), 1)

        album = Album.objects.get()
        artists = []

        response = self.client.get(reverse('exordium:browse_album'))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['table'].data, [repr(album)])
        self.assertContains(response, 'Album 1')
        self.assertContains(response, reverse('exordium:album', args=(album.pk,)))
        self.assertContains(response, reverse('exordium:artist', args=(album.artist.normname,)))
        for artist in Artist.objects.exclude(name='Various'):
            self.assertContains(response, str(artist))
            self.assertContains(response, reverse('exordium:artist', args=(artist.normname,)))

    def test_various_album(self):
        """
        Test display of a Various Artists album
        """
        self.add_mp3(artist='Artist 1', title='Title 1',
            album='Album', filename='song1.mp3')
        self.add_mp3(artist='Artist 2', title='Title 2',
            album='Album', filename='song2.mp3')
        self.run_add()

        self.assertEqual(Artist.objects.count(), 3)
        self.assertEqual(Album.objects.count(), 1)
        artist_1 = Artist.objects.get(name='Artist 1')
        artist_2 = Artist.objects.get(name='Artist 2')
        various = Artist.objects.get(name='Various')
        album = Album.objects.get()

        response = self.client.get(reverse('exordium:browse_album'))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['table'].data, [repr(album)])
        self.assertContains(response, 'Album')
        self.assertContains(response, reverse('exordium:album', args=(album.pk,)))
        self.assertContains(response, reverse('exordium:artist', args=(album.artist.normname,)))
        self.assertContains(response, reverse('exordium:artist', args=(various.normname,)))
        for artist in [artist_1, artist_2]:
            self.assertNotContains(response, str(artist_1))
            self.assertNotContains(response, reverse('exordium:artist', args=(artist.normname,)))

    def test_classical_album_two_tracks_various(self):
        """
        Test the display of an album with classical tags.  Two tracks, where
        all artist fields change, so it's a Various Artists album.
        """
        self.add_mp3(artist='Artist 1', title='Title 1',
            group='Group', conductor='Conductor', composer='Composer',
            album='Album 1', filename='song1.mp3')
        self.add_mp3(artist='Artist 2', title='Title 2',
            group='Group 2', conductor='Conductor 2', composer='Composer 2',
            album='Album 1', filename='song2.mp3')
        self.run_add()

        self.assertEqual(Artist.objects.count(), 9)
        self.assertEqual(Album.objects.count(), 1)

        album = Album.objects.get()
        artists = []

        various = Artist.objects.get(name='Various')

        response = self.client.get(reverse('exordium:browse_album'))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['table'].data, [repr(album)])
        self.assertContains(response, 'Album 1')
        self.assertContains(response, reverse('exordium:album', args=(album.pk,)))
        self.assertContains(response, reverse('exordium:artist', args=(album.artist.normname,)))
        self.assertContains(response, reverse('exordium:artist', args=(various.normname,)))
        for artist in Artist.objects.exclude(Q(name='Artist 1') | Q(name='Artist 2')):
            self.assertContains(response, str(artist))
            self.assertContains(response, reverse('exordium:artist', args=(artist.normname,)))
        for artist in Artist.objects.filter(Q(name='Artist 1') | Q(name='Artist 2')):
            self.assertNotContains(response, str(artist))
            self.assertNotContains(response, reverse('exordium:artist', args=(artist.normname,)))

    def test_pagination(self):
        """
        Test to make sure that our pagination is working properly.
        The album browse page will show a total of 50 albums
        """
        for num in range(60):
            self.add_mp3(artist='Artist', title='Title %d' % (num+1),
                album='Album %02d' % (num+1), filename='song%d.mp3' % (num+1))
        self.run_add()
        self.assertEqual(Album.objects.count(), 60)

        albums = {}
        for num in range(60):
            albums[num] = Album.objects.get(name='Album %02d' % (num+1))

        response = self.client.get(reverse('exordium:browse_album'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['table'].data), 60)
        for num in range(50):
            self.assertContains(response, '%s<' % (albums[num]))
            self.assertContains(response, reverse('exordium:album', args=(albums[num].pk,)))
        for num in range(50, 60):
            self.assertNotContains(response, '%s<' % (albums[num]))
            self.assertNotContains(response, reverse('exordium:album', args=(albums[num].pk,)))
        self.assertContains(response, '50 of 60 albums')
        self.assertContains(response, '"?page=2"')

        # test page 2
        response = self.client.get(reverse('exordium:browse_album'), {'page': 2})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['table'].data), 60)
        for num in range(50):
            self.assertNotContains(response, '%s<' % (albums[num]))
            self.assertNotContains(response, reverse('exordium:album', args=(albums[num].pk,)))
        for num in range(50, 60):
            self.assertContains(response, '%s<' % (albums[num]))
            self.assertContains(response, reverse('exordium:album', args=(albums[num].pk,)))
        self.assertContains(response, '10 of 60 albums')
        self.assertContains(response, '"?page=1"')

    def test_sorting(self):
        """
        Test at least one case of sorting.
        """
        self.add_mp3(artist='Zed', title='Title 1',
            album='Album 1', filename='song1.mp3')
        self.add_mp3(artist='Gee', title='Title 2',
            album='Album 2', filename='song2.mp3')
        self.add_mp3(artist='Artist', title='Title 3',
            album='Album 3', filename='song3.mp3')
        self.run_add()
        self.assertEqual(Album.objects.count(), 3)

        albums = [
            Album.objects.get(name='Album 1'),
            Album.objects.get(name='Album 2'),
            Album.objects.get(name='Album 3'),
        ]
        response = self.client.get(reverse('exordium:browse_album'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['table'].data), 3)
        self.assertQuerysetEqual(response.context['table'].data, [repr(al) for al in albums])
        self.assertContains(response, '"?sort=artist"')

        # test the sorting button
        response = self.client.get(reverse('exordium:browse_album'), {'sort': 'artist'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['table'].data), 3)
        self.assertQuerysetEqual(response.context['table'].data, [repr(al) for al in reversed(albums)])
        self.assertContains(response, '"?sort=-artist"')

class ArtistViewTests(ExordiumTests):
    """
    Tests of our Artist info page
    """

    def test_invalid_artist(self):
        """
        Tests making a request for an artist which can't be found.
        """
        response = self.client.get(reverse('exordium:artist', args=('notfound',)))
        self.assertEqual(response.status_code, 404)

    def test_single_album(self):
        """
        Test an artist who only has a single album
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3')
        self.run_add()
        
        self.assertEqual(Artist.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Song.objects.count(), 1)

        artist = Artist.objects.get(name='Artist')
        album = Album.objects.get()
        song = Song.objects.get()

        response = self.client.get(reverse('exordium:artist', args=('artist',)))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['albums'].data, [repr(album)])
        self.assertEqual(response.context['have_songs'], True)
        self.assertQuerysetEqual(response.context['songs'].data, [repr(song)])
        self.assertContains(response, 'Songs by %s' % (artist))
        self.assertContains(response, reverse('exordium:artist', args=(artist.normname,)))
        self.assertContains(response, reverse('exordium:album', args=(album.pk,)))
        self.assertContains(response, song.get_download_url())
        self.assertContains(response, '1 album')
        self.assertContains(response, '1 song')

        # May as well double-check the no-album-art-found image as well
        self.assertContains(response, '"%s"' % (static('exordium/no_album_art_small.png')))

        # Artist song-list view should not have the tracknum column, and should have album-sort
        self.assertNotContains(response, 'sort=tracknum')
        self.assertContains(response, 'song-sort=album')

    def test_single_album_with_art(self):
        """
        Test an artist who only has a single album, with album art.
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3')
        self.add_art()
        self.run_add()
        
        self.assertEqual(Artist.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        self.assertEqual(Song.objects.count(), 1)

        artist = Artist.objects.get(name='Artist')
        album = Album.objects.get()
        song = Song.objects.get()

        response = self.client.get(reverse('exordium:artist', args=('artist',)))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['albums'].data, [repr(album)])
        self.assertEqual(response.context['have_songs'], True)
        self.assertQuerysetEqual(response.context['songs'].data, [repr(song)])
        self.assertContains(response, '1 album')
        self.assertContains(response, '1 song')
        self.assertContains(response, 'Songs by %s' % (artist))
        self.assertContains(response, reverse('exordium:artist', args=(artist.normname,)))
        self.assertContains(response, reverse('exordium:album', args=(album.pk,)))
        self.assertContains(response, reverse('exordium:albumart', args=(album.pk, 'list',)))
        self.assertContains(response, song.get_download_url())
        self.assertNotContains(response, 'sort=tracknum')
        self.assertContains(response, 'song-sort=album')

    def test_various_artists(self):
        """
        Test a various artist album - the one containing the artist
        we care about should show up in the list
        """
        self.add_mp3(artist='Artist 1', title='Title 1',
            album='Album 1', filename='song1.mp3', path='album_1')
        self.add_mp3(artist='Artist 2', title='Title 2',
            album='Album 1', filename='song2.mp3', path='album_1')
        self.add_mp3(artist='Artist 2', title='Title 3',
            album='Album 2', filename='song3.mp3', path='album_2')
        self.add_mp3(artist='Artist 3', title='Title 4',
            album='Album 2', filename='song4.mp3', path='album_2')
        self.run_add()

        self.assertEqual(Artist.objects.count(), 4)
        self.assertEqual(Album.objects.count(), 2)
        self.assertEqual(Song.objects.count(), 4)

        artist_1 = Artist.objects.get(name='Artist 1')
        artist_2 = Artist.objects.get(name='Artist 2')
        artist_3 = Artist.objects.get(name='Artist 3')
        various = Artist.objects.get(name='Various')

        album_1 = Album.objects.get(name='Album 1')
        album_2 = Album.objects.get(name='Album 2')

        song_1 = Song.objects.get(filename='album_1/song1.mp3')
        song_2 = Song.objects.get(filename='album_1/song2.mp3')
        song_3 = Song.objects.get(filename='album_2/song3.mp3')
        song_4 = Song.objects.get(filename='album_2/song4.mp3')

        response = self.client.get(reverse('exordium:artist', args=(artist_1.normname,)))
        self.assertEqual(response.status_code, 200)

        # Only the Various Artists album should show up
        self.assertContains(response, '1 album')
        self.assertQuerysetEqual(response.context['albums'].data, [repr(album_1)])
        self.assertContains(response, reverse('exordium:album', args=(album_1.pk,)))
        self.assertContains(response, reverse('exordium:artist', args=(various.normname,)))
        self.assertNotContains(response, str(album_2))
        self.assertNotContains(response, reverse('exordium:album', args=(album_2.pk,)))

        # Only one song should show up
        self.assertContains(response, '1 song')
        self.assertQuerysetEqual(response.context['songs'].data, [repr(song_1)])
        self.assertContains(response, reverse('exordium:artist', args=(artist_1.normname,)))
        # This check is a bit silly since it's already shown up above
        self.assertContains(response, reverse('exordium:album', args=(album_1.pk,)))
        self.assertContains(response, song_1.get_download_url())
        for song in [song_2, song_3, song_4]:
            self.assertNotContains(response, str(song))
            self.assertNotContains(response, song.get_download_url())

        # Shouldn't see any links to our other two artists
        for artist in [artist_2, artist_3]:
            self.assertNotContains(response, str(artist))
            self.assertNotContains(response, reverse('exordium:artist', args=(artist.normname,)))

    def test_ordering(self):
        """
        Tests ordering of various types of albums.  Regular albums should be first,
        followed by non-album tracks, and then Various-artists albums.  Song lists
        should be alphabetical.
        """
        # "Album 1" and "Album 3" are regular albums
        # "Album 2" is V/A
        # The remaining track will create a non-album track.
        self.add_mp3(artist='Artist 1', title='Title 1',
            album='Album 1', filename='song1.mp3', path='album_1')
        self.add_mp3(artist='Artist 1', title='Title 2',
            album='Album 1', filename='song2.mp3', path='album_1')
        self.add_mp3(artist='Artist 1', title='Title 3',
            album='Album 2', filename='song3.mp3', path='album_2')
        self.add_mp3(artist='Artist 2', title='Title 4',
            album='Album 2', filename='song4.mp3', path='album_2')
        self.add_mp3(artist='Artist 1', title='Title 5',
            album='Album 3', filename='song5.mp3', path='album_3')
        self.add_mp3(artist='Artist 1', title='Title 6',
            album='Album 3', filename='song6.mp3', path='album_3')
        self.add_mp3(artist='Artist 1', title='Title 7',
            filename='song7.mp3')
        self.run_add()

        artist = Artist.objects.get(name='Artist 1')

        self.assertEqual(Album.objects.count(), 4)
        reg_album_1 = Album.objects.get(name='Album 1')
        reg_album_2 = Album.objects.get(name='Album 3')
        va_album = Album.objects.get(name='Album 2')
        misc_album = Album.objects.get(miscellaneous=True)

        response = self.client.get(reverse('exordium:artist', args=(artist.normname,)))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '4 albums')
        self.assertContains(response, '6 songs')
        self.assertQuerysetEqual(response.context['albums'].data,
            [repr(al) for al in [reg_album_1, reg_album_2, misc_album, va_album]])
        self.assertQuerysetEqual(response.context['songs'].data,
            [repr(s) for s in Song.objects.filter(artist=artist).order_by('title')])

        # There are certainly some duplicate tests happening down here.
        for album in [reg_album_1, reg_album_2, misc_album, va_album]:
            self.assertContains(response, str(album))
            self.assertContains(response, str(album.artist))
            self.assertContains(response, reverse('exordium:album', args=(album.pk,)))
            self.assertContains(response, reverse('exordium:artist', args=(album.artist.normname,)))
        for song in Song.objects.filter(artist=artist):
            self.assertContains(response, str(song.title))
            self.assertContains(response, song.get_download_url())
        for song in Song.objects.exclude(artist=artist):
            self.assertNotContains(response, str(song.title))
            self.assertNotContains(response, song.get_download_url())

    def test_classical_as_conductor(self):
        """
        Test the scenario where our only track is as a conductor on
        a track on an album tagged with classical stuff.
        """
        self.add_mp3(artist='Artist 1', title='Title 1',
            group='Group 1', conductor='Conductor 1', composer='Composer 1',
            album='Album 1', filename='song1.mp3', path='album_1')
        self.add_mp3(artist='Artist 1', title='Title 2',
            group='Group 2', conductor='Conductor 2', composer='Composer 2',
            album='Album 1', filename='song2.mp3', path='album_1')
        self.run_add()

        self.assertEqual(Artist.objects.count(), 8)
        artist = Artist.objects.get(name='Conductor 2')

        self.assertEqual(Album.objects.count(), 1)
        album = Album.objects.get()

        self.assertEqual(Song.objects.count(), 2)
        song_1 = Song.objects.get(title='Title 1')
        song_2 = Song.objects.get(title='Title 2')

        response = self.client.get(reverse('exordium:artist', args=(artist.normname,)))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['albums'].data, [repr(album)])
        self.assertContains(response, '1 album')
        self.assertQuerysetEqual(response.context['songs'].data, [repr(song_2)])
        self.assertContains(response, '1 song')
        self.assertContains(response, str(album))
        self.assertContains(response, reverse('exordium:album', args=(album.pk,)))
        
        for artist in Artist.objects.exclude(name='Various'):
            self.assertContains(response, str(artist))
            self.assertContains(response, reverse('exordium:artist', args=(artist.normname,)))

        self.assertNotContains(response, str(song_1))
        self.assertNotContains(response, song_1.get_download_url())
        self.assertContains(response, str(song_2))
        self.assertContains(response, song_2.get_download_url())

    def test_classical_as_conductor_various(self):
        """
        Test the scenario where our only track is as a conductor on
        a track on an album tagged with classical stuff.  Also the
        album is classified as Various Artists
        """
        self.add_mp3(artist='Artist 1', title='Title 1',
            group='Group 1', conductor='Conductor 1', composer='Composer 1',
            album='Album 1', filename='song1.mp3', path='album_1')
        self.add_mp3(artist='Artist 2', title='Title 2',
            group='Group 2', conductor='Conductor 2', composer='Composer 2',
            album='Album 1', filename='song2.mp3', path='album_1')
        self.run_add()

        self.assertEqual(Artist.objects.count(), 9)
        artist = Artist.objects.get(name='Conductor 2')

        self.assertEqual(Album.objects.count(), 1)
        album = Album.objects.get()

        self.assertEqual(Song.objects.count(), 2)
        song_1 = Song.objects.get(title='Title 1')
        song_2 = Song.objects.get(title='Title 2')

        response = self.client.get(reverse('exordium:artist', args=(artist.normname,)))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['albums'].data, [repr(album)])
        self.assertContains(response, '1 album')
        self.assertQuerysetEqual(response.context['songs'].data, [repr(song_2)])
        self.assertContains(response, '1 song')
        self.assertContains(response, str(album))
        self.assertContains(response, reverse('exordium:album', args=(album.pk,)))
        
        for artist in Artist.objects.exclude(name='Artist 1'):
            self.assertContains(response, str(artist))
            self.assertContains(response, reverse('exordium:artist', args=(artist.normname,)))
        for artist in Artist.objects.filter(name='Artist 1'):
            self.assertNotContains(response, str(artist))
            self.assertNotContains(response, reverse('exordium:artist', args=(artist.normname,)))

        self.assertNotContains(response, str(song_1))
        self.assertNotContains(response, song_1.get_download_url())
        self.assertContains(response, str(song_2))
        self.assertContains(response, song_2.get_download_url())

    def test_pagination(self):
        """
        Test pagination.  To actually use assertNotContains we have to do both
        album and song pagination at the same time, so we'll go ahead and do that
        rather than splitting them into separate tests.  We show 50 albums and
        25 songs on the artist page.
        """
        for num in range(60):
            self.add_mp3(artist='Artist', title='Title %02d' % (num+1),
                album='Album %02d' % (num+1), filename='song%d.mp3' % (num+1))
        self.run_add()
        self.assertEqual(Album.objects.count(), 60)

        self.assertEqual(Artist.objects.count(), 2)
        artist = Artist.objects.get(name='Artist')

        albums = {}
        for num in range(60):
            albums[num] = Album.objects.get(name='Album %02d' % (num+1))

        songs = {}
        for num in range(60):
            songs[num] = Song.objects.get(title='Title %02d' % (num+1))

        response = self.client.get(reverse('exordium:artist', args=(artist.normname,)))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '50 of 60 albums')
        self.assertContains(response, '25 of 60 songs')
        self.assertContains(response, '"?album-page=2"')
        self.assertContains(response, '"?song-page=2"')
        self.assertEqual(len(response.context['albums'].data), 60)
        self.assertEqual(len(response.context['songs'].data), 60)
        for num in range(50):
            self.assertContains(response, '%s<' % (albums[num]))
            self.assertContains(response, reverse('exordium:album', args=(albums[num].pk,)))
        for num in range(50, 60):
            self.assertNotContains(response, '%s<' % (albums[num]))
            self.assertNotContains(response, reverse('exordium:album', args=(albums[num].pk,)))
        for num in range(25):
            self.assertContains(response, '%s<' % (songs[num]))
        for num in range(25, 60):
            self.assertNotContains(response, '%s<' % (songs[num]))

        # test page 2/3
        response = self.client.get(reverse('exordium:artist', args=(artist.normname,)), {'album-page': 2, 'song-page': 3})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '10 of 60 albums')
        self.assertContains(response, '10 of 60 songs')
        self.assertContains(response, 'album-page=1')
        self.assertContains(response, 'song-page=2')
        self.assertEqual(len(response.context['albums'].data), 60)
        self.assertEqual(len(response.context['songs'].data), 60)
        for num in range(50):
            self.assertNotContains(response, '%s<' % (albums[num]))
            self.assertNotContains(response, reverse('exordium:album', args=(albums[num].pk,)))
        for num in range(50, 60):
            self.assertContains(response, '%s<' % (albums[num]))
            self.assertContains(response, reverse('exordium:album', args=(albums[num].pk,)))
        for num in range(50):
            self.assertNotContains(response, '%s<' % (songs[num]))
        for num in range(50, 60):
            self.assertContains(response, '%s<' % (songs[num]))

    def test_sorting_album(self):
        """
        Test at least one case of album sorting.
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album 1', year=2016, filename='song1.mp3')
        self.add_mp3(artist='Artist', title='Title 2',
            album='Album 2', year=2006, filename='song2.mp3')
        self.add_mp3(artist='Artist', title='Title 3',
            album='Album 3', year=1996, filename='song3.mp3')
        self.run_add()
        self.assertEqual(Album.objects.count(), 3)

        albums = [
            Album.objects.get(name='Album 1'),
            Album.objects.get(name='Album 2'),
            Album.objects.get(name='Album 3'),
        ]
        artist = Artist.objects.get(name='Artist')

        response = self.client.get(reverse('exordium:artist', args=(artist.normname,)))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['albums'].data), 3)
        self.assertQuerysetEqual(response.context['albums'].data, [repr(al) for al in albums])
        self.assertContains(response, '"?album-sort=year"')

        # test the sorting button
        response = self.client.get(reverse('exordium:artist', args=(artist.normname,)), {'album-sort': 'year'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['albums'].data), 3)
        self.assertQuerysetEqual(response.context['albums'].data, [repr(al) for al in reversed(albums)])
        self.assertContains(response, '"?album-sort=-year"')

    def test_sorting_song(self):
        """
        Test at least one case of song sorting.
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album 3', filename='song1.mp3')
        self.add_mp3(artist='Artist', title='Title 2',
            album='Album 2', filename='song2.mp3')
        self.add_mp3(artist='Artist', title='Title 3',
            album='Album 1', filename='song3.mp3')
        self.run_add()
        self.assertEqual(Album.objects.count(), 3)

        songs = [
            Song.objects.get(title='Title 1'),
            Song.objects.get(title='Title 2'),
            Song.objects.get(title='Title 3'),
        ]
        artist = Artist.objects.get(name='Artist')

        response = self.client.get(reverse('exordium:artist', args=(artist.normname,)))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['songs'].data), 3)
        self.assertQuerysetEqual(response.context['songs'].data, [repr(al) for al in songs])
        self.assertContains(response, '"?song-sort=album"')

        # test the sorting button
        response = self.client.get(reverse('exordium:artist', args=(artist.normname,)), {'song-sort': 'album'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['songs'].data), 3)
        self.assertQuerysetEqual(response.context['songs'].data, [repr(al) for al in reversed(songs)])
        self.assertContains(response, '"?song-sort=-album"')

    def test_too_many_songs(self):
        """
        If an artist has more than 500 songs, the song list won't be
        shown on the artist page.  We're going to cheat here and
        insert directly into the database rather than going through our
        ``run_add()`` rigamarole.  Quite possibly I should be doing that
        on all our pagination tests, too, since those are noticeably
        slow.  Ah well.
        """
        artist = Artist.objects.create(name='Artist', normname='artist')
        album = Album.objects.create(artist=artist, name='Album', normname='album')
        for num in range(501):
            Song.objects.create(filename='file%03d.mp3' % (num+1),
                artist=artist,
                album=album,
                title='Title %03d' % (num+1),
                year=0,
                tracknum=0,
                normtitle='title %03d' % (num+1),
                raw_artist='artist',
                filetype=Song.MP3,
                bitrate=128000,
                mode=Song.CBR,
                size=123000,
                length=90,
                sha256sum='0cf31fc7d968ec16c69758f9b0ebb2355471d5694a151b40e5e4f8641b061092',
            )

        response = self.client.get(reverse('exordium:artist', args=(artist.normname,)))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['albums'].data, [repr(album)])
        self.assertEqual(response.context['have_songs'], False)
        self.assertNotIn('songs', response.context)
        self.assertNotContains(response, 'Songs by %s' % (artist))
        self.assertContains(response, reverse('exordium:artist', args=(artist.normname,)))
        self.assertContains(response, reverse('exordium:album', args=(album.pk,)))
        self.assertContains(response, '1 album')
        self.assertNotContains(response, '1 song')

class AlbumViewTests(ExordiumUserTests):
    """
    Tests of our Album info page
    """

    def test_invalid_album(self):
        """
        Tests making a request for an album which can't be found.
        """
        response = self.client.get(reverse('exordium:album', args=(42,)))
        self.assertEqual(response.status_code, 404)

    def test_minimal_album(self):
        """
        Test a minimally-tagged album
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3')
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        album = Album.objects.get()

        self.assertEqual(Song.objects.count(), 1)
        song = Song.objects.get()

        response = self.client.get(reverse('exordium:album', args=(album.pk,)))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['songs'].data, [repr(song)])
        self.assertEqual(response.context['groups'], [])
        self.assertEqual(response.context['composers'], [])
        self.assertEqual(response.context['conductors'], [])
        self.assertNotContains(response, 'Ensemble')
        self.assertNotContains(response, 'Conductor')
        self.assertNotContains(response, 'Composer')
        self.assertContains(response, reverse('exordium:artist', args=(album.artist.normname,)))
        self.assertContains(response, str(album))
        self.assertContains(response, str(album.artist))
        self.assertNotContains(response, 'Year:')
        self.assertContains(response, 'Tracks: <strong>1</strong>')
        self.assertContains(response, 'Length: <strong>0:02</strong>')
        self.assertContains(response, 'Added on:')
        self.assertContains(response, reverse('exordium:m3udownload', args=(album.pk,)))
        self.assertContains(response, 'albumstreambutton')
        self.assertContains(response, '"%s"' % (static('exordium/no_album_art.png')))
        self.assertContains(response, song.title)
        self.assertContains(response, '1 item')

        # Ensure we have a tracknum column, but not an album column
        self.assertContains(response, '"?sort=tracknum"')
        self.assertNotContains(response, '"?sort=album"')

        # At the moment we do not have album downloads enabled, so we should not see
        # the download button.
        self.assertNotContains(response, reverse('exordium:albumdownload', args=(album.pk,)))

        # We are not logged in, so we shouldn't see the album art regen button
        self.assertNotContains(response, reverse('exordium:albumartupdate', args=(album.pk,)))

    def test_minimal_album_art(self):
        """
        Test a minimally-tagged album which also has album art.
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3')
        self.add_art()
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        album = Album.objects.get()

        self.assertEqual(Song.objects.count(), 1)
        song = Song.objects.get()

        response = self.client.get(reverse('exordium:album', args=(album.pk,)))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['songs'].data, [repr(song)])
        self.assertEqual(response.context['groups'], [])
        self.assertEqual(response.context['composers'], [])
        self.assertEqual(response.context['conductors'], [])
        self.assertNotContains(response, 'Ensemble')
        self.assertNotContains(response, 'Conductor')
        self.assertNotContains(response, 'Composer')
        self.assertContains(response, reverse('exordium:artist', args=(album.artist.normname,)))
        self.assertContains(response, str(album))
        self.assertContains(response, str(album.artist))
        self.assertNotContains(response, 'Year:')
        self.assertContains(response, 'Tracks: <strong>1</strong>')
        self.assertContains(response, 'Length: <strong>0:02</strong>')
        self.assertContains(response, 'Added on:')
        self.assertContains(response, reverse('exordium:m3udownload', args=(album.pk,)))
        self.assertContains(response, 'albumstreambutton')
        self.assertNotContains(response, '"%s"' % (static('exordium/no_album_art.png')))
        self.assertContains(response, reverse('exordium:albumart', args=(album.pk, 'album',)))
        self.assertContains(response, reverse('exordium:origalbumart', args=(album.pk, album.art_ext,)))
        self.assertContains(response, song.title)
        self.assertContains(response, '1 item')

        # Ensure we have a tracknum column, but not an album column
        self.assertContains(response, '"?sort=tracknum"')
        self.assertNotContains(response, '"?sort=album"')

        # At the moment we do not have album downloads enabled, so we should not see
        # the download button.
        self.assertNotContains(response, reverse('exordium:albumdownload', args=(album.pk,)))

        # We are not logged in, so we shouldn't see the album art regen button
        self.assertNotContains(response, reverse('exordium:albumartupdate', args=(album.pk,)))

    def test_login_album_no_art(self):
        """
        Test view when we're logged in and have no album art.  Should see our
        update button now.
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3')
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        album = Album.objects.get()

        self.login()
        response = self.client.get(reverse('exordium:album', args=(album.pk,)))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '"%s"' % (static('exordium/no_album_art.png')))
        self.assertContains(response, reverse('exordium:albumartupdate', args=(album.pk,)))

    def test_login_album_with_art(self):
        """
        Test view when we're logged in and have album art.  Should have our update button.
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3')
        self.add_art()
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        album = Album.objects.get()

        self.login()
        response = self.client.get(reverse('exordium:album', args=(album.pk,)))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, '"%s"' % (static('exordium/no_album_art.png')))
        self.assertContains(response, reverse('exordium:albumart', args=(album.pk, 'album',)))
        self.assertContains(response, reverse('exordium:origalbumart', args=(album.pk, album.art_ext,)))
        self.assertContains(response, reverse('exordium:albumartupdate', args=(album.pk,)))

    def test_fully_tagged_album(self):
        """
        Test a fully-tagged album
        """
        self.add_mp3(artist='Artist', title='Title 1', tracknum=1,
            year=2016, group='Group', conductor='Conductor',
            composer='Composer',
            album='Album', filename='song1.mp3')
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        album = Album.objects.get()

        self.assertEqual(Song.objects.count(), 1)
        song = Song.objects.get()

        artist = Artist.objects.get(name='Artist')
        group = Artist.objects.get(name='Group')
        conductor = Artist.objects.get(name='Conductor')
        composer = Artist.objects.get(name='Composer')

        response = self.client.get(reverse('exordium:album', args=(album.pk,)))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['songs'].data, [repr(song)])
        self.assertQuerysetEqual(response.context['groups'], [repr(group)])
        self.assertQuerysetEqual(response.context['composers'], [repr(composer)])
        self.assertQuerysetEqual(response.context['conductors'], [repr(conductor)])
        self.assertEqual(response.context['have_empty_group'], False)
        self.assertEqual(response.context['have_empty_composer'], False)
        self.assertEqual(response.context['have_empty_conductor'], False)
        self.assertContains(response, 'Ensemble:')
        self.assertContains(response, 'Conductor:')
        self.assertContains(response, 'Composer:')
        self.assertContains(response, reverse('exordium:artist', args=(album.artist.normname,)))
        self.assertContains(response, reverse('exordium:artist', args=(group.normname,)))
        self.assertContains(response, reverse('exordium:artist', args=(conductor.normname,)))
        self.assertContains(response, reverse('exordium:artist', args=(composer.normname,)))
        self.assertContains(response, str(album))
        self.assertContains(response, str(album.artist))
        self.assertContains(response, str(group))
        self.assertContains(response, str(conductor))
        self.assertContains(response, str(composer))
        self.assertContains(response, 'Year: <strong>2016</strong>')
        self.assertContains(response, 'Tracks: <strong>1</strong>')
        self.assertContains(response, 'Length: <strong>0:02</strong>')
        self.assertContains(response, song.title)
        self.assertContains(response, '"?sort=tracknum"')
        self.assertContains(response, '1 item')

    def test_fully_tagged_album_two_tracks(self):
        """
        Test a fully-tagged album, with two tracks
        """
        self.add_mp3(artist='Artist', title='Title 1', tracknum=1,
            year=2016, group='Group', conductor='Conductor',
            composer='Composer',
            album='Album', filename='song1.mp3')
        self.add_mp3(artist='Artist', title='Title 2', tracknum=2,
            year=2016, group='Group 2', conductor='Conductor 2',
            composer='Composer 2',
            album='Album', filename='song2.mp3')
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        album = Album.objects.get()

        self.assertEqual(Song.objects.count(), 2)
        songs = [
            Song.objects.get(filename='song1.mp3'),
            Song.objects.get(filename='song2.mp3'),
        ]

        artist = Artist.objects.get(name='Artist')
        groups = [
            Artist.objects.get(name='Group'),
            Artist.objects.get(name='Group 2'),
        ]
        conductors = [
            Artist.objects.get(name='Conductor'),
            Artist.objects.get(name='Conductor 2'),
        ]
        composers = [
            Artist.objects.get(name='Composer'),
            Artist.objects.get(name='Composer 2'),
        ]

        response = self.client.get(reverse('exordium:album', args=(album.pk,)))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['songs'].data, [repr(song) for song in songs])
        self.assertQuerysetEqual(response.context['groups'], [repr(group) for group in groups])
        self.assertQuerysetEqual(response.context['composers'], [repr(composer) for composer in composers])
        self.assertQuerysetEqual(response.context['conductors'], [repr(conductor) for conductor in conductors])
        self.assertEqual(response.context['have_empty_group'], False)
        self.assertEqual(response.context['have_empty_composer'], False)
        self.assertEqual(response.context['have_empty_conductor'], False)
        self.assertContains(response, 'Ensembles:')
        self.assertContains(response, 'Conductors:')
        self.assertContains(response, 'Composers:')
        for a in [artist] + groups + conductors + composers:
            self.assertContains(response, reverse('exordium:artist', args=(a.normname,)))
            self.assertContains(response, str(a))
        self.assertContains(response, str(album))
        self.assertContains(response, str(album.artist))
        self.assertContains(response, 'Year: <strong>2016</strong>')
        self.assertContains(response, 'Tracks: <strong>2</strong>')
        self.assertContains(response, 'Length: <strong>0:04</strong>')
        for song in songs:
            self.assertContains(response, song.title)
        self.assertContains(response, '"?sort=tracknum"')
        self.assertContains(response, '2 items')

    def test_fully_tagged_album_two_tracks_various(self):
        """
        Test a fully-tagged album, with two tracks, which is also a various-artists
        album.
        """
        self.add_mp3(artist='Artist 1', title='Title 1', tracknum=1,
            year=2016, group='Group 1', conductor='Conductor 1',
            composer='Composer 1',
            album='Album', filename='song1.mp3')
        self.add_mp3(artist='Artist 2', title='Title 2', tracknum=2,
            year=2016, group='Group 2', conductor='Conductor 2',
            composer='Composer 2',
            album='Album', filename='song2.mp3')
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        album = Album.objects.get()

        self.assertEqual(Song.objects.count(), 2)
        songs = [
            Song.objects.get(filename='song1.mp3'),
            Song.objects.get(filename='song2.mp3'),
        ]

        various = Artist.objects.get(name='Various')
        artists = [
            Artist.objects.get(name='Artist 1'),
            Artist.objects.get(name='Artist 2'),
        ]
        groups = [
            Artist.objects.get(name='Group 1'),
            Artist.objects.get(name='Group 2'),
        ]
        conductors = [
            Artist.objects.get(name='Conductor 1'),
            Artist.objects.get(name='Conductor 2'),
        ]
        composers = [
            Artist.objects.get(name='Composer 1'),
            Artist.objects.get(name='Composer 2'),
        ]

        response = self.client.get(reverse('exordium:album', args=(album.pk,)))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Various')
        self.assertContains(response, reverse('exordium:artist', args=(various.normname,)))
        self.assertQuerysetEqual(response.context['songs'].data, [repr(song) for song in songs])
        self.assertQuerysetEqual(response.context['groups'], [repr(group) for group in groups])
        self.assertQuerysetEqual(response.context['composers'], [repr(composer) for composer in composers])
        self.assertQuerysetEqual(response.context['conductors'], [repr(conductor) for conductor in conductors])
        self.assertEqual(response.context['have_empty_group'], False)
        self.assertEqual(response.context['have_empty_composer'], False)
        self.assertEqual(response.context['have_empty_conductor'], False)
        self.assertContains(response, 'Ensembles:')
        self.assertContains(response, 'Conductors:')
        self.assertContains(response, 'Composers:')
        for a in artists + groups + conductors + composers:
            self.assertContains(response, reverse('exordium:artist', args=(a.normname,)))
            self.assertContains(response, str(a))
        self.assertContains(response, str(album))
        self.assertContains(response, str(album.artist))
        self.assertContains(response, 'Year: <strong>2016</strong>')
        self.assertContains(response, 'Tracks: <strong>2</strong>')
        self.assertContains(response, 'Length: <strong>0:04</strong>')
        for song in songs:
            self.assertContains(response, song.title)
        self.assertContains(response, '"?sort=tracknum"')
        self.assertContains(response, '2 items')

    def test_album_some_tracks_with_classical_tags_others_without(self):
        """
        Tests display of an album in which one track has classical tags defined
        but the other does not.  The classical tags should be displayed up in
        the top header, but also with a note that some tracks don't have the
        tags.  Technically we should have a check for making sure the tracks
        themselves are showing the information, though we can't really do that
        without hooking into selenium or whatever.
        """
        self.add_mp3(artist='Artist', title='Title 1', tracknum=1,
            year=2016, group='Group', conductor='Conductor',
            composer='Composer',
            album='Album', filename='song1.mp3')
        self.add_mp3(artist='Artist', title='Title 2', tracknum=2,
            year=2016, album='Album', filename='song2.mp3')
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        album = Album.objects.get()

        self.assertEqual(Song.objects.count(), 2)
        songs = [
            Song.objects.get(filename='song1.mp3'),
            Song.objects.get(filename='song2.mp3'),
        ]

        artist = Artist.objects.get(name='Artist')
        group = Artist.objects.get(name='Group')
        conductor = Artist.objects.get(name='Conductor')
        composer = Artist.objects.get(name='Composer')

        response = self.client.get(reverse('exordium:album', args=(album.pk,)))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['songs'].data, [repr(song) for song in songs])
        self.assertQuerysetEqual(response.context['groups'], [repr(group)])
        self.assertQuerysetEqual(response.context['composers'], [repr(composer)])
        self.assertQuerysetEqual(response.context['conductors'], [repr(conductor)])
        self.assertEqual(response.context['have_empty_group'], True)
        self.assertEqual(response.context['have_empty_composer'], True)
        self.assertEqual(response.context['have_empty_conductor'], True)
        self.assertContains(response, 'Ensemble:')
        self.assertContains(response, 'Conductor:')
        self.assertContains(response, 'Composer:')
        self.assertContains(response, 'Some tracks have no ensemble')
        self.assertContains(response, 'Some tracks have no conductor')
        self.assertContains(response, 'Some tracks have no composer')
        for a in [artist, group, conductor, composer]:
            self.assertContains(response, reverse('exordium:artist', args=(a.normname,)))
            self.assertContains(response, str(a))
        self.assertContains(response, str(album))
        self.assertContains(response, str(album.artist))
        self.assertContains(response, 'Year: <strong>2016</strong>')
        self.assertContains(response, 'Tracks: <strong>2</strong>')
        self.assertContains(response, 'Length: <strong>0:04</strong>')
        for song in songs:
            self.assertContains(response, song.title)
        self.assertContains(response, '"?sort=tracknum"')
        self.assertContains(response, '2 items')

    def test_miscellaneous_album(self):
        """
        Test a miscellaneous (non-album-tracks) album.  The only real difference
        is that this table should NOT contain a tracknum column.
        """
        self.add_mp3(artist='Artist', title='Title 1', filename='song1.mp3')
        self.run_add()

        self.assertEqual(Song.objects.count(), 1)
        song = Song.objects.get()

        self.assertEqual(Album.objects.count(), 1)
        album = Album.objects.get()

        response = self.client.get(reverse('exordium:album', args=(album.pk,)))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['songs'].data, [repr(song)])
        self.assertContains(response, song.title)
        self.assertNotContains(response, '"?sort=tracknum"')
        self.assertContains(response, '1 item')

    def test_sorting_song(self):
        """
        Test at least one case of song sorting.  Default sorting is by track
        number.
        """
        self.add_mp3(artist='Artist', title='Title 3', tracknum=1,
            album='Album', filename='song1.mp3')
        self.add_mp3(artist='Artist', title='Title 2', tracknum=2,
            album='Album', filename='song2.mp3')
        self.add_mp3(artist='Artist', title='Title 1', tracknum=3,
            album='Album', filename='song3.mp3')
        self.run_add()

        songs = [
            Song.objects.get(filename='song1.mp3'),
            Song.objects.get(filename='song2.mp3'),
            Song.objects.get(filename='song3.mp3'),
        ]
        album = Album.objects.get(name='Album')

        response = self.client.get(reverse('exordium:album', args=(album.pk,)))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['songs'].data), 3)
        self.assertQuerysetEqual(response.context['songs'].data, [repr(song) for song in songs])
        self.assertContains(response, '"?sort=title"')
        self.assertContains(response, '3 items')

        # test the sorting button
        response = self.client.get(reverse('exordium:album', args=(album.pk,)), {'sort': 'title'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['songs'].data), 3)
        self.assertQuerysetEqual(response.context['songs'].data, [repr(song) for song in reversed(songs)])
        self.assertContains(response, '"?sort=-title"')
        self.assertContains(response, '3 items')

    def test_pagination(self):
        """
        Test pagination.  Our album view will show 100 tracks, so rather than
        going through our whole ``run_add()`` process, we're just importing
        directly into the database.  Should probably do this for the rest of our
        pagination tests, too, actually, given that ``run_add()`` can be rather
        slow.
        """
        artist = Artist.objects.create(name='Artist', normname='artist')
        album = Album.objects.create(artist=artist, name='Album', normname='album')
        songs = {}
        for num in range(120):
            songs[num] = Song.objects.create(filename='file%03d.mp3' % (num+1),
                artist=artist,
                album=album,
                title='Title %03d' % (num+1),
                year=2016,
                tracknum=num+1,
                normtitle='title %03d' % (num+1),
                raw_artist='artist',
                filetype=Song.MP3,
                bitrate=128000,
                mode=Song.CBR,
                size=123000,
                length=90,
                sha256sum='0cf31fc7d968ec16c69758f9b0ebb2355471d5694a151b40e5e4f8641b061092',
            )

        response = self.client.get(reverse('exordium:album', args=(album.pk,)))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '100 of 120 items')
        self.assertContains(response, '"?page=2"')
        self.assertEqual(len(response.context['songs'].data), 120)
        for num in range(100):
            self.assertContains(response, '%s<' % (songs[num]))
            self.assertContains(response, '"%s"' % (songs[num].get_download_url()))
        for num in range(100, 120):
            self.assertNotContains(response, '%s<' % (songs[num]))
            self.assertNotContains(response, '"%s"' % (songs[num].get_download_url()))

        # test page 2
        response = self.client.get(reverse('exordium:album', args=(album.pk,)), {'page': 2})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '20 of 120 items')
        self.assertContains(response, '"?page=1"')
        self.assertEqual(len(response.context['songs'].data), 120)
        for num in range(100):
            self.assertNotContains(response, '%s<' % (songs[num]))
            self.assertNotContains(response, '"%s"' % (songs[num].get_download_url()))
        for num in range(100, 120):
            self.assertContains(response, '%s<' % (songs[num]))
            self.assertContains(response, '"%s"' % (songs[num].get_download_url()))

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

class AlbumM3UDownloadViewTests(ExordiumTests):
    """
    Tests for our album M3U downloads
    """

    def test_invalid_album(self):
        """
        Tests making a request for an album which can't be found.
        """
        response = self.client.get(reverse('exordium:m3udownload', args=(42,)))
        self.assertEqual(response.status_code, 404)

    def test_one_track_album(self):
        """
        Test getting a one-track album M3U
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3')
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        album = Album.objects.get()

        self.assertEqual(Song.objects.count(), 1)
        song = Song.objects.get()

        response = self.client.get(reverse('exordium:m3udownload', args=(album.pk,)))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'audio/mpegurl')
        self.assertEqual(response['Content-Disposition'], 'attachment; filename=Artist_-_Album.m3u')
        self.assertContains(response, '#EXTM3U')
        self.assertContains(response, '#EXTINF:')
        self.assertContains(response, str(song.artist))
        self.assertContains(response, str(song.title))
        self.assertContains(response, '(%s)' % (str(song.album)))
        self.assertContains(response, song.get_download_url())

    def test_three_track_album(self):
        """
        Test getting a three-track album M3U
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3')
        self.add_mp3(artist='Artist', title='Title 2',
            album='Album', filename='song2.mp3')
        self.add_mp3(artist='Artist', title='Title 3',
            album='Album', filename='song3.mp3')
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        album = Album.objects.get()

        self.assertEqual(Song.objects.count(), 3)

        response = self.client.get(reverse('exordium:m3udownload', args=(album.pk,)))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'audio/mpegurl')
        self.assertEqual(response['Content-Disposition'], 'attachment; filename=Artist_-_Album.m3u')
        self.assertContains(response, '#EXTM3U')
        self.assertContains(response, '#EXTINF:')
        self.assertContains(response, '(%s)' % (str(album)))
        for song in Song.objects.all():
            self.assertContains(response, str(song.artist))
            self.assertContains(response, str(song.title))
            self.assertContains(response, song.get_download_url())

class SearchViewTests(ExordiumTests):
    """
    Tests for our search page.
    """

    def test_empty_search_string(self):
        """
        Test what happens with an empty search string.
        """

        response = self.client.get(reverse('exordium:search'), {'q': ''})
        self.assertEqual(response.status_code, 200)
        self.assertIn('length_error', response.context)
        self.assertNotIn('song_results', response.context)
        self.assertNotIn('album_results', response.context)
        self.assertNotIn('artist_results', response.context)
        self.assertNotIn('found_results', response.context)
        self.assertContains(response, 'Search strings must be at least three characters')

    def test_short_search_string(self):
        """
        Test what happens with a short search string.  Shoul be the same
        results as for no search string, really.
        """

        response = self.client.get(reverse('exordium:search'), {'q': 'qu'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('length_error', response.context)
        self.assertNotIn('song_results', response.context)
        self.assertNotIn('album_results', response.context)
        self.assertNotIn('artist_results', response.context)
        self.assertNotIn('found_results', response.context)
        self.assertContains(response, 'Search strings must be at least three characters')

    def test_no_results(self):
        """
        Test what happens when there are literally no results.
        """

        response = self.client.get(reverse('exordium:search'), {'q': 'que'})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('length_error', response.context)
        self.assertNotIn('song_results', response.context)
        self.assertNotIn('album_results', response.context)
        self.assertNotIn('artist_results', response.context)
        self.assertIn('found_results', response.context)
        self.assertEqual(response.context['found_results'], False)
        self.assertContains(response, 'No results found!')

    def test_find_artist(self):
        """
        Test a successful search for an artist
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3')
        self.run_add()

        artist = Artist.objects.get(name='Artist')

        response = self.client.get(reverse('exordium:search'), {'q': 'artist'})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('song_results', response.context)
        self.assertNotIn('album_results', response.context)
        self.assertIn('artist_results', response.context)
        self.assertIn('found_results', response.context)
        self.assertEqual(response.context['found_results'], True)
        self.assertNotContains(response, 'No results found!')

        self.assertQuerysetEqual(response.context['artist_results'].data, [repr(artist)])
        self.assertContains(response, 'Artists')
        self.assertContains(response, '%s<' % (artist))
        self.assertContains(response, reverse('exordium:artist', args=(artist.normname,)))
        self.assertContains(response, '1 artist')

    def test_with_linefeed(self):
        """
        Test a search with a linefeed in the search string - should only
        search for the bit before the newline
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3')
        self.run_add()

        artist = Artist.objects.get(name='Artist')

        response = self.client.get(reverse('exordium:search'), {'q': "artist\nname"})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('song_results', response.context)
        self.assertNotIn('album_results', response.context)
        self.assertIn('artist_results', response.context)
        self.assertIn('found_results', response.context)
        self.assertEqual(response.context['found_results'], True)
        self.assertNotContains(response, 'No results found!')

        self.assertQuerysetEqual(response.context['artist_results'].data, [repr(artist)])
        self.assertContains(response, 'Artists')
        self.assertContains(response, '%s<' % (artist))
        self.assertContains(response, reverse('exordium:artist', args=(artist.normname,)))
        self.assertContains(response, '1 artist')

    def test_with_carriagereturn(self):
        """
        Test a search with a carriage return in the search string - should only
        search for the bit before the newline
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3')
        self.run_add()

        artist = Artist.objects.get(name='Artist')

        response = self.client.get(reverse('exordium:search'), {'q': "artist\rname"})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('song_results', response.context)
        self.assertNotIn('album_results', response.context)
        self.assertIn('artist_results', response.context)
        self.assertIn('found_results', response.context)
        self.assertEqual(response.context['found_results'], True)
        self.assertNotContains(response, 'No results found!')

        self.assertQuerysetEqual(response.context['artist_results'].data, [repr(artist)])
        self.assertContains(response, 'Artists')
        self.assertContains(response, '%s<' % (artist))
        self.assertContains(response, reverse('exordium:artist', args=(artist.normname,)))
        self.assertContains(response, '1 artist')

    def test_with_very_long_search(self):
        """
        We limit searches to 80 characters - anything more than that
        will get truncated.  I'm... not exactly sure why I'm doing that?
        I guess it does seem like a good idea to put some kind of a cap
        on that, lest the database complain or something, but I rather
        doubt it would actually be a problem.  Whatever, we'll test for
        it anyway.
        """
        self.add_mp3(artist='here is a very long artist name whose name exceeds eighty characters and we will search on it',
            title='Title 1', album='Album', filename='song1.mp3')
        self.run_add()

        artist = Artist.objects.get(name__startswith='here is a very')

        response = self.client.get(reverse('exordium:search'),
            {'q': 'here is a very long artist name whose name exceeds eighty characters and we will search xyzzy'})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('song_results', response.context)
        self.assertNotIn('album_results', response.context)
        self.assertIn('artist_results', response.context)
        self.assertIn('found_results', response.context)
        self.assertEqual(response.context['found_results'], True)
        self.assertNotContains(response, 'No results found!')

        self.assertQuerysetEqual(response.context['artist_results'].data, [repr(artist)])
        self.assertContains(response, 'Artists')
        self.assertContains(response, '%s<' % (artist))
        self.assertContains(response, reverse('exordium:artist', args=(artist.normname,)))
        self.assertContains(response, '1 artist')

    def test_find_album(self):
        """
        Test a successful search for an album
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3')
        self.run_add()

        album = Album.objects.get()

        response = self.client.get(reverse('exordium:search'), {'q': 'album'})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('song_results', response.context)
        self.assertIn('album_results', response.context)
        self.assertNotIn('artist_results', response.context)
        self.assertIn('found_results', response.context)
        self.assertEqual(response.context['found_results'], True)
        self.assertNotContains(response, 'No results found!')

        self.assertQuerysetEqual(response.context['album_results'].data, [repr(album)])
        self.assertContains(response, 'Albums')
        self.assertContains(response, '%s<' % (album))
        self.assertContains(response, reverse('exordium:album', args=(album.pk,)))
        self.assertContains(response, reverse('exordium:artist', args=(album.artist.normname,)))
        self.assertContains(response, '1 album')

    def test_find_song(self):
        """
        Test a successful search for a song
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='song1.mp3')
        self.run_add()

        song = Song.objects.get()

        response = self.client.get(reverse('exordium:search'), {'q': 'title'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('song_results', response.context)
        self.assertNotIn('album_results', response.context)
        self.assertNotIn('artist_results', response.context)
        self.assertIn('found_results', response.context)
        self.assertEqual(response.context['found_results'], True)
        self.assertNotContains(response, 'No results found!')

        self.assertQuerysetEqual(response.context['song_results'].data, [repr(song)])
        self.assertContains(response, 'Songs')
        self.assertContains(response, '%s<' % (song.title))
        self.assertContains(response, reverse('exordium:album', args=(song.album.pk,)))
        self.assertContains(response, reverse('exordium:artist', args=(song.artist.normname,)))
        self.assertContains(response, '1 song')

    def test_find_all(self):
        """
        Test a successful search which finds one of each type
        """
        self.add_mp3(artist='Artist Ocelot', title='Title Ocelot',
            album='Album Ocelot', filename='song1.mp3')
        self.run_add()

        song = Song.objects.get()
        album = Album.objects.get()
        artist = Artist.objects.get(name='Artist Ocelot')

        response = self.client.get(reverse('exordium:search'), {'q': 'ocelot'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('song_results', response.context)
        self.assertIn('album_results', response.context)
        self.assertIn('artist_results', response.context)
        self.assertIn('found_results', response.context)
        self.assertEqual(response.context['found_results'], True)
        self.assertNotContains(response, 'No results found!')

        self.assertQuerysetEqual(response.context['artist_results'].data, [repr(artist)])
        self.assertContains(response, 'Artists')
        self.assertContains(response, '%s<' % (artist))
        self.assertContains(response, reverse('exordium:artist', args=(artist.normname,)))
        self.assertContains(response, '1 artist')

        self.assertQuerysetEqual(response.context['album_results'].data, [repr(album)])
        self.assertContains(response, 'Albums')
        self.assertContains(response, '%s<' % (album))
        self.assertContains(response, reverse('exordium:album', args=(album.pk,)))
        self.assertContains(response, reverse('exordium:artist', args=(album.artist.normname,)))
        self.assertContains(response, '1 album')

        self.assertQuerysetEqual(response.context['song_results'].data, [repr(song)])
        self.assertContains(response, 'Songs')
        self.assertContains(response, '%s<' % (song.title))
        self.assertContains(response, reverse('exordium:album', args=(song.album.pk,)))
        self.assertContains(response, reverse('exordium:artist', args=(song.artist.normname,)))
        self.assertContains(response, '1 song')

    def run_normalization_test(self, query):
        """
        Base function to use for queries which make use of our normalization
        functions.  Sets up a track with various characters and then runs the
        specified query against it, hoping to find a match.

        Don't ask me where I got that name from.
        """
        self.add_mp3(artist='Artist Æthër & Stràuß', title='Title Æthër & Stràuß',
            album='Album Æthër & Stràuß', filename='song1.mp3')
        self.run_add()

        song = Song.objects.get()
        album = Album.objects.get()
        artist = Artist.objects.get(name='Artist Æthër & Stràuß')

        response = self.client.get(reverse('exordium:search'), {'q': query})
        self.assertEqual(response.status_code, 200)
        self.assertIn('song_results', response.context)
        self.assertIn('album_results', response.context)
        self.assertIn('artist_results', response.context)
        self.assertIn('found_results', response.context)
        self.assertEqual(response.context['found_results'], True)
        self.assertNotContains(response, 'No results found!')

        self.assertQuerysetEqual(response.context['artist_results'].data, [repr(artist)])
        self.assertContains(response, 'Artists')
        self.assertContains(response, '%s<' % (html.escape(artist)))
        self.assertContains(response, reverse('exordium:artist', args=(artist.normname,)))
        self.assertContains(response, '1 artist')

        self.assertQuerysetEqual(response.context['album_results'].data, [repr(album)])
        self.assertContains(response, 'Albums')
        self.assertContains(response, '%s<' % (html.escape(album)))
        self.assertContains(response, reverse('exordium:album', args=(album.pk,)))
        self.assertContains(response, reverse('exordium:artist', args=(album.artist.normname,)))
        self.assertContains(response, '1 album')

        self.assertQuerysetEqual(response.context['song_results'].data, [repr(song)])
        self.assertContains(response, 'Songs')
        self.assertContains(response, '%s<' % (html.escape(song.title)))
        self.assertContains(response, reverse('exordium:album', args=(song.album.pk,)))
        self.assertContains(response, reverse('exordium:artist', args=(song.artist.normname,)))
        self.assertContains(response, '1 song')

    def test_normalized_full(self):
        """
        Test a search against normalized data using the original strings.
        """
        self.run_normalization_test('Æthër & Stràuß')

    def test_normalized_plain(self):
        """
        Test a search against normalized data using plain ascii
        """
        self.run_normalization_test('aether and strauss')

    def test_normalized_mixed(self):
        """
        Test a search against normalized data using a mixed query
        """
        self.run_normalization_test('aether & Stràuß')

    def test_classical_album(self):
        """
        Search for a classical album by its title - just to make sure that
        we're displaying all the relevant artists in the artist column.
        """
        self.add_mp3(artist='Main Artist', title='Title 1',
            group='Group', conductor='Conductor', composer='Composer',
            album='Main Album', filename='song1.mp3')
        self.run_add()

        album = Album.objects.get()
        artists = [
            Artist.objects.get(name='Main Artist'),
            Artist.objects.get(name='Group'),
            Artist.objects.get(name='Conductor'),
            Artist.objects.get(name='Composer'),
        ]

        response = self.client.get(reverse('exordium:search'), {'q': 'main album'})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('song_results', response.context)
        self.assertIn('album_results', response.context)
        self.assertNotIn('artist_results', response.context)
        self.assertIn('found_results', response.context)
        self.assertEqual(response.context['found_results'], True)
        self.assertNotContains(response, 'No results found!')

        self.assertQuerysetEqual(response.context['album_results'].data, [repr(album)])
        self.assertContains(response, 'Albums')
        self.assertContains(response, '%s<' % (album))
        self.assertContains(response, reverse('exordium:album', args=(album.pk,)))
        for artist in artists:
            self.assertContains(response, reverse('exordium:artist', args=(artist.normname,)))
            self.assertContains(response, str(artist))
        self.assertContains(response, '1 album')

    def test_classical_song(self):
        """
        Search for a classical song by its title - just to make sure that
        we're displaying all the relevant artists in the artist column.
        """
        self.add_mp3(artist='Main Artist', title='Title 1',
            group='Group', conductor='Conductor', composer='Composer',
            album='Main Album', filename='song1.mp3')
        self.run_add()

        song = Song.objects.get()
        artists = [
            Artist.objects.get(name='Main Artist'),
            Artist.objects.get(name='Group'),
            Artist.objects.get(name='Conductor'),
            Artist.objects.get(name='Composer'),
        ]

        response = self.client.get(reverse('exordium:search'), {'q': 'title'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('song_results', response.context)
        self.assertNotIn('album_results', response.context)
        self.assertNotIn('artist_results', response.context)
        self.assertIn('found_results', response.context)
        self.assertEqual(response.context['found_results'], True)
        self.assertNotContains(response, 'No results found!')

        self.assertQuerysetEqual(response.context['song_results'].data, [repr(song)])
        self.assertContains(response, 'Songs')
        self.assertContains(response, '%s<' % (song.title))
        self.assertContains(response, reverse('exordium:album', args=(song.album.pk,)))
        for artist in artists:
            self.assertContains(response, reverse('exordium:artist', args=(artist.normname,)))
            self.assertContains(response, str(artist))
        self.assertContains(response, '1 song')

    def test_pagination_artist(self):
        """
        Test pagination on our artist results.  Will show a total of 25 artists.
        Will fake our data by inserting directly into the DB, to save on testing
        time.
        """
        artists = {}
        for num in range(35):
            artists[num] = Artist.objects.create(
                name='Artist %02d' % (num+1),
                normname='artist %02d' % (num+1),
            )

        # Page 1
        response = self.client.get(reverse('exordium:search'), {'q': 'artist'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '25 of 35 artists')
        self.assertContains(response, 'artist-page=2')
        self.assertEqual(len(response.context['artist_results'].data), 35)
        for num in range(25):
            self.assertContains(response, '%s<' % (artists[num]))
            self.assertContains(response, reverse('exordium:artist', args=(artists[num].normname,)))
        for num in range(25, 35):
            self.assertNotContains(response, '%s<' % (artists[num]))
            self.assertNotContains(response, reverse('exordium:artist', args=(artists[num].normname,)))

        # Page 2
        response = self.client.get(reverse('exordium:search'), {'q': 'artist', 'artist-page': 2})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '10 of 35 artists')
        self.assertContains(response, 'artist-page=1')
        self.assertEqual(len(response.context['artist_results'].data), 35)
        for num in range(25):
            self.assertNotContains(response, '%s<' % (artists[num]))
            self.assertNotContains(response, reverse('exordium:artist', args=(artists[num].normname,)))
        for num in range(25, 35):
            self.assertContains(response, '%s<' % (artists[num]))
            self.assertContains(response, reverse('exordium:artist', args=(artists[num].normname,)))

    def test_pagination_album(self):
        """
        Test pagination on our album results.  Will show a total of 25 albums.
        Will fake our data by inserting directly into the DB, to save on testing
        time.
        """
        artist = Artist.objects.create(name='Artist', normname='artist')
        albums = {}
        for num in range(35):
            albums[num] = Album.objects.create(
                name='Album %02d' % (num+1),
                normname='album %02d' % (num+1),
                artist=artist,
            )
            Song.objects.create(
                artist=artist,
                album=albums[num],
                title='Title %03d' % (num+1),
                year=0,
                tracknum=0,
                normtitle='title %03d' % (num+1),
                raw_artist='artist',
                filetype=Song.MP3,
                bitrate=128000,
                mode=Song.CBR,
                size=123000,
                length=90,
                sha256sum='0cf31fc7d968ec16c69758f9b0ebb2355471d5694a151b40e5e4f8641b061092',
            )

        # Page 1
        response = self.client.get(reverse('exordium:search'), {'q': 'album'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '25 of 35 albums')
        self.assertContains(response, 'album-page=2')
        self.assertEqual(len(response.context['album_results'].data), 35)
        self.assertContains(response, reverse('exordium:artist', args=(artist.normname,)))
        for num in range(25):
            self.assertContains(response, '%s<' % (albums[num]))
            self.assertContains(response, reverse('exordium:album', args=(albums[num].pk,)))
        for num in range(25, 35):
            self.assertNotContains(response, '%s<' % (albums[num]))
            self.assertNotContains(response, reverse('exordium:album', args=(albums[num].pk,)))

        # Page 2
        response = self.client.get(reverse('exordium:search'), {'q': 'album', 'album-page': 2})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '10 of 35 albums')
        self.assertContains(response, 'album-page=1')
        self.assertEqual(len(response.context['album_results'].data), 35)
        self.assertContains(response, reverse('exordium:artist', args=(artist.normname,)))
        for num in range(25):
            self.assertNotContains(response, '%s<' % (albums[num]))
            self.assertNotContains(response, reverse('exordium:album', args=(albums[num].pk,)))
        for num in range(25, 35):
            self.assertContains(response, '%s<' % (albums[num]))
            self.assertContains(response, reverse('exordium:album', args=(albums[num].pk,)))

    def test_pagination_song(self):
        """
        Test pagination on our song results.  Will show a total of 25 songs.
        Will fake our data by inserting directly into the DB, to save on testing
        time.
        """
        artist = Artist.objects.create(name='Artist', normname='artist')
        album = Album.objects.create(name='Album', normname='album', artist=artist)
        songs = {}
        for num in range(35):
            songs[num] = Song.objects.create(
                artist=artist,
                album=album,
                title='Title %03d' % (num+1),
                year=0,
                tracknum=0,
                normtitle='title %03d' % (num+1),
                raw_artist='artist',
                filetype=Song.MP3,
                bitrate=128000,
                mode=Song.CBR,
                size=123000,
                length=90,
                sha256sum='0cf31fc7d968ec16c69758f9b0ebb2355471d5694a151b40e5e4f8641b061092',
            )

        # Page 1
        response = self.client.get(reverse('exordium:search'), {'q': 'title'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '25 of 35 songs')
        self.assertContains(response, 'song-page=2')
        self.assertEqual(len(response.context['song_results'].data), 35)
        self.assertContains(response, reverse('exordium:artist', args=(artist.normname,)))
        self.assertContains(response, reverse('exordium:album', args=(album.pk,)))
        for num in range(25):
            self.assertContains(response, '%s<' % (songs[num].title))
        for num in range(25, 35):
            self.assertNotContains(response, '%s<' % (songs[num].title))

        # Page 2
        response = self.client.get(reverse('exordium:search'), {'q': 'title', 'song-page': 2})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '10 of 35 songs')
        self.assertContains(response, 'song-page=1')
        self.assertEqual(len(response.context['song_results'].data), 35)
        self.assertContains(response, reverse('exordium:artist', args=(artist.normname,)))
        self.assertContains(response, reverse('exordium:album', args=(album.pk,)))
        for num in range(25):
            self.assertNotContains(response, '%s<' % (songs[num].title))
        for num in range(25, 35):
            self.assertContains(response, '%s<' % (songs[num].title))

    def test_sorting_artist(self):
        """
        Test at least one case of artist sorting.
        """
        self.add_mp3(artist='Artist 1', title='Title 1',
            album='Album', year=2016, filename='song1.mp3')
        self.add_mp3(artist='Artist 2', title='Title 2',
            album='Album', year=2006, filename='song2.mp3')
        self.add_mp3(artist='Artist 3', title='Title 3',
            album='Album', year=1996, filename='song3.mp3')
        self.run_add()
        self.assertEqual(Artist.objects.count(), 4)

        artists = [
            Artist.objects.get(name='Artist 1'),
            Artist.objects.get(name='Artist 2'),
            Artist.objects.get(name='Artist 3'),
        ]

        response = self.client.get(reverse('exordium:search'), {'q': 'artist'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['artist_results'].data), 3)
        self.assertQuerysetEqual(response.context['artist_results'].data, [repr(ar) for ar in artists])
        self.assertContains(response, 'artist-sort=-name')
        self.assertContains(response, '3 artists')

        # test the sorting button
        response = self.client.get(reverse('exordium:search'), {'q': 'artist', 'artist-sort': '-name'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['artist_results'].data), 3)
        self.assertQuerysetEqual(response.context['artist_results'].data, [repr(ar) for ar in reversed(artists)])
        self.assertContains(response, 'artist-sort=name')
        self.assertContains(response, '3 artists')

    def test_sorting_album(self):
        """
        Test at least one case of album sorting.
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album 1', year=2016, filename='song1.mp3')
        self.add_mp3(artist='Artist', title='Title 2',
            album='Album 2', year=2006, filename='song2.mp3')
        self.add_mp3(artist='Artist', title='Title 3',
            album='Album 3', year=1996, filename='song3.mp3')
        self.run_add()
        self.assertEqual(Album.objects.count(), 3)

        albums = [
            Album.objects.get(name='Album 1'),
            Album.objects.get(name='Album 2'),
            Album.objects.get(name='Album 3'),
        ]

        response = self.client.get(reverse('exordium:search'), {'q': 'album'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['album_results'].data), 3)
        self.assertQuerysetEqual(response.context['album_results'].data, [repr(al) for al in albums])
        self.assertContains(response, 'album-sort=year')
        self.assertContains(response, '3 albums')

        # test the sorting button
        response = self.client.get(reverse('exordium:search'), {'q': 'album', 'album-sort': 'year'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['album_results'].data), 3)
        self.assertQuerysetEqual(response.context['album_results'].data, [repr(al) for al in reversed(albums)])
        self.assertContains(response, 'album-sort=-year')
        self.assertContains(response, '3 albums')

    def test_sorting_song(self):
        """
        Test at least one case of song sorting.  Default sorting is by track name
        """
        self.add_mp3(artist='Artist', title='Title 1', tracknum=1,
            album='Album 3', filename='song1.mp3')
        self.add_mp3(artist='Artist', title='Title 2', tracknum=2,
            album='Album 2', filename='song2.mp3')
        self.add_mp3(artist='Artist', title='Title 3', tracknum=3,
            album='Album 1', filename='song3.mp3')
        self.run_add()

        songs = [
            Song.objects.get(filename='song1.mp3'),
            Song.objects.get(filename='song2.mp3'),
            Song.objects.get(filename='song3.mp3'),
        ]

        response = self.client.get(reverse('exordium:search'), {'q': 'title'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['song_results'].data), 3)
        self.assertQuerysetEqual(response.context['song_results'].data, [repr(song) for song in songs])
        self.assertContains(response, 'song-sort=album')
        self.assertContains(response, '3 songs')

        # test the sorting button
        response = self.client.get(reverse('exordium:search'), {'q': 'title', 'song-sort': 'album'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['song_results'].data), 3)
        self.assertQuerysetEqual(response.context['song_results'].data, [repr(song) for song in reversed(songs)])
        self.assertContains(response, 'song-sort=-album')
        self.assertContains(response, '3 songs')

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
        self.assertContains(response, App.prefs['exordium__media_url'])
        self.assertNotContains(response, 'Zipfile Support:</strong> Yes')
        self.assertContains(response, 'Zipfile Support:</strong> No')

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

class LiveAlbumViewTestsAnonymous(ExordiumUserTests):
    """
    Tests of our live album viewing functionality.  They can be either
    hidden or shown based on user preference, so there'll basically just
    be one test in here per view where this preference applies.
    """

    def set_show_live(self, show_live=True):
        """
        Sets our ``show_live`` preference as specified, by submitting our
        user preference form.  (That way we don't need a request object.)
        """
        if show_live:
            post_data = {'show_live': 'yes'}
        else:
            post_data = {}
        self.client.post(reverse('exordium:updateprefs'), post_data)

    def test_index(self):
        """
        Tests our index page display
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='2016.01.01 - Live at City Name', filename='song1.mp3')
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        album = Album.objects.get()
        self.assertEqual(album.live, True)

        # Default is off
        response = self.client.get(reverse('exordium:index'))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['album_list'].data, [])
        self.assertNotContains(response, reverse('exordium:album', args=(album.pk,)))
        self.assertNotContains(response, reverse('exordium:artist', args=(album.artist.normname,)))

        # Now flip it on
        self.set_show_live()
        response = self.client.get(reverse('exordium:index'))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['album_list'].data, [repr(album)])
        self.assertContains(response, reverse('exordium:album', args=(album.pk,)))
        self.assertContains(response, reverse('exordium:artist', args=(album.artist.normname,)))
        self.assertContains(response, '1 album')

    def test_album_browse(self):
        """
        Tests our Browse Album page
        """

        self.add_mp3(artist='Artist', title='Title 1',
            album='2016.01.01 - Live at City Name', filename='song1.mp3')
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        album = Album.objects.get()
        self.assertEqual(album.live, True)

        # Default is off
        response = self.client.get(reverse('exordium:browse_album'))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['table'].data, [])
        self.assertNotContains(response, reverse('exordium:album', args=(album.pk,)))
        self.assertNotContains(response, reverse('exordium:artist', args=(album.artist.normname,)))

        # Now flip it on
        self.set_show_live()
        response = self.client.get(reverse('exordium:browse_album'))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['table'].data, [repr(album)])
        self.assertContains(response, reverse('exordium:album', args=(album.pk,)))
        self.assertContains(response, reverse('exordium:artist', args=(album.artist.normname,)))
        self.assertContains(response, '1 album')

    def test_artist(self):
        """
        Tests our Artist info page
        """

        self.add_mp3(artist='Artist', title='Title 1',
            album='2016.01.01 - Live at City Name', filename='song1.mp3')
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        album = Album.objects.get()
        self.assertEqual(album.live, True)

        self.assertEqual(Artist.objects.count(), 2)
        artist = Artist.objects.get(name='Artist')

        self.assertEqual(Song.objects.count(), 1)
        song = Song.objects.get()

        # Default is off
        response = self.client.get(reverse('exordium:artist', args=(artist.normname,)))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['have_songs'], True)
        self.assertQuerysetEqual(response.context['albums'].data, [])
        self.assertQuerysetEqual(response.context['songs'].data, [])
        self.assertNotContains(response, reverse('exordium:album', args=(album.pk,)))
        self.assertNotContains(response, '"%s"' % (reverse('exordium:artist', args=(album.artist.normname,))))

        # Now flip it on
        self.set_show_live()
        response = self.client.get(reverse('exordium:artist', args=(artist.normname,)))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['have_songs'], True)
        self.assertQuerysetEqual(response.context['albums'].data, [repr(album)])
        self.assertQuerysetEqual(response.context['songs'].data, [repr(song)])
        self.assertContains(response, reverse('exordium:album', args=(album.pk,)))
        self.assertContains(response, '"%s"' % (reverse('exordium:artist', args=(album.artist.normname,))))
        self.assertContains(response, '1 album')
        self.assertContains(response, '1 song')

    def test_search_album(self):
        """
        Tests our search page, searching for albums
        """

        self.add_mp3(artist='Artist', title='Title 1',
            album='2016.01.01 - Live at City Name', filename='song1.mp3')
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        album = Album.objects.get()
        self.assertEqual(album.live, True)

        self.assertEqual(Artist.objects.count(), 2)
        artist = Artist.objects.get(name='Artist')

        self.assertEqual(Song.objects.count(), 1)
        song = Song.objects.get()

        # Default is off
        response = self.client.get(reverse('exordium:search'), {'q': 'city name'})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('length_error', response.context)
        self.assertNotIn('song_results', response.context)
        self.assertNotIn('album_results', response.context)
        self.assertNotIn('artist_results', response.context)
        self.assertIn('found_results', response.context)
        self.assertEqual(response.context['found_results'], False)
        self.assertContains(response, 'No results found!')
        self.assertNotContains(response, reverse('exordium:album', args=(album.pk,)))
        self.assertNotContains(response, reverse('exordium:artist', args=(artist.normname,)))

        # Now flip it on
        self.set_show_live()
        response = self.client.get(reverse('exordium:search'), {'q': 'city name'})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('song_results', response.context)
        self.assertIn('album_results', response.context)
        self.assertNotIn('artist_results', response.context)
        self.assertIn('found_results', response.context)
        self.assertEqual(response.context['found_results'], True)
        self.assertNotContains(response, 'No results found!')

        self.assertQuerysetEqual(response.context['album_results'].data, [repr(album)])
        self.assertContains(response, 'Albums')
        self.assertContains(response, '%s<' % (album))
        self.assertContains(response, reverse('exordium:album', args=(album.pk,)))
        self.assertContains(response, reverse('exordium:artist', args=(album.artist.normname,)))
        self.assertContains(response, '1 album')

    def test_search_song(self):
        """
        Tests our search page, searching for songs
        """

        self.add_mp3(artist='Artist', title='Title 1',
            album='2016.01.01 - Live at City Name', filename='song1.mp3')
        self.run_add()

        self.assertEqual(Album.objects.count(), 1)
        album = Album.objects.get()
        self.assertEqual(album.live, True)

        self.assertEqual(Artist.objects.count(), 2)
        artist = Artist.objects.get(name='Artist')

        self.assertEqual(Song.objects.count(), 1)
        song = Song.objects.get()

        # Default is off
        response = self.client.get(reverse('exordium:search'), {'q': 'title'})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('length_error', response.context)
        self.assertNotIn('song_results', response.context)
        self.assertNotIn('album_results', response.context)
        self.assertNotIn('artist_results', response.context)
        self.assertIn('found_results', response.context)
        self.assertEqual(response.context['found_results'], False)
        self.assertContains(response, 'No results found!')
        self.assertNotContains(response, reverse('exordium:album', args=(album.pk,)))
        self.assertNotContains(response, reverse('exordium:artist', args=(artist.normname,)))
        self.assertNotContains(response, song.title)

        # Now flip it on
        self.set_show_live()
        response = self.client.get(reverse('exordium:search'), {'q': 'title'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('song_results', response.context)
        self.assertNotIn('album_results', response.context)
        self.assertNotIn('artist_results', response.context)
        self.assertIn('found_results', response.context)
        self.assertEqual(response.context['found_results'], True)
        self.assertNotContains(response, 'No results found!')

        self.assertQuerysetEqual(response.context['song_results'].data, [repr(song)])
        self.assertContains(response, 'Songs')
        self.assertContains(response, '%s<' % (song.title))
        self.assertContains(response, reverse('exordium:album', args=(song.album.pk,)))
        self.assertContains(response, reverse('exordium:artist', args=(song.artist.normname,)))
        self.assertContains(response, '1 song')

class LiveAlbumViewTestsUser(LiveAlbumViewTestsAnonymous):
    """
    Some nonsense along the lines of BasicUpdateAsAddTests.  Basically,
    all of our tests in LiveAlbumViewTestsAnonymous should work just
    as well if the user is logged in as when the user is anonymous.  So,
    we have a custom setUp() function here which will do that prior to
    every test.
    """

    def setUp(self):
        super(LiveAlbumViewTestsUser, self).setUp()
        self.login()

    def tearDown(self):
        """
        Ensure that we revert back to the default of not showing live
        albums inbetween tests - this won't automatically happen for
        logged-in users because changes to the user database persists.
        """
        super(LiveAlbumViewTestsUser, self).tearDown()
        self.set_show_live(False)

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
