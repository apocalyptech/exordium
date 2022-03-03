from .base import ExordiumTests

from exordium.models import Artist, Album, Song, App, AlbumArt

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

    def test_basic_update_opus(self):
        """
        Test a simple track update to the title, on an ogg opus file.  (This
        is really more testing our opus update function than it is Exordium,
        at this point.)
        """
        self.add_opus(filename='song.opus', artist='Artist', title='Title')
        self.run_add()

        # Quick verification
        song = Song.objects.get()
        self.assertEqual(song.artist.name, 'Artist')
        self.assertEqual(song.title, 'Title')

        # Now make some changes.
        self.update_opus(filename='song.opus', title='New Title Æ')
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

    def test_basic_moved_file_year_update(self):
        """
        Test a track update where a file's Year gets updated, but
        also the file has been renamed.  The album year should
        still get updated.
        """
        self.add_mp3(filename='song.mp3', artist='Artist', title='Title',
            album = 'Album', year=2006)
        self.run_add()

        # Quick verification
        self.assertEqual(Song.objects.count(), 1)
        song = Song.objects.get()
        song_pk = song.pk
        self.assertEqual(song.year, 2006)

        self.assertEqual(Album.objects.count(), 1)
        album = Album.objects.get()
        album_pk = album.pk
        self.assertEqual(album.year, 2006)

        # Now make some changes
        self.update_mp3(filename='song.mp3', year=2016)
        self.rename_file('song.mp3', 'song2.mp3')
        self.run_update()

        # Now the real verification
        self.assertEqual(Song.objects.count(), 1)
        song = Song.objects.get()
        self.assertEqual(song.year, 2016)
        self.assertNotEqual(song.pk, song_pk)

        self.assertEqual(Album.objects.count(), 1)
        album = Album.objects.get()
        self.assertEqual(album.pk, album_pk)
        self.assertEqual(album.year, 2016)

    def test_basic_moved_file_year_update_two_files(self):
        """
        Test a track update where a file's Year gets updated, but
        also one file has been renamed.  The album year should
        still get updated.
        """
        self.add_mp3(filename='song.mp3', artist='Artist', title='Title',
            album = 'Album', year=2006)
        self.add_mp3(filename='song2.mp3', artist='Artist', title='Title',
            album = 'Album', year=2006)
        self.run_add()

        # Quick verification
        self.assertEqual(Song.objects.count(), 2)
        song = Song.objects.get(filename='song.mp3')
        song_pk = song.pk
        self.assertEqual(song.year, 2006)
        song = Song.objects.get(filename='song2.mp3')
        song2_pk = song.pk
        self.assertEqual(song.year, 2006)

        self.assertEqual(Album.objects.count(), 1)
        album = Album.objects.get()
        album_pk = album.pk
        self.assertEqual(album.year, 2006)

        # Now make some changes
        self.update_mp3(filename='song.mp3', year=2016)
        self.update_mp3(filename='song2.mp3', year=2016)
        self.rename_file('song2.mp3', 'song3.mp3')
        self.run_update()

        # Now the real verification
        self.assertEqual(Song.objects.count(), 2)
        song = Song.objects.get(filename='song.mp3')
        self.assertEqual(song.year, 2016)
        self.assertEqual(song.pk, song_pk)
        song = Song.objects.get(filename='song3.mp3')
        self.assertEqual(song.year, 2016)
        self.assertNotEqual(song.pk, song2_pk)

        self.assertEqual(Album.objects.count(), 1)
        album = Album.objects.get()
        self.assertEqual(album.pk, album_pk)
        self.assertEqual(album.year, 2016)

    def test_basic_moved_file_albumname_update(self):
        """
        Test a track update where a file's album name gets updated,
        but also the file has been renamed.  The album name should
        still get updated.
        """
        self.add_mp3(filename='song.mp3', artist='Artist', title='Title',
            album = 'Album', year=2006)
        self.run_add()

        # Quick verification
        self.assertEqual(Song.objects.count(), 1)
        song = Song.objects.get()
        song_pk = song.pk
        self.assertEqual(song.album.name, 'Album')

        self.assertEqual(Album.objects.count(), 1)
        album = Album.objects.get()
        album_pk = album.pk
        self.assertEqual(album.name, 'Album')

        # Now make some changes
        self.update_mp3(filename='song.mp3', album='New Album')
        self.rename_file('song.mp3', 'song2.mp3')
        self.run_update()

        # Now the real verification
        self.assertEqual(Song.objects.count(), 1)
        song = Song.objects.get()
        self.assertEqual(song.album.name, 'New Album')
        self.assertNotEqual(song.pk, song_pk)

        self.assertEqual(Album.objects.count(), 1)
        album = Album.objects.get()
        self.assertNotEqual(album.pk, album_pk)
        self.assertEqual(album.name, 'New Album')

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

