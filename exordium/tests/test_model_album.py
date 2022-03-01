from django.test import TestCase

from exordium.models import Artist, Album, Song, App, AlbumArt

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

    def test_get_songs_ordered(self):
        """
        Test to make sure that songs come back ordered by track number
        """
        ar = Artist.objects.create(name='Artist', normname='artist')
        al = Album.objects.create(artist = ar, name = 'Album', normname = 'album')
        s1 = Song.objects.create(artist=ar,
                album=al,
                title='Title 1',
                tracknum=2,
                year=2020,
                bitrate=128000,
                mode=Song.CBR,
                size=123000,
                length=90,
                sha256sum='0cf31fc7d968ec16c69758f9b0ebb2355471d5694a151b40e5e4f8641b061092',
                )
        s2 = Song.objects.create(artist=ar,
                album=al,
                title='Title 2',
                tracknum=1,
                year=2020,
                bitrate=128000,
                mode=Song.CBR,
                size=123000,
                length=90,
                sha256sum='0cf31fc7d968ec16c69758f9b0ebb2355471d5694a151b40e5e4f8641b061092',
                )

        self.assertEqual(list(al.get_songs_ordered()), [s2, s1])

    def test_get_jquery_streaming_songs_ordered(self):
        """
        Test to make sure that streamable songs come back ordered by track number
        """
        ar = Artist.objects.create(name='Artist', normname='artist')
        al = Album.objects.create(artist = ar, name = 'Album', normname = 'album')
        s1 = Song.objects.create(artist=ar,
                album=al,
                title='Title 1',
                tracknum=2,
                year=2020,
                bitrate=128000,
                mode=Song.CBR,
                size=123000,
                length=90,
                sha256sum='0cf31fc7d968ec16c69758f9b0ebb2355471d5694a151b40e5e4f8641b061092',
                )
        s2 = Song.objects.create(artist=ar,
                album=al,
                title='Title 2',
                tracknum=1,
                year=2020,
                bitrate=128000,
                mode=Song.CBR,
                size=123000,
                length=90,
                sha256sum='0cf31fc7d968ec16c69758f9b0ebb2355471d5694a151b40e5e4f8641b061092',
                )

        self.assertEqual(list(al.get_songs_jplayer_streamable_ordered()), [s2, s1])

    def test_get_jquery_streaming_songs_ordered_one_missing(self):
        """
        Test to make sure that streamable songs come back ordered by track number,
        when one of the songs isn't actually streamable.
        """
        ar = Artist.objects.create(name='Artist', normname='artist')
        al = Album.objects.create(artist = ar, name = 'Album', normname = 'album')
        s1 = Song.objects.create(artist=ar,
                album=al,
                title='Title 1',
                tracknum=3,
                year=2020,
                bitrate=128000,
                mode=Song.CBR,
                size=123000,
                length=90,
                sha256sum='0cf31fc7d968ec16c69758f9b0ebb2355471d5694a151b40e5e4f8641b061092',
                )
        s2 = Song.objects.create(artist=ar,
                album=al,
                title='Title 2',
                tracknum=2,
                year=2020,
                bitrate=128000,
                mode=Song.CBR,
                size=123000,
                length=90,
                sha256sum='0cf31fc7d968ec16c69758f9b0ebb2355471d5694a151b40e5e4f8641b061092',
                filetype=Song.OPUS,
                )
        s3 = Song.objects.create(artist=ar,
                album=al,
                title='Title 3',
                tracknum=1,
                year=2020,
                bitrate=128000,
                mode=Song.CBR,
                size=123000,
                length=90,
                sha256sum='0cf31fc7d968ec16c69758f9b0ebb2355471d5694a151b40e5e4f8641b061092',
                )

        self.assertEqual(list(al.get_songs_jplayer_streamable_ordered()), [s3, s1])

