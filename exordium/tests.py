from django.test import TestCase
from django.urls import reverse

from dynamic_preferences.registries import global_preferences_registry

import io
import os
import shutil
import pathlib

from mutagen.id3 import ID3, TIT2, TALB, TPE1, TDRC, TRCK, TDRL, TPE2, TPE3, TCOM
from mutagen.oggvorbis import OggVorbis
from PIL import Image

from .models import Artist, Album, Song, App, AlbumArt

# These two imports are just here in case we want to examine SQL while running tests.
# If so, set "settings.DEBUG = True" in the test and then use connection.queries
from django.conf import settings
from django.db import connection

# Create your tests here.

# TODO: At the moment all this really does is test the models themselves,
# and more specifically the add() and update() logic.  It does not
# currently test anything relating to views.

class ExordiumTests(TestCase):
    """
    Custom TestCase class for Exordium.  Includes our ``initial_data``
    fixture and sets up a pretend library under ``testdata``.  Uses
    the sample mp3 files in ``testdata`` as the basis for all the files
    that we'll be testing with.
    """

    fixtures = ['initial_data.json']

    testdata_path = os.path.join(os.path.dirname(__file__), 'testdata')
    library_path = os.path.join(testdata_path, 'library')

    prefs = None

    def setUp(self):
        """
        Run automatically at the start of any test.  Ensure that there's no
        library hanging around in our testdata dir, ensure that our base
        testing files exist, and then set up the base library path.
        """
        for filename in ['silence-abr.mp3', 'silence-cbr.mp3', 'silence-vbr.mp3', 'invalid-tags.mp3',
                'silence.ogg', 'cover_400.jpg', 'cover_400.gif', 'cover_400.png', 'cover_100.jpg']:
            if not os.path.exists(os.path.join(self.testdata_path, filename)):
                raise Exception('Required testing file "%s" does not exist!' % (filename))
        if os.path.exists(self.library_path):
            raise Exception('Test data path "%s" cannot exist before running tests' %
                (self.library_path))
        os.mkdir(self.library_path)
        self.prefs = global_preferences_registry.manager()
        self.prefs['exordium__base_path'] = self.library_path

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

        if len(filename) < 3 or '..' in filename or filename[0] == '/':
            raise Exception('Given filename "%s" is invalid' % (filename))

        full_filename = os.path.join(self.library_path, filename)
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

        if len(filename) < 3 or '..' in filename or filename[0] == '/':
            raise Exception('Given filename "%s" is invalid' % (filename))

        full_filename = os.path.join(self.library_path, filename)
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

    def delete_file(self, filename):
        """
        Deletes the given file from our fake library
        """
        if len(filename) < 3 or '..' in filename or filename[0] == '/':
            raise Exception('Given filename "%s" is invalid' % (filename))

        full_filename = os.path.join(self.library_path, filename)
        self.assertEqual(os.path.exists(full_filename), True)

        os.unlink(full_filename)

        self.assertEqual(os.path.exists(full_filename), False)

    def move_file(self, filename, destination):
        """
        Deletes the given file from our fake library
        """
        if len(filename) < 3 or '..' in filename or filename[0] == '/':
            raise Exception('Given filename "%s" is invalid' % (filename))

        full_filename = os.path.join(self.library_path, filename)
        self.assertEqual(os.path.exists(full_filename), True)

        if destination != '' and ('..' in destination or destination[0] == '/'):
            raise Exception('Given destination "%s" is invalid' % (destination))
        full_destination = os.path.join(self.library_path, destination)

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

        if len(filename) < 3 or '..' in filename or filename[0] == '/':
            raise Exception('Given filename "%s" is invalid' % (filename))

        full_filename = os.path.join(self.library_path, filename)

        starting_mtime = int(os.stat(full_filename).st_mtime)

        pathlib.Path(full_filename).touch(exist_ok=True)

        stat_result = os.stat(full_filename)
        ending_mtime = int(stat_result.st_mtime)
        if starting_mtime == ending_mtime:
            new_mtime = ending_mtime + 1
            os.utime(full_filename, times=(stat_result.st_atime, new_mtime))

    def get_file_contents(self, filename):
        """
        Retrieves file contents from the named file in the library
        """

        if len(filename) < 3 or '..' in filename or filename[0] == '/':
            raise Exception('Given filename "%s" is invalid' % (filename))

        full_filename = os.path.join(self.library_path, filename)

        with open(full_filename, 'rb') as df:
            return df.read()

    def add_art(self, path='', filename='cover.jpg', basefile='cover_400.jpg'):
        """
        Adds a new cover image to our library in the specified dir.
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

    def assertNoErrors(self, appresults):
        """
        Given a list of tuples (as returned from ``App.add()`` or ``App.update()``),
        ensure that none of the lines have status App.STATUS_ERROR
        """
        for (status, line) in appresults:
            self.assertNotEqual(status, App.STATUS_ERROR)
        return appresults

    def assertErrors(self, appresults, errors_min=1):
        """
        Given a list of tuples (as returned from ``App.add()`` or ``App.update()``),
        ensure that we have at least ``errors_min`` with a status of App.STATUS_ERROR
        """
        error_count = 0
        for (status, line) in appresults:
            if status == App.STATUS_ERROR:
                error_count += 1
        self.assertTrue(error_count >= errors_min)
        return appresults

    def run_add(self):
        """
        Runs an ``add`` operation on our library, and checks for errors.
        """
        return self.assertNoErrors(list(App.add()))

    def run_add_errors(self, errors_min=1):
        """
        Runs an ``add`` operation on our library, and expect to see at least
        one error.
        """
        return self.assertErrors(list(App.add()), errors_min)

    def run_update(self):
        """
        Runs an ``update`` operation on our library, and checks for errors.
        """
        return self.assertNoErrors(list(App.update()))

    def run_update_errors(self, errors_min=1):
        """
        Runs an ``add`` operation on our library, and expect to see at least
        one error.
        """
        return self.assertErrors(list(App.update()), errors_min)

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
        self.assertEquals(song.mode, mode.upper())

    def mp3_year_test(self, year, yeartag):
        """
        Tests a simple addition of an mp3 to the database, using
        the specified year tag.
        """
        self.add_mp3(artist='Artist', title='Title', year=year, yeartag=yeartag)
        self.run_add()
        song = Song.objects.get()
        self.assertEquals(song.year, year)

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
        self.run_add_errors()
        self.assertEqual(Song.objects.count(), 0)
        self.assertEqual(Artist.objects.count(), 1)
        self.assertEqual(Album.objects.count(), 0)

    def test_add_mp3_no_title_tag(self):
        """
        Test adding an mp3 file which has no title tag specified
        """
        self.add_mp3(artist='Artist')
        self.run_add_errors()
        self.assertEqual(Song.objects.count(), 0)
        self.assertEqual(Artist.objects.count(), 1)
        self.assertEqual(Album.objects.count(), 0)

    def test_add_mp3_no_artist_tag(self):
        """
        Test adding an mp3 file which has no title tag specified
        """
        self.add_mp3(title='Title', composer='Composer', album='Album')
        self.run_add_errors()
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
        artist = Artist.objects.get(name='artist Name')
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
        artist = Artist.objects.get(name='artist Name')
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
        artist = Artist.objects.get(name='artist Name')
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
        artist = Artist.objects.get(name='artist Name')
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
        artist = Artist.objects.get(name='artist One')
        self.assertEqual(artist.name.lower(), 'artist one')
        artist = Artist.objects.get(name='artist Two')
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
        artist = Artist.objects.get(name='artist One')
        self.assertEqual(artist.name.lower(), 'artist one')
        artist = Artist.objects.get(name='artist Two')
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
        artist = Artist.objects.get(name='artist One')
        self.assertEqual(artist.name.lower(), 'artist one')
        artist = Artist.objects.get(name='artist Two')
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
        album = Album.objects.get(name='album Name')
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
        album = Album.objects.get(name='album Name')
        self.assertEqual(album.name.lower(), 'album name')
        self.assertEqual(album.song_set.count(), 2)
        artist = Artist.objects.get(name='artist Name')
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

    def run_add_errors(self, errors_min=1):
        """
        Runs an ``update`` operation on our library while pretending to be
        ``add``, and ensures that there's at least one error
        """
        return self.assertErrors(list(App.update()), errors_min)

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
        artist = Artist.objects.get(name='Artist Name')
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
        artist = Artist.objects.get(name='Group')
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
        artist = Artist.objects.get(name='Conductor')
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
        artist = Artist.objects.get(name='Composer')
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
        artist = Artist.objects.get(name='Artist Name')
        self.assertEqual(artist.pk, artist_pk)
        self.assertEqual(artist.name, 'Artist Name')
        album = Album.objects.get(name='Album Name')
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
        artist = Artist.objects.get(name='umlaut')
        artist_pk = artist.pk
        self.assertEqual(artist.name, 'Umläut')
        
        # Update
        self.update_mp3('song2.mp3', artist='Umlaut')
        self.run_update()

        # Actual checks
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        artist = Artist.objects.get(name='umlaut')
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
        album = Album.objects.get(name='album')
        album_pk = album.pk
        self.assertEqual(album.name, 'Albüm')
        
        # Update
        self.update_mp3('song2.mp3', album='Album')
        self.run_update()

        # Actual checks
        self.assertEqual(Song.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 1)
        album = Album.objects.get(name='album')
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

class AlbumArtTests(ExordiumTests):
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
        self.run_add_errors()

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
        self.assertEqual(art.image, data.read())

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
        self.assertEqual(art.image, data.read())

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

