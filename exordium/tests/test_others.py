from .base import ExordiumTests

import os

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

    def test_add_opus_without_tags(self):
        """
        Add an ogg opus file without tags
        """
        self.add_opus(filename='song.opus', apply_tags=False)

    def test_update_opus_with_previously_empty_tags(self):
        """
        Update an ogg opus file which previously had no tags.
        """
        self.add_opus(filename='song.opus', apply_tags=False)
        self.update_opus('song.opus',
            artist='Artist',
            album='Album',
            title='Title',
            tracknum=1,
            year=2016,
            group='Group',
            conductor='Conductor',
            composer='Composer')

    def test_update_opus_with_previously_full_tags(self):
        """
        Update an ogg opus file which previously had a full set of tags
        """
        self.add_opus(filename='song.opus',
            artist='Artist',
            album='Album',
            title='Title',
            tracknum=1,
            year=2016,
            group='Group',
            conductor='Conductor',
            composer='Composer')
        self.update_opus('song.opus',
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

