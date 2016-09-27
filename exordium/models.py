import os
import re
import io
import hashlib
import mutagen
import datetime

from dynamic_preferences.registries import global_preferences_registry

from django.db import models, transaction
from django.db.utils import IntegrityError
from django.utils import timezone
from django.db.models import Q

from PIL import Image

# Create your models here.

# TODO: I actually don't think I like those "on_delete=models.CASCADE"
# parameters on ForeignKeys.  I'm guessing that in all circumstances I'd
# prefer that we error out, rather than silently deleting data we might
# not mean to.  I've squashed a few bugs related to that kind of thing
# already, and more similar bugs might be lurking still.

class SongHelper(object):
    """
    A little class, little more than a glorified dict, which is used
    to store some interim information while adding/updating/cleaning
    tracks.  The class helps in these ways:
    
    1. Helps with associations of "Various" albums
    2. Takes care of "unattached" tracks which aren't in an album
    3. Takes care of stripping the artist prefix
    """

    def __init__(self, artist_full, group, conductor, composer, album, song_obj):

        # Direct vars
        self.song_obj = song_obj
        self.album = album

        # Some inferred info
        (self.artist_prefix, self.artist_name) = Artist.extract_prefix(artist_full)
        self.norm_artist_name = App.norm_name(self.artist_name)

        (self.group_prefix, self.group_name) = Artist.extract_prefix(group)
        self.norm_group_name = App.norm_name(self.group_name)

        (self.conductor_prefix, self.conductor_name) = Artist.extract_prefix(conductor)
        self.norm_conductor_name = App.norm_name(self.conductor_name)

        (self.composer_prefix, self.composer_name) = Artist.extract_prefix(composer)
        self.norm_composer_name = App.norm_name(self.composer_name)

        self.base_dir = os.path.dirname(song_obj.filename)

        # Information which may be overwritten later
        self.album_artist = self.artist_name
        self.norm_album_artist = self.norm_artist_name

        # If we have no defined album, make one up!
        # This... might not be the right place to do this?  Still, it's
        # convenient here, so whatever.
        if self.album == '':
            self.album = Album.miscellaneous_format_str % (artist_full)
            self.miscellaneous_album = True
        else:
            self.miscellaneous_album = False

        # Create our normalized album name here, in case we'd started with it
        # blank.
        self.norm_album = App.norm_name(self.album)

        # Also set a "live" boolean.  Will mostly just be used for frontend
        # filtering.
        if App.livere.match(self.album):
            self.live_album = True
        else:
            self.live_album = False

    def set_album_artist(self, artist):
        """
        Sets the album artist for this helper (and also the normalized version
        of the artist)
        """
        self.album_artist = artist
        self.norm_album_artist = App.norm_name(artist)

class Artist(models.Model):

    name = models.CharField(
        max_length=255,
        unique=True,
    )
    name.verbose_name = 'Artist'
    normname = models.CharField(
        max_length=255,
        unique=True,
    )
    prefix = models.CharField(
        max_length=32,
    )
    various = models.BooleanField(default=False)

    def __str__(self):
        """
        Returns a string representation of ourselves
        """
        if self.prefix and self.prefix != '':
            return '%s %s' % (self.prefix, self.name)
        else:
            return self.name

    def save(self, *args, **kwargs):
        """
        Custom handler for save() which populates our normname field
        automatically.
        """
        self.normname = App.norm_name(self.name)
        super(Artist, self).save(*args, **kwargs)

    # TODO: dynamic prefixes via the admin interface?
    # TODO: prefix exceptions ("The The")
    @staticmethod
    def extract_prefix(name):
        """
        Extracts a prefix from the given name, if one exists.  Returns
        a tuple of `(prefix, name)`, where `prefix` may be an empty string.
        """
        if name == '':
            return ('', '')

        match = App.prefixre.match(name)
        if match.group(2):
            return (match.group(2), match.group(3))
        else:
            return ('', name)

class Album(models.Model):

    miscellaneous_format_str = '(Non-Album Tracks: %s)'

    artist = models.ForeignKey(Artist, on_delete=models.CASCADE)
    artist.verbose_name = 'Artist'
    name = models.CharField(
        max_length=255,
    )
    name.verbose_name = 'Album Title'
    normname = models.CharField(
        max_length=255,
    )
    year = models.IntegerField(
        default=0,
    )
    year.verbose_name = 'Year'
    miscellaneous = models.BooleanField(default=False)
    live = models.BooleanField(default=False)
    time_added = models.DateTimeField(default=timezone.now)
    time_added.verbose_name = 'Added to Database'

    # This is a bit of denormalization but lets us query for albums
    # with art without having to bring in possibly-expensive JOINs.
    # Also lets us just pass through original files from the filesystem
    # rather than unnecessarily bloating our database.
    art_filename = models.CharField(max_length=4096, default=None)
    art_mtime = models.IntegerField(default=0)
    art_ext = models.CharField(max_length=4, default=None)
    art_mime = models.CharField(max_length=64, default=None)

    class Meta:
        unique_together = ('artist', 'name')

    def __str__(self):
        """
        Returns a string representation of ourselves
        """
        if self.miscellaneous:
            return Album.miscellaneous_format_str % (self.artist)
        else:
            return self.name

    def save(self, *args, **kwargs):
        """
        Custom handler for save() which populates our normname field
        automatically.
        """
        self.normname = App.norm_name(self.name)
        super(Album, self).save(*args, **kwargs)

    def get_album_image(self):
        """
        Find our album art filename.  Most of the heavy lifting here
        is done in some static methods from App.  Will return None
        if no album art was found.
        """
        if self.song_set.count() > 0:
            song = self.song_set.all()[0]
            base_dir = song.full_base_dir()
            return App.get_directory_cover_image(base_dir)
        else:
            return None

    def import_album_image_from_filename(self, filename, short_filename):
        """
        Imports the given filename as our new album art.  Will yield
        a list of tuples in the format (loglevel, text) like the
        static App.add() and App.update() functions.

        `filename` is the full path to the image, whereas `short_filename`
        is what will get stored in the DB
        """
        valid_extension = False
        for ext in App.cover_extensions:
            if filename[-len(ext):] == ext:
                valid_extension = True
                break
        if not valid_extension:
            yield (App.STATUS_ERROR, 'Invalid extension for image %s' % (filename))
            return False

        if os.access(filename, os.R_OK):
            try:
                imagedata = None
                with Image.open(filename) as im:
                    if im.format in App.image_format_to_mime:
                        (mime, ext) = App.image_format_to_mime[im.format]
                        stat_data = os.stat(filename)
                        self.art_filename = short_filename
                        self.art_mtime = int(stat_data.st_mtime)
                        self.art_ext = ext
                        self.art_mime = mime
                        self.save()
                        yield (App.STATUS_INFO, 'Found album art for "%s / %s"' % (self.artist, self))
                        return True
                    else:
                        yield (App.STATUS_ERROR, 'Unknown image type found in %s: %s' % (
                            filename, im.format))
                        return False
            except Exception as e:
                yield (App.STATUS_ERROR, 'Error importing album art %s for "%s/ %s": %s' % (
                    filename, self.artist, self, e))
                return False
        else:
            yield (App.STATUS_ERROR, 'Cover image %s found but not readable' % (filename))
            return False

    def update_album_art(self):
        """
        Updates our album art based on what we find on-disk.  Yields a list of
        tuples like our App.add() and App.update() functions.
        """
        art_filename = self.get_album_image()
        if art_filename:
            yield (App.STATUS_DEBUG, 'Found art at %s' % (art_filename))
            short_filename = art_filename[len(base_path)+1:]
            for retline in self.import_album_image_from_filename(art_filename, short_filename):
                yield retline
        elif self.art_filename is not None and self.art_filename != '':
            self.art_filename = ''
            self.art_ext = ''
            self.art_mime = ''
            self.art_mtime = 0
            self.save()
            yield (App.STATUS_INFO, 'Removed art from "%s / %s"' % (self.artist, self))

    def get_original_art_filename(self):
        """
        Returns our full original art filename, or None
        """
        # App.prefs seems to be uninitialized when we get in here, possibly because
        # this is generally getting called from a custom view, which may not be
        # loading things all the way?  Dunno, but App.prefs[''] ends up throwing a
        # TypeError saying that 'NoneType' object is not scriptable, so whatever.
        prefs = global_preferences_registry.manager()
        if self.art_filename and self.art_filename != '':
            return os.path.join(prefs['exordium__base_path'], self.art_filename)
        else:
            return None

class AlbumArt(models.Model):
    """
    Class to hold album art.  Contrary to every objection that the Django
    docs give, I am at least for now going to be storing the images in the
    database.  I don't want to mirror these out on the filesystem (and I
    don't really want Django to have write permissions anywhere on the
    filesystem), and IMO this way I've got more flexibility in how I handle
    the data.  On my own head be it!

    Anyway - The original album art is kept on the filesystem and pulled
    in via Django as needed (not what Django recommends either, of course,
    but I'd rather not have that reliant on having filesystem access to
    link directly).  So this table will only ever contain the resized
    images.

    These are all written out as jpeg images.
    """

    SZ_ALBUM = 'album'
    SZ_LIST = 'list'

    SIZE_CHOICES = (
        (SZ_ALBUM, 'Album Listing'),
        (SZ_LIST, 'Inside Lists'),
    )

    resolutions = {
        SZ_ALBUM: 300,
        SZ_LIST: 75,
    }

    album = models.ForeignKey(Album, on_delete=models.CASCADE)
    size = models.CharField(
        max_length=5,
        choices=SIZE_CHOICES,
    )
    resolution = models.PositiveSmallIntegerField(default=0)
    from_mtime = models.IntegerField(default=0)

    # *gasp!*
    image = models.BinaryField()

    class Meta:
        unique_together = ('album', 'size')

    @staticmethod
    def get_or_create(album, size):
        """
        Gets a resized album art from the database (checking to
        make sure it's sized properly), or create a new one.
        """

        # Check to make sure the album has a base filename
        # to begin with.
        if album.art_filename is None or album.art_filename == '':
            return None

        # Also check to make sure we've been asked for a
        # valid size.
        if size not in [t[0] for t in AlbumArt.SIZE_CHOICES]:
            return None

        # Get our resolution
        try:
            res = AlbumArt.resolutions[size]
        except KeyError:
            return None

        # See if we have an existing object
        try:
            art = AlbumArt.objects.get(album=album, size=size)
            if art.from_mtime == album.art_mtime and art.resolution == res:
                return art
            else:
                # We could do some updates here, but if we consider it
                # a delete/add then we save some code redundancy.
                art.delete()
        except AlbumArt.DoesNotExist:
            pass

        # We could argue that here we should tell the Album object to
        # update its album art.  After all, the mtime on disk may not
        # match the mtime in the DB.  For now I'm saying to hell with
        # it, but we'll see how long that attitude lasts.

        # If we got here, we need to create a new AlbumArt object
        # based on the album's original art.
        try:
            with open(album.get_original_art_filename(), 'rb') as df:
                image_data = df.read()
                image_in = io.BytesIO(image_data)
                with Image.open(image_in) as img:
                    img.thumbnail((res, res))
                    image_out = io.BytesIO()
                    img.save(image_out, format='JPEG')
                    image_out.seek(0)
                    albumart = AlbumArt.objects.create(album=album,
                        size=size,
                        resolution=res,
                        from_mtime=album.art_mtime,
                        image=image_out.read())
                    return albumart
        except Exception as e:
            # TODO: Should log this
            return None

class Song(models.Model):

    ABR = 'ABR'
    CBR = 'CBR'
    VBR = 'VBR'
    MODE_CHOICES = (
        (ABR, ABR),
        (CBR, CBR),
        (VBR, VBR),
    )

    MP3 = 'mp3'
    OGG = 'ogg'
    TYPE_CHOICES = (
        (MP3, MP3),
        (OGG, OGG),
    )

    # Filename
    filename = models.CharField(max_length=4096)

    # Tag information
    album = models.ForeignKey(Album, on_delete=models.CASCADE)
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE)
    artist.verbose_name = 'Artist'
    title = models.CharField(max_length=255)
    title.verbose_name = 'Title'
    year = models.IntegerField()
    tracknum = models.SmallIntegerField('#')
    group = models.ForeignKey(Artist, on_delete=models.CASCADE,
        related_name='group_set',
        null=True, blank=True, default=None)
    composer = models.ForeignKey(Artist, on_delete=models.CASCADE,
        related_name='composer_set',
        null=True, blank=True, default=None)
    conductor = models.ForeignKey(Artist, on_delete=models.CASCADE,
        related_name='conductor_set',
        null=True, blank=True, default=None)

    # "raw" tag information.  Only used currently by App.update()
    # when checking to see if an artist name definition should be
    # updated to a value which is identical in normalization but
    # different in specifics.  "raw" is a bit of a misnomer, really,
    # since this value will omit any of our defined prefixes
    # regardless of the *actual* raw value.
    raw_artist = models.CharField(max_length=255)
    raw_group = models.CharField(max_length=255, default='')
    raw_composer = models.CharField(max_length=255, default='')
    raw_conductor = models.CharField(max_length=255, default='')

    # Technical information
    filetype = models.CharField(
        max_length=3,
        choices=TYPE_CHOICES,
    )
    bitrate = models.IntegerField()
    mode = models.CharField(
        max_length=3,
        choices=MODE_CHOICES,
    )
    size = models.IntegerField()
    length = models.IntegerField()
    length.verbose_name = 'Length'

    # Timestamps
    time_added = models.DateTimeField(default=timezone.now)
    time_updated = models.IntegerField(default=0)
    
    # Checksum
    sha256sum = models.CharField(max_length=64)

    def __str__(self):
        """
        Returns a string representation of ourselves
        """
        return self.title

    def full_filename(self):
        """
        Returns our full path (including library prefix)
        """
        return os.path.join(App.prefs['exordium__base_path'], self.filename)

    def base_dir(self):
        """
        Returns the base directory which contains our file (without our
        library prefix)
        """
        return os.path.dirname(self.filename)

    def full_base_dir(self):
        """
        Returns the full base directory which contains our file (including our
        library prefix)
        """
        return os.path.dirname(self.full_filename())

    def exists_on_disk(self):
        """
        Returns True if our file actually exists on disk in our library
        """
        return os.path.exists(self.full_filename())

    def changed_on_disk(self):
        """
        Returns True if the mtime of our filesystem file doesn't match
        our database entry
        """
        full_filename = self.full_filename()
        stat_result = os.stat(full_filename)
        return int(stat_result.st_mtime) != self.time_updated

    def set_artist(self, artist):
        """
        Sets our artist - convenience function so that we can loop through
        our various artist types later on in the update code.
        """
        self.artist = artist

    def set_group(self, artist):
        """
        Sets our group - convenience function so that we can loop through
        our various artist types later on in the update code.
        """
        self.group = artist

    def set_composer(self, artist):
        """
        Sets our composer - convenience function so that we can loop through
        our various artist types later on in the update code.
        """
        self.composer = artist

    def set_conductor(self, artist):
        """
        Sets our conductor - convenience function so that we can loop through
        our various artist types later on in the update code.
        """
        self.conductor = artist

    def get_group_normname(self):
        """
        Gets our group normname, if group is defined, or an empty string otherwise.
        Another convenience function which lets us loop through artist types a bit
        more easily while udpating.
        """
        if self.group:
            return self.group.normname
        else:
            return ''

    def get_conductor_normname(self):
        """
        Gets our conductor normname, if conductor is defined, or an empty string otherwise.
        Another convenience function which lets us loop through artist types a bit
        more easily while udpating.
        """
        if self.conductor:
            return self.conductor.normname
        else:
            return ''

    def get_composer_normname(self):
        """
        Gets our composer normname, if composer is defined, or an empty string otherwise.
        Another convenience function which lets us loop through artist types a bit
        more easily while udpating.
        """
        if self.composer:
            return self.composer.normname
        else:
            return ''

    def get_group_prefix(self):
        """
        Gets our group prefix, if group is defined, or an empty string otherwise.
        Another convenience function which lets us loop through artist types a bit
        more easily while udpating.
        """
        if self.group:
            return self.group.prefix
        else:
            return ''

    def get_conductor_prefix(self):
        """
        Gets our conductor prefix, if conductor is defined, or an empty string otherwise.
        Another convenience function which lets us loop through artist types a bit
        more easily while udpating.
        """
        if self.conductor:
            return self.conductor.prefix
        else:
            return ''

    def get_composer_prefix(self):
        """
        Gets our composer prefix, if composer is defined, or an empty string otherwise.
        Another convenience function which lets us loop through artist types a bit
        more easily while udpating.
        """
        if self.composer:
            return self.composer.prefix
        else:
            return ''

    def update_from_disk(self, retlines=[]):
        """
        Updates what values we can from disk.  Will not process Artist or
        Album changes, though, since those depend on a lot of other factors
        this object won't know about.  Does NOT call `.save()` on ourself,
        since we might be processing Artist and Album further.

        `retlines` can be passed in as a list of status lines which we can
        feel free to add to.  If not passed in, any logging information will
        be lost.

        Returns `None` if there is an error in updating the object, or
        a tuple containing:
           1. `artist_full`, the "new" full artist name as a string, taken from tags
           2. `album`, the "new" full album name as a string, taken from tags
           3. Ourself - a bit silly, but enables us to take some syntax shortcuts
        """

        song_info = Song.from_filename(
            self.full_filename(), self.filename, retlines
        )
        if song_info is None:
            return None

        # Update all our information (don't bother checking to see
        # if it changed, just copy the new values)
        (artist_full, group, conductor, composer, album, new_song) = song_info
        self.raw_artist = new_song.raw_artist
        self.raw_group = new_song.raw_group
        self.raw_conductor = new_song.raw_conductor
        self.raw_composer = new_song.raw_composer
        self.year = new_song.year
        self.title = new_song.title
        self.tracknum = new_song.tracknum
        self.bitrate = new_song.bitrate
        self.mode = new_song.mode
        self.size = new_song.size
        self.length = new_song.length
        self.filetype = new_song.filetype
        self.time_updated = new_song.time_updated
        self.sha256sum = new_song.sha256sum

        # Now return the artist and album we got from the new tags.
        return (artist_full, group, conductor, composer, album, self)

    @staticmethod
    def get_sha256sum(filename):
        """
        Given a filename, return a sha256sum.
        """
        hash_sha256 = hashlib.sha256()
        with open(filename, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()

    @staticmethod
    def from_filename(full_filename, short_filename, retlines=[], sha256sum=None):
        """
        Initializes a new Song object given its `full_filename` and the
        related `short_filename` which will actually be stored with the
        object.  Does NOT call `.save()` on the new object, since the
        artist and album data points will NOT be populated in this routine
        (since that information is subject to processing while doing
        global imports/updates).

        `retlines` can be passed in as a list of status lines which we can
        feel free to add to.  If not passed in, any logging information will
        be lost.

        `sha256sum` can be passed in if you've already computed a checksum.

        Returns `None` if there is an error in creating the object, or
        a tuple containing:
           1. `artist_full`, the full artist name as a string, taken from tags
           2. `group`, group/ensemble name as a string
           3. `conductor`, conductor name as a string
           4. `composer`, composer name as a string
           5. `album`, the full album name as a string, taken from tags
           6. The new `Song` object itself
        
        If you call this method like `(a, b, c) = Song.from_filename()`, you'll
        probably want to catch a `TypeError` to catch the `None` possibility.
        """

        # Set up some vars
        raw_artist = ''
        raw_group = ''
        raw_conductor = ''
        raw_composer = ''
        artist_full = ''
        artist = ''
        group = ''
        conductor = ''
        composer = ''
        album = ''
        title = ''
        filetype = ''
        tracknum = 0
        year = 0
        length = 0
        bitrate = 0

        # First check to see if we can even read the file.  Only complain
        # about this in debug - ordinarily this will be something we're
        # likely to come across intentionally.
        if not os.access(full_filename, os.R_OK):
            retlines.append((App.STATUS_DEBUG,
                'Audio file is not readable: %s' % (
                    short_filename)))
            return None

        # Load the audio file into Mutagen
        audio = mutagen.File(full_filename)

        # Do some processing that's dependent on file type
        if str(type(audio)) == "<class 'mutagen.mp3.MP3'>":
            if 'TPE1' in audio:
                artist_full = str(audio['TPE1']).strip().strip("\x00")
                (prefix, raw_artist) = Artist.extract_prefix(artist_full)
            if 'TPE2' in audio:
                group = str(audio['TPE2']).strip().strip("\x00")
                (prefix, raw_group) = Artist.extract_prefix(group)
            if 'TPE3' in audio:
                conductor = str(audio['TPE3']).strip().strip("\x00")
                (prefix, raw_conductor) = Artist.extract_prefix(conductor)
            if 'TCOM' in audio:
                composer = str(audio['TCOM']).strip().strip("\x00")
                (prefix, raw_composer) = Artist.extract_prefix(composer)
            if 'TALB' in audio:
                album = str(audio['TALB']).strip().strip("\x00")
            if 'TIT2' in audio:
                title = str(audio['TIT2']).strip().strip("\x00")
            if 'TRCK' in audio:
                tracknum = str(audio['TRCK']).strip().strip("\x00")
                if '/' in tracknum:
                    tracknum = tracknum.split('/', 2)[0]
                try:
                    tracknum = int(tracknum)
                except ValueError:
                    tracknum = 0

            try:
                if 'TYER' in audio:
                    year = int(str(audio['TYER']).strip().strip("\x00"))
                elif 'TDRL' in audio:
                    year = int(str(audio['TDRL']).strip().strip("\x00"))
                elif 'TDRC' in audio:
                    year = int(str(audio['TDRC']).strip().strip("\x00"))
            except ValueError:
                year = 0

            filetype = Song.MP3
            length = audio.info.length
            bitrate = audio.info.bitrate
            if audio.info.bitrate_mode == mutagen.mp3.BitrateMode.VBR:
                mode = Song.VBR
            elif audio.info.bitrate_mode == mutagen.mp3.BitrateMode.ABR:
                mode = Song.ABR
            else:
                mode = Song.CBR
        else:
            retlines.append((App.STATUS_ERROR,
                'ERROR: audio type of %s not yet understood: %s' % (
                    short_filename, type(audio))))
            return None

        # Some data validation here.  We can have a song without an album,
        # but we won't allow one which doesn't have an artist or title.
        if artist_full == '':
            retlines.append((App.STATUS_ERROR,
                'ERROR: Artist name not found, from audio file %s' % (
                    short_filename)))
            return None
        if title == '':
            retlines.append((App.STATUS_ERROR,
                'ERROR: Title not found, from audio file %s' % (
                    short_filename)))
            return None

        # A bit of data validation here - "Various" is a protected
        # special artist name, unfortunately.  Hope I never get into a
        # band called "Various"
        if artist_full == 'Various':
            retlines.append((App.STATUS_ERROR,
                'ERROR: Artist name "Various" is reserved, from audio file %s' % (
                    short_filename)))
            return None

        # Get some data independent of file type
        stat_result = os.stat(full_filename)
        #file_mtime = datetime.datetime.fromtimestamp(stat_result.st_mtime)
        file_mtime = stat_result.st_mtime
        file_size = stat_result.st_size
        if sha256sum is None:
            sha256sum = Song.get_sha256sum(full_filename)

        # Create the object
        song_obj = Song(
            filename = short_filename,
            raw_artist = raw_artist,
            raw_group = raw_group,
            raw_conductor = raw_conductor,
            raw_composer = raw_composer,
            year = year,
            title = title,
            tracknum = tracknum,
            bitrate = bitrate,
            mode = mode,
            size = file_size,
            length = length,
            filetype = filetype,
            time_added = timezone.now(),
            time_updated = file_mtime,
            sha256sum = sha256sum,
        )

        # Return
        return (artist_full, group, conductor, composer, album, song_obj)

class App(object):
    """
    Mostly just a collection of static methods used to do various things
    in Exordium (adds/updates/etc).
    """

    STATUS_DEBUG = 'debug'
    STATUS_INFO = 'info'
    STATUS_ERROR = 'error'
    STATUS_SUCCESS = 'success'

    prefs = None

    prefixre = re.compile('^((the)\s+)?(.+)$', re.IGNORECASE)
    livere = re.compile('^....[-\._]..[-\._].. - live', re.IGNORECASE)

    norm_translation = str.maketrans('äáàâãåëéèêẽïíìîĩöóòôõøüúùûũůÿýỳŷỹðçř“”‘’', 'aaaaaaeeeeeiiiiioooooouuuuuuyyyyydcr""\'\'')

    cover_extensions = ['.png', '.jpg', '.gif']
    image_format_to_mime = {
        'PNG': ('image/png', 'png'),
        'JPEG': ('image/jpeg', 'jpg'),
        'GIF': ('image/gif', 'gif'),
    }

    @staticmethod
    def norm_name(name):
        """
        Returns a name which can be used to compare against other
        names, disregarding case and special characters like umlauts.
        and the like.

        This process used to do a few things which aren't done anymore.
        We used to use `unicodedata.normalize('NFKD', name)` in here
        but was running into problems such as the following:

            >>> len('umläut')
            6
            >>> len(unicodedata.normalize('NFKD', 'umläut'))
            7

        ... since the normalized form would technically be taking
        two characters to combine the umlauts.  In the end I 
        figured it just wasn't worth it.

        Then, after doing some initial manual translations, the final
        step used to be to convert to plain ASCII - if we ended up
        losing any string length due to that conversion, we'd
        assume that we don't know enough to safely denormalize it
        and just return the original string again.  In the end I opted
        not to do that either, since we'd then have some warring data
        types with explicitly-encoded strings and the like.

        Note that if this method doesn't include some characters which
        are considered identical in your database's current collation
        settings, you can end up with IntegrityErrors when trying to
        insert new records, even if this method doesn't equate the two
        values.
        """
        # TODO: Translations and replacements could use some expansion
        return name.lower().translate(App.norm_translation).replace(
            'æ', 'ae').replace('ß', 'ss').replace('þ', 'th').replace(
            'œ', 'oe').replace('&', 'and')
        #lower = name.lower()
        #lower = lower.translate(App.norm_translation).replace(
        #    'æ', 'ae').replace('ß', 'ss').replace('þ', 'th')
        #final = lower.encode('ASCII', 'ignore')
        #if len(final) != len(lower):
        #    return lower
        #else:
        #    return final

    @staticmethod
    def ensure_prefs():
        """
        Loads our preferences in the root context of the App object.  We
        can't assign outside of a method because this class gets loaded
        before Django loads the actual models, and dynamic_preferences
        can't actually load anything then.
        """
        if App.prefs is None:
            App.prefs = global_preferences_registry.manager()

    @staticmethod
    def get_filesystem_media(extra_base=None):
        """
        Returns a list of all media found on the filesystem.  Optionally
        also only find files within `extra_base`.
        """
        App.ensure_prefs()
        base_path = App.prefs['exordium__base_path']
        all_files = []
        if extra_base is None:
            start_base = base_path
        else:
            start_base = os.path.join(base_path, extra_base)
        for (dirpath, dirnames, filenames) in os.walk(start_base, followlinks=True):
            for filename in filenames:
                filename_lower = filename.lower()
                if filename_lower[-4:] == '.mp3' or filename_lower[-4:] == '.ogg':
                    short_filename = os.path.join(dirpath, filename)[len(base_path)+1:]
                    all_files.append(short_filename)
        return all_files

    @staticmethod
    def ensure_various_artists():
        """
        Ensures that we have a Various Artists album in the DB.  Returns
        True if a "Various" artist was created, and False otherwise
        """
        try:
            va = Artist.objects.get(name='Various', various=True)
            return False
        except Artist.DoesNotExist:
            artist_obj = Artist(name='Various', prefix='', various=True)
            artist_obj.save()
            return True

    @staticmethod
    def add(to_add=None):
        """
        Looks through our base_dir for new files we don't know anything
        about yet.  Yields its entire processing status log as a generator,
        as tuples of the form (status, text).

        `status` will be one of `info`, `debug`, `success`, or `error`, so can
        be processed appropriately by whatever calls this method.

        Optionally, pass in `to_add` to have this method process given a list
        of tuples containing filenames and sha256sums.  This way we can be
        called from update()

        `to_add` should be a list of tuples, where the first field is the
        filename and the second is either the sha256sum or `None`, if the
        checksum has not yet been computed.
        """

        App.ensure_prefs()

        # Some statistics
        artists_added = 0
        albums_added = 0
        songs_added = 0

        # Check to see if we're in the middle of an update or not
        updating = True
        if to_add is None:
            to_add = []
            yield (App.STATUS_INFO, 'Starting process...')
            updating = False

            # First grab a dict of all songs we already know about
            known_song_paths = {}
            for song in Song.objects.all():
                known_song_paths[song.filename] = True

            # Now walk through our directory structure looking for more music
            for short_filename in App.get_filesystem_media():
                if short_filename not in known_song_paths:
                    yield (App.STATUS_DEBUG, 'Found file: %s' % (short_filename))
                    to_add.append((short_filename, None))
            
            # If we have no data, just get out of here
            if len(to_add) == 0:
                yield (App.STATUS_SUCCESS, 'No new music found!')
                return

            # Ensure that we have a Various artist.
            if App.ensure_various_artists():
                yield (App.STATUS_INFO, 'Created new artist "Various" (meta-artist)')
                artists_added += 1

        else:

            # Don't bother reporting about no added files if we're updating.
            # Theoretically we shouldn't get here, but no worries if we do.
            if len(to_add) == 0:
                return

        # Grab a nested dict of all artists and their albums
        album_art_needed = []
        known_artists = {}
        for artist in Artist.objects.all():
            known_artists[artist.normname] = (artist, {}, {})
        for album in Album.objects.all():
            if album.miscellaneous:
                known_artists[album.artist.normname][2]['miscellaneous'] = album
            else:
                known_artists[album.artist.normname][1][album.normname] = album

        # Also grab songs and sort by what directory they're in.  We only
        # need this for the following scenario: An album exists in a
        # directory, by a single artist, but later a new track is added
        # the album with a second artist (thus turning it into a VA album)
        existing_songs_in_dir = {}
        for song in Song.objects.all():
            song_base_dir = song.base_dir()
            if song_base_dir not in existing_songs_in_dir:
                existing_songs_in_dir[song_base_dir] = []
            existing_songs_in_dir[song_base_dir].append(song)

        # And now loop through our files-to-add.
        # The songs_in_dir dict is what we're using to figure out
        # "Various Artists" type albums - the keys are the directory
        # names in which the files are found, and the values are
        # lists of all the songs in that dir (as a SongHelper object)
        songs_in_dir = {}
        checksums_computed = 0
        total_checksums = 0
        for (short_filename, sha256sum) in to_add:
            if sha256sum is None:
                total_checksums += 1
        if total_checksums > 0:
            yield (App.STATUS_INFO, 'Total track checksums to compute: %d' % (total_checksums))
        for (short_filename, sha256sum) in to_add:
            full_filename = os.path.join(App.prefs['exordium__base_path'], short_filename)

            retlines = []
            if sha256sum is None:
                checksums_computed += 1
                if checksums_computed % 100 == 0:
                    yield (App.STATUS_INFO, 'Checksums gathered for %d/%d tracks (%d%%)' % (
                        checksums_computed, total_checksums, (checksums_computed/total_checksums*100)))
            song_info = Song.from_filename(
                full_filename, short_filename,
                retlines=retlines, sha256sum=sha256sum)
            for retline in retlines:
                yield retline
            if song_info is None:
                continue
            else:
                helper = SongHelper(*song_info)
                if helper.base_dir not in songs_in_dir:
                    songs_in_dir[helper.base_dir] = []
                songs_in_dir[helper.base_dir].append(helper)

        # Figure out any Various-Artists type places
        # There's some extra weirdness in here to deal with a possible
        # scenario where a single directory contains both multiple
        # artists and multiple albums - not all albums in that dir
        # would necessarily be Various
        for (base_dir, songlist) in songs_in_dir.items():
            albums_to_update = {}
            album_artist = {}

            # Step 1: Loop through new tracks and populate album_artist
            for helper in songlist:
                if helper.norm_album not in album_artist:
                    album_artist[helper.norm_album] = helper.artist_name
                if helper.norm_artist_name != App.norm_name(album_artist[helper.norm_album]):
                    album_artist[helper.norm_album] = 'Various'

            # Step 2: Loop through any existing tracks in this
            # directory and potentially mark them for update as well.
            if base_dir in existing_songs_in_dir:
                for song in existing_songs_in_dir[base_dir]:
                    if song.album.normname not in album_artist:
                        album_artist[song.album.normname] = song.album.artist.name
                    if song.artist.normname != App.norm_name(album_artist[song.album.normname]):
                        album_artist[song.album.normname] = 'Various'
                        albums_to_update[song.album.normname] = song.album

            # Step 3: actually assign the artist to the SongHelper
            for helper in songlist:
                helper.set_album_artist(album_artist[helper.norm_album])

            # Step 4: update existing album records if we need to
            for (albumname, album) in albums_to_update.items():
                try:
                    del known_artists[album.artist.normname][1][album.normname]
                    yield (App.STATUS_INFO, 'Updating album "%s / %s" to artist "%s"' %
                        (album.artist, album, album_artist[album.normname]))
                    album.artist = Artist.objects.get(normname=App.norm_name(album_artist[album.normname]))
                    album.save()
                    known_artists[album.artist.normname][1][album.normname] = album
                except Artist.DoesNotExist:
                    yield (App.STATUS_ERROR, 'Cannot find artist "%s" to convert to Various' %
                        (album_artist[albumname]))

        # Loop through helper objects
        for (base_dir, songlist) in songs_in_dir.items():

            for helper in songlist:

                # Check to see if we know the artist yet, and if not create it.
                for (norm_name, artist_name, artist_prefix) in [
                        (helper.norm_artist_name, helper.artist_name, helper.artist_prefix),
                        (helper.norm_group_name, helper.group_name, helper.group_prefix),
                        (helper.norm_conductor_name, helper.conductor_name, helper.conductor_prefix),
                        (helper.norm_composer_name, helper.composer_name, helper.composer_prefix)]:
                    if artist_name != '':
                        if norm_name not in known_artists:
                            try:
                                artist_obj = Artist.objects.create(name=artist_name, prefix=artist_prefix)
                                known_artists[norm_name] = (artist_obj, {}, {})
                                yield (App.STATUS_INFO, 'Created new artist "%s"' % (artist_obj))
                                artists_added += 1
                            except IntegrityError:
                                # Apparently in this case we're not associating things according to our
                                # database's collation values.  We'll just try to load the matching artist
                                # for now...
                                artist_obj = Artist.objects.get(normname=norm_name)
                                known_artists[norm_name] = (artist_obj, {}, {})
                                yield (App.STATUS_DEBUG, 'Loaded existing artist for "%s"' % (artist_obj))
                        elif artist_prefix != '' and known_artists[norm_name][0].prefix == '':
                            # While we're at it, if our artist didn't have a prefix originally
                            # but we see one now, update the artist record with that prefix.
                            known_artists[norm_name][0].prefix = artist_prefix
                            known_artists[norm_name][0].save()
                            yield (App.STATUS_DEBUG, 'Updated artist to include prefix: "%s"' %
                                (known_artists[norm_name][0]))

                # Check to see if we know the album yet, and if not create it.
                if helper.miscellaneous_album:
                    if 'miscellaneous' not in known_artists[helper.norm_album_artist][2]:
                        try:
                            with transaction.atomic():
                                album_obj = Album.objects.create(name=helper.album,
                                        artist=known_artists[helper.norm_album_artist][0],
                                        year=helper.song_obj.year,
                                        miscellaneous=helper.miscellaneous_album,
                                        live=helper.live_album)
                                known_artists[helper.norm_album_artist][2]['miscellaneous'] = album_obj
                                yield (App.STATUS_INFO, 'Created new miscellaneous album "%s / %s"' % (album_obj.artist, album_obj))
                                albums_added += 1
                        except IntegrityError:
                            album_obj = Album.objects.get(miscellaneous=True, artist=known_artists[helper.norm_album_artist][0])
                            known_artists[helper.norm_album_artist][2]['miscellaneous'] = album_obj
                            yield (App.STATUS_DEBUG, 'Loaded existing miscellaneous album for "%s / %s"' % (album_obj.artist, album_obj))
                else:
                    if helper.norm_album not in known_artists[helper.norm_album_artist][1]:
                        try:
                            with transaction.atomic():
                                album_obj = Album.objects.create(name=helper.album,
                                        artist=known_artists[helper.norm_album_artist][0],
                                        year=helper.song_obj.year,
                                        miscellaneous=helper.miscellaneous_album,
                                        live=helper.live_album)
                                known_artists[helper.norm_album_artist][1][helper.norm_album] = album_obj
                                yield (App.STATUS_INFO, 'Created new album "%s / %s"' % (album_obj.artist, album_obj))
                                albums_added += 1
                        except IntegrityError:
                            album_obj = Album.objects.get(normname=helper.norm_album, artist=known_artists[helper.norm_album_artist][0])
                            known_artists[helper.norm_album_artist][1][helper.norm_album] = album_obj
                            yield (App.STATUS_DEBUG, 'Loaded existing album for "%s / %s"' % (album_obj.artist, album_obj))

                # Mark this album as possibly needing an album art update
                if not album_obj.art_filename:
                    album_art_needed.append(album_obj)
                
                # And now, update and save our song_obj
                helper.song_obj.artist = known_artists[helper.norm_artist_name][0]
                if helper.norm_group_name != '' and helper.norm_group_name in known_artists:
                    helper.song_obj.group = known_artists[helper.norm_group_name][0]
                if helper.norm_conductor_name != '' and helper.norm_conductor_name in known_artists:
                    helper.song_obj.conductor = known_artists[helper.norm_conductor_name][0]
                if helper.norm_composer_name != '' and helper.norm_composer_name in known_artists:
                    helper.song_obj.composer = known_artists[helper.norm_composer_name][0]
                if helper.miscellaneous_album:
                    helper.song_obj.album = known_artists[helper.norm_album_artist][2]['miscellaneous']
                else:
                    helper.song_obj.album = known_artists[helper.norm_album_artist][1][helper.norm_album]
                helper.song_obj.save()
                songs_added += 1

        # Report
        if not updating:

            # Get album art
            for retline in App.find_album_art(album_art_needed):
                yield retline

            yield (App.STATUS_SUCCESS, 'Finished adding new music!')
            yield (App.STATUS_SUCCESS, 'Artists added: %d' % (artists_added))
            yield (App.STATUS_SUCCESS, 'Albums added: %d' % (albums_added))
            yield (App.STATUS_SUCCESS, 'Songs added: %d' % (songs_added))

        # Finally, return
        return

    @staticmethod
    def update():
        """
        Looks through our base_dir for any files which may have been changed,
        deleted, moved, or added (will call out to `add()` to handle the latter,
        if needed).

        Yields its entire processing status log as a generator, as tuples of the
        form (status, text).

        `status` will be one of `info`, `debug`, `success`, or `error`, so can
        be processed appropriately by whatever calls this method.

        There's a fair amount of duplicated code between this and `add()`.
        Arguably there should only be one function, and adds in specific would
        just be a subset of that.

        This whole procedure is... messy.  Lots of weird little custom dicts and
        lists flying around to keep everything straight, and not always terribly
        well documented in-code.
        """

        App.ensure_prefs()

        yield (App.STATUS_INFO, 'Starting process...')

        to_update = []
        to_delete = {}

        # Just get this out of the way up here.
        if App.ensure_various_artists():
            yield (App.STATUS_INFO, 'Created new artist "Various" (meta-artist)')

        # Step one - loop through the database and find any files which are missing
        # or have been updated.  Create `digest_dict` which is a mapping of sha256sums
        # to the database Song object, and `db_paths` which is a mapping of filenames
        # to database Song objects, used below to find out which new files have been
        # added.
        #
        # Also populates the `to_update` list with files whose mtimes have changed, and
        # the `to_delete` dict which at this point is technically only *possible*
        # deletions - our `digest_dict` structure will be used to determine below if
        # that deleted file has merely moved
        db_paths = {}
        digest_dict = {}
        for song in Song.objects.all():

            if song.exists_on_disk():
                db_paths[song.filename] = song
                if song.changed_on_disk():
                    to_update.append(song)
                    yield (App.STATUS_DEBUG, 'Updated file: %s' % (song.filename))
            else:
                # Just store some data for now
                to_delete[song] = True
                digest_dict[song.sha256sum] = song

        # Figure out what new files might exist (deleted files might have just moved)
        to_add = []
        for path in App.get_filesystem_media():
            if path not in db_paths:
                sha256sum = Song.get_sha256sum(os.path.join(App.prefs['exordium__base_path'], path))
                if sha256sum in digest_dict:
                    song = digest_dict[sha256sum]
                    yield (App.STATUS_INFO, 'File move detected: %s -> %s' % (
                        song.filename, path
                    ))
                    song.filename = path
                    song.save()
                    del digest_dict[sha256sum]
                    del to_delete[song]
                else:
                    yield (App.STATUS_DEBUG, 'Found new file: %s' % (path))
                    to_add.append((path, sha256sum))

        # Report on deleted files here, and delete them
        delete_rel_albums = {}
        delete_rel_artists = {}
        album_changes = {}
        for song in to_delete.keys():
            delete_rel_albums[song.album] = True
            delete_rel_artists[song.artist] = True
            if song.group:
                delete_rel_artists[song.group] = True
            if song.conductor:
                delete_rel_artists[song.conductor] = True
            if song.composer:
                delete_rel_artists[song.composer] = True
            album_changes[os.path.dirname(song.filename)] = True
            song.delete()
            yield (App.STATUS_INFO, 'Deleted file: %s' % (song.filename))

        # Handle adds here, just pass through for now.  There's a bunch of duplicated
        # effort between here and the update section below, and some various unnecessary
        # duplication of work, but whatever.  We'll cope.
        if len(to_add) > 0:
            for retline in App.add(to_add=to_add):
                yield retline

        # Updates next, pull in the new data
        to_update_helpers = {}
        possible_artist_updates = {}
        for song in to_update:

            retlines = []
            song_info = song.update_from_disk(retlines)
            for retline in retlines:
                yield retline
            if song_info is None:
               yield (App.STATUS_ERROR, 'Could not read updated information for: %s' % (song.filename))
               continue

            helper = SongHelper(*song_info)

            # Process an Artist change, if we need to
            artist_changed = False
            for (is_artist, norm_name, artist_name, artist_prefix, song_norm_name, song_artist_prefix, loop_artist_obj, assign_func) in [
                    (True, helper.norm_artist_name, helper.artist_name, helper.artist_prefix,
                        song.artist.normname, song.artist.prefix, song.artist, song.set_artist),
                    (False, helper.norm_group_name, helper.group_name, helper.group_prefix,
                        song.get_group_normname(), song.get_group_prefix(), song.group, song.set_group),
                    (False, helper.norm_conductor_name, helper.conductor_name, helper.conductor_prefix,
                        song.get_conductor_normname(), song.get_conductor_prefix(), song.conductor, song.set_conductor),
                    (False, helper.norm_composer_name, helper.composer_name, helper.composer_prefix,
                        song.get_composer_normname(), song.get_composer_prefix(), song.composer, song.set_composer)]:
                if artist_name == '':
                    if loop_artist_obj is not None:
                        assign_func(None)
                        delete_rel_artists[loop_artist_obj] = True
                else:
                    if norm_name == song_norm_name:
                        # Check for a prefix update, if we have it
                        if artist_prefix != '' and song_artist_prefix == '':
                            loop_artist_obj.prefix = artist_prefix
                            loop_artist_obj.save()
                            yield (App.STATUS_DEBUG, 'Updated artist to include prefix: "%s"' %
                                (loop_artist_obj))
                        # Also check to see if the non-normalized artist name matches or not.
                        # If not, we MAY want to update the main artist name to match, though
                        # only if literally all instances of the artist name are equal, in the
                        # DB.
                        if artist_name != loop_artist_obj.name:
                            possible_artist_updates[loop_artist_obj.normname] = True
                    else:
                        # Otherwise, try to load in the artist we should be, or create a new one
                        try:
                            artist_obj = Artist.objects.get(normname=norm_name)
                            if artist_prefix != '' and artist_obj.prefix == '':
                                artist_obj.prefix = artist_prefix
                                artist_obj.save()
                                yield (App.STATUS_DEBUG, 'Updated artist to include prefix: "%s"' %
                                    (artist_obj))
                        except Artist.DoesNotExist:
                            artist_obj = Artist.objects.create(name=artist_name, prefix=artist_prefix)
                            yield (App.STATUS_INFO, 'Created new artist "%s"' % (artist_obj))
                        if loop_artist_obj is not None:
                            delete_rel_artists[loop_artist_obj] = True
                        assign_func(artist_obj)

                        # At this point, it generally doesn't matter whether the
                        # album name has changed or not, since the only case in which
                        # we DON'T do an album switch now is if we're a various artists
                        # album.  We'll include this in the next 'if' clause
                        if is_artist:
                            artist_changed = True

            # Ordinarily we would compare normalized names here, but there's the possibility
            # that all tracks making up an album might have changed the album name to something
            # which would otherwise match our normalized case, and if ALL the tracks get updated
            # then that's a change we'd want to make even if it's "virtually" the same thing.
            if artist_changed or helper.album != song.album.name:
                delete_rel_albums[song.album] = True
                album_changes[helper.base_dir] = True
                to_update_helpers[song.filename] = helper

        # If we have any album changes to make, do so.
        for album_basedir in album_changes.keys():
            files = App.get_filesystem_media(extra_base=album_basedir)
            album_artist = {}
            album_tracks = {}
            album_denorm = {}
            miscellaneous_albums = {}
            live_albums = {}
            for filename in files:

                if filename in to_update_helpers:
                    helper = to_update_helpers[filename]
                    album_tuple = (helper.miscellaneous_album, helper.live_album,
                            helper.album, helper.norm_album,
                            helper.song_obj.artist.name, helper.song_obj.artist.normname,
                            helper.song_obj)
                else:
                    try:
                        song = Song.objects.get(filename=filename)
                        # This is fudging a bit; these songs would only need a save() later
                        # if they actually change, but whatever.
                        to_update.append(song)
                        album_tuple = (song.album.miscellaneous, song.album.live,
                                song.album.name, song.album.normname,
                            song.artist.name, song.artist.normname,
                            song)
                    except Song.DoesNotExist:
                        yield (App.STATUS_ERROR, 'Could not find Song record for: %s' % (filename))
                        continue

                # Album Artist Name detection
                (miscellaneous, live, album, norm_album, artist, norm_artist, song_obj) = album_tuple
                if norm_album not in album_artist:
                    yield (App.STATUS_DEBUG, 'Initial album artist: %s' % (artist))
                    # TODO: this is ludicrous; should just be passing around a SongHelper or something
                    album_artist[norm_album] = (artist, norm_artist)
                    album_tracks[norm_album] = []
                    album_denorm[norm_album] = album
                    miscellaneous_albums[norm_album] = miscellaneous
                    live_albums[norm_album] = live
                album_tracks[norm_album].append(song_obj)
                if norm_artist != album_artist[norm_album][1]:
                    yield (App.STATUS_DEBUG, 'Got artist change from %s -> %s' % (album_artist[norm_album][0], artist))
                    album_artist[norm_album] = ('Various', 'various')

            #yield (App.STATUS_DEBUG, album_artist)
            #yield (App.STATUS_DEBUG, album_tracks)
            #yield (App.STATUS_DEBUG, album_denorm)
            #yield (App.STATUS_DEBUG, miscellaneous_albums)

            # Actually make the changes
            updated_albums = {}
            # We're sorting here because a test uncovered a bug whose exact behavior
            # depended on which order some updates happened in, and the behavior wasn't
            # predictable unless we sorted.  Ideally the order shouldn't matter, but
            # for the purposes of squashing the bug fully and having test cases for
            # all possibilities, we'll just keep sorting.
            for norm_album in sorted(album_artist.keys()):
                album = album_denorm[norm_album]
                (artist, norm_artist) = album_artist[norm_album]
                tracks = album_tracks[norm_album]
                miscellaneous = miscellaneous_albums[norm_album]
                live = live_albums[norm_album]
                yield (App.STATUS_DEBUG, 'Looking at album %s, artist %s, tracks %d' % (album, artist, len(tracks)))

                try:
                    artist_obj = Artist.objects.get(name=artist)
                except Artist.DoesNotExist:
                    # I don't think it should be possible to get here.
                    yield (App.STATUS_ERROR, 'Artist "%s" not found for file change on album "%s"' % (artist, album))
                    continue

                # Check to see if we should update our current album record,
                # use a different, existing album record, or create a brand-new
                # album.  Our criteria for creating a new one is basically that
                # every track in the existing album is being touched by this update.
                # This logic is a *bit* fuzzy and may not hold in our rare cases
                # when we have a bunch of mixed "other" type tracks in a single
                # dir, though hopefuly that's just legacy stuff which can stand
                # a bit of loopiness.
                track_updates_possible = 0
                tracks_to_update = 0
                seen_album_title = None
                for track in tracks:
                    #if track.album.normname == norm_album:
                    track_updates_possible += 1
                    if track.filename in to_update_helpers:
                        if seen_album_title is None:
                            seen_album_title = to_update_helpers[track.filename].album
                        #yield (App.STATUS_DEBUG, 'Comparing album %s to %s' % (to_update_helpers[track.filename].album, seen_album_title))
                        if to_update_helpers[track.filename].album == seen_album_title:
                            tracks_to_update += 1
                yield (App.STATUS_DEBUG, 'tracks to update: %d, possible: %d' % (tracks_to_update, track_updates_possible))
                if tracks_to_update != 0 and tracks_to_update == track_updates_possible and tracks[0].album.pk not in updated_albums:
                    album_obj = tracks[0].album
                    old_artist = album_obj.artist
                    old_name = album_obj.name
                    album_obj.artist = artist_obj
                    if tracks[0].year is not None and tracks[0].year != 0:
                        album_obj.year = tracks[0].year
                    album_obj.name = album
                    album_obj.miscellaneous = miscellaneous
                    album_obj.live = live
                    album_obj.save()
                    yield (App.STATUS_INFO, 'Updated album from "%s / %s" to "%s / %s"' %
                        (old_artist, old_name, album_obj.artist, album_obj))
                    updated_albums[album_obj.pk] = True
                else:
                    try:
                        album_obj = Album.objects.get(normname=norm_album, artist__normname=norm_artist)
                        yield (App.STATUS_DEBUG, 'Using existing album "%s / %s" for %s' % (album_obj.artist, album_obj, album))
                    except Album.DoesNotExist:
                        album_obj = Album(name=album,
                            artist=artist_obj,
                            year=tracks[0].year,
                            miscellaneous=miscellaneous,
                            live=live)
                        album_obj.save()
                        yield (App.STATUS_INFO, 'Created new album "%s / %s"' % (album_obj.artist, album_obj))
                    updated_albums[album_obj.pk] = True

                for track in tracks:
                    if track.album != album_obj:
                        track.album = album_obj
                        yield (App.STATUS_INFO, 'Updated album to "%s / %s" for: %s' % (album_obj.artist, album_obj, track.filename))

        # Now that we theoretically have song-change albums sorted, loop through
        # again and save out all the song changes.
        for song in to_update:
            song.save()
            yield (App.STATUS_DEBUG, 'Processed file changes for: %s' % (song.filename))

        # Loop through the database for all albums/artists which have had records
        # deleted, and delete the album/artist if there's no more dependent data
        for album in delete_rel_albums.keys():
            if album.song_set.count() == 0:
                yield (App.STATUS_INFO, 'Deleted orphaned album "%s / %s"' % (album, album.artist))
                album.delete()
        for artist in delete_rel_artists.keys():
            if artist.name != 'Various':
                if (artist.album_set.count() == 0 and Song.objects.filter(Q(artist=artist) |
                        Q(group=artist) | Q(conductor=artist) | Q(composer=artist)).count() == 0):
                    yield (App.STATUS_INFO, 'Deleted orphaned artist "%s"' % (artist))
                    artist.delete()

        # Now check to see if we need to update any artist names.  We'll be here
        # if a normalized name matched but the "real" name didn't.
        for normname in possible_artist_updates.keys():
            try:
                artist = Artist.objects.get(normname=normname)
                seen_name = None
                mismatch = False
                for song in (artist.song_set.all() | artist.group_set.all() | 
                        artist.conductor_set.all() | artist.composer_set.all()):
                    for (song_artist_obj, song_raw_name) in [
                            (song.artist, song.raw_artist),
                            (song.group, song.raw_group),
                            (song.conductor, song.raw_conductor),
                            (song.composer, song.raw_composer),
                            ]:
                        if song_artist_obj is not None and song_artist_obj.normname == artist.normname:
                            if seen_name is None:
                                seen_name = song_raw_name
                            elif seen_name != song_raw_name:
                                mismatch = True
                                break
                    if mismatch:
                        break
                if not mismatch:
                    yield (App.STATUS_INFO, 'Updated artist name from "%s" to "%s"' % (
                        artist.name, seen_name))
                    artist.name = seen_name
                    artist.save()
            except Artist.DoesNotExist:
                # Maybe we were deleted or something, whatever.
                pass

        # Get album art
        for retline in App.find_album_art():
            yield retline

        # Finally, return
        yield (App.STATUS_SUCCESS, 'Finished update/clean!')
        return

    @staticmethod
    def get_directory_cover_images(directory):
        """
        Scans a directory to find a likely album art.  Returns a
        list of all available album art in the directory, in order
        of our preference.  (In general you'll only really be
        interested in the very first item in the list.)  Note that
        the returned filenames will NOT include the directory
        component.

        The sorting here works as follows:
            1) We prefer any image named "cover.ext"
            2) Next we prefer any image named "coverXXX.ext"
            3) finally any other image.

        Additionally, we will prefer filename extensions in the order
        listed in App.cover_extensions, within those three groups.
        "cover.gif" will still be sorted before "cover-back.png"
        """

        # Dict of tuples, where:
        #   [0] is "cover.ext" style images
        #   [1] is "cover$foo.ext" images
        #   [2] is other image files
        extensions = {}
        for ext in App.cover_extensions:
            extensions[ext] = ([], [], [])

        # Loop through filenames
        for filename in os.listdir(directory):
            for ext in App.cover_extensions:
                if filename[-len(ext):] == ext:
                    if filename == 'cover%s' % (ext):
                        extensions[ext][0].append(filename)
                    elif filename[:5] == 'cover':
                        extensions[ext][1].append(filename)
                    else:
                        extensions[ext][2].append(filename)
                    break
        
        # Put together our list to return
        retlist = []
        for ext in App.cover_extensions:
            retlist.extend(extensions[ext][0])
        for ext in App.cover_extensions:
            retlist.extend(sorted(extensions[ext][1]))
        for ext in App.cover_extensions:
            retlist.extend(sorted(extensions[ext][2]))
        return retlist

    @staticmethod
    def get_directory_cover_image(directory):
        """
        Scans our directory for a preferred cover image and returns
        the filename, or None.  Will do a reverse-recursion to the
        parent directory if no image files are found in the given
        directory.
        """
        images = App.get_directory_cover_images(directory)
        if len(images) == 0:
            images = App.get_directory_cover_images(os.path.join(directory, '..'))
            if len(images) == 0:
                return None
            else:
                return os.path.normpath(os.path.join(directory, '..', images[0]))
        else:
            return os.path.join(directory, images[0])

    @staticmethod
    def find_album_art(albums=None):
        """
        Finds album art for any album which doesn't currently have it.  Will not touch
        any album which already has album art defined.  If `albums` is passed as a
        list of album objects, only those albums will be checked for album art, rather
        than looping through the whole database

        Yields its entire processing status log as a generator, as tuples of the form
        (status, text).

        `status` will be one of `info`, `debug`, `success`, or `error`, so can
        be processed appropriately by whatever calls this method.
        """

        if albums is None:
            albums = Album.objects.filter(Q(art_filename=None) | Q(art_filename=''))

        if len(albums) == 0:
            return

        yield (App.STATUS_INFO, 'Scanning for album art - albums to scan: %d' % (len(albums)))

        base_path = App.prefs['exordium__base_path']
        for album in albums:
            art_filename = album.get_album_image()
            if art_filename:
                yield (App.STATUS_DEBUG, 'Found art at %s' % (art_filename))
                short_filename = art_filename[len(base_path)+1:]
                for retline in album.import_album_image_from_filename(art_filename, short_filename):
                    yield retline
            else:
                yield (App.STATUS_DEBUG, 'No album art found for "%s / %s"' %
                    (album.artist, album))

        yield (App.STATUS_INFO, 'Album art scanning finished')
        return
