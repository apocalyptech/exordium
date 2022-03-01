from .base import ExordiumTests

from exordium.models import Artist, Album, Song, App, AlbumArt

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

    def test_add_opus_simple_tag_check(self):
        """
        Adds a single fully-tagged track and check that the resulting database
        objects are all populated properly
        """
        self.add_opus(artist='Artist', title='Title', album='Album',
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

    def test_add_classical_simple_tag_check_opus(self):
        """
        Adds a single fully-tagged track and check that the resulting database
        objects are all populated properly
        """
        self.add_opus(artist='Artist', title='Title', album='Album',
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

class BasicAddAsUpdateTests(BasicAddTests):
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

