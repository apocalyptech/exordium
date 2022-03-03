from django.test import TestCase, override_settings
from django.utils import timezone

from django.contrib.auth.models import User

from dynamic_preferences.registries import global_preferences_registry

import os
import shutil
import pathlib
import datetime
import tempfile

from mutagen.id3 import ID3, TIT2, TALB, TPE1, TDRC, TRCK, TDRL, TPE2, TPE3, TCOM
from mutagen.oggvorbis import OggVorbis
from mutagen.oggopus import OggOpus
from mutagen.mp4 import MP4

from exordium.models import Artist, Album, Song, App, AlbumArt

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

    testdata_path = os.path.join(os.path.dirname(__file__), '..', 'testdata')
    library_path = None

    prefs = None

    def setUp(self):
        """
        Run automatically at the start of any test.  Ensure that there's no
        library hanging around in our testdata dir, ensure that our base
        testing files exist, and then set up the base library path.
        """
        for filename in ['silence-abr.mp3', 'silence-cbr.mp3', 'silence-vbr.mp3', 'invalid-tags.mp3',
                'silence.ogg', 'silence.m4a', 'silence.flac', 'silence.opus',
                'cover_400.jpg', 'cover_400.gif', 'cover_400.png', 'cover_400.tif', 'cover_100.jpg']:
            if not os.path.exists(os.path.join(self.testdata_path, filename)):  # pragma: no cover
                raise Exception('Required testing file "%s" does not exist!' % (filename))
        self.library_path = tempfile.mkdtemp()
        self.prefs = global_preferences_registry.manager()
        self.prefs['exordium__base_path'] = self.library_path
        self.prefs['exordium__media_url_html5'] = 'http://testserver-media/html5music'
        self.prefs['exordium__media_url_m3u'] = 'http://testserver-media/m3umusic'

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

    def add_opus(self, path='', filename='file.opus', artist='', album='',
            title='', tracknum=None, year=None, group='', conductor='', composer='',
            basefile='silence.opus', apply_tags=True):
        """
        Adds a new ogg opus file with the given parameters to our library.

        Pass in ``False`` for ``apply_tags`` to only use whatever tags happen to
        be present in the source basefile.
        """

        full_filename = self.add_file(basefile, filename, path=path)

        # Finish here if we've been told to.
        if not apply_tags:
            return

        # Apply the tags as specified
        tags = OggOpus(full_filename)
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

    def update_opus(self, filename, artist=None, album=None,
            title=None, tracknum=None, year=None,
            group=None, conductor=None, composer=None):
        """
        Updates an on-disk ogg opus file with the given tag data.  Any passed-in
        variable set to None will be ignored.

        If group/conductor/composer is a blank string, those fields will
        be completely removed from the file.  Any of the other fields set
        to blank will leave the tag in place.

        Will ensure that the file's mtime is updated.
        """

        full_filename = self.check_library_filename(filename)
        self.assertEqual(os.path.exists(full_filename), True)

        starting_mtime = int(os.stat(full_filename).st_mtime)

        tags = OggOpus(full_filename)

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

    def rename_file(self, filename, new_filename):
        """
        Renames the given file in our fake library to a new filename (in
        the same directory)
        """
        full_filename = self.check_library_filename(filename)
        self.assertEqual(os.path.exists(full_filename), True)
        full_new_filename = self.check_library_filename(new_filename)
        shutil.move(full_filename, full_new_filename)
        self.assertEqual(os.path.exists(full_new_filename), True)

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

