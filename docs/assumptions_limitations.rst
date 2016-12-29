.. Assumptions / Limitations

Assumptions and Limitations
===========================

As mentioned on the main page, Exordium does not really attempt to be
a general-purpose web music library suitable for widespread use.  The
only configuration options currently available are those necessary for
basic operation.  Exordium was born out of my persistent
dissatisfaction with existing web music library applications.  I've
been using various library applications over the years but have always
ended up maintaining my own patchsets to alter their behavior to suit
what I like, and in the end I figured it would be more rewarding to
just write my own.

So, Exordium represents essentially my own personal ideal of a web
music library application, and its design decisions and operational
goals reflect a very specific set of requirements: my own.  If your
ideal music library differs from my own in even moderate ways, other
music library apps are much more likely to be to your liking.

I would, of course, be happy to accept patches which add, extend, or
modify Exordium behavior, so long as the current functionality remains
the default.  I certainly don't actually *expect* any patches, of course,
given that Exordium's target market is exactly one individual.

Assumptions
-----------

- Except for the Javascript necessary to hook into jPlayer, and jPlayer
  itself, there is no client-side Javascript or AJAX-style dynamic page
  content.  All HTML is generated server-side.  The application is
  quite usable from text-based browsers.

- Music files must be accessible via the local filesystem on which Django
  is running, and stored as either mp3, ogg vorbis, or m4a (mp4a).

- The entire music library must be available from a single directory
  prefix.  If subdirs of this root dir span multiple volumes (or network
  mounts), that's fine, but there is NO support for multiple libraries in
  Exordium.

- Exordium itself will never attempt to write to your library directory for
  any reason - all music files (and album art) are managed outside of
  this app.  Write access to a directory on the filesystem is required
  for zipfile downloads, but that directory need not be in your music
  library.

- Music files should be, in general, arranged scrupulously: All files
  within a single directory belong to the same album, and an album should
  never span multiple directories.  There's actually plenty of wiggle room
  here, and Exordium should correctly deal with directories full of
  "miscellaneous" files, etc, but in general the library should be
  well-ordered and have albums contained in their own directories.  This
  is less important during the initial library import, but becomes much
  more important when updating tags or rearranging your filesystem layout,
  as Exordium uses the directory structure to help determine what kind of
  changes have been made.

  - Directory containment is the primary method through which Various Artists
    albums are collated.  A group of files in the same directory with different
    artists but the same album name will be sorted into a single "Various"
    album containing all those tracks.  Conversely, if an album name is shared
    by tracks from different directories (each dir's files with a different
    artist name), multiple albums will be created.

  - Tracks without an album tag will be sorted into a "virtual" album entitled
    "Non-Album Tracks: Band Name" - this is the one case where it's expected that
    this virtual "album" might span multiple directories.
 
- The artwork for albums should be contained in gif/jpg/png files stored
  alongside the mp3s/oggs/m4as, or in the immediate parent folder (in the case
  of multi-disc albums, for instance).  Filenames which start with "cover"
  will be preferred over other graphics in the directory.  PNGs will be
  preferred over JPGs, and JPGs will be preferred over GIFs.

  - Artwork thumbnails will be stored directly in Django's database, in
    blatant disregard for Django best practices.  IMO the benefits far
    outweigh the performance concerns, given the scale of data involved.

- Music files should be available directly via HTTP/HTTPS, using the same
  directory structure as the library.  This does not have to be on the same
  port or even server as Django, but the direct download and streaming
  functionality rely on having a direct URL to the files.

- Album zipfile downloads, similarly, require that the zipfile directory be
  accessible directly over the web.  As with the music files, this does not
  need to be on the same port or even server as Django, but Django will not
  serve the zipfile itself.  The reason for this is that I want to be able
  to pass the zipfile URL to other apps for downloading, and for downloads
  to be easily resumable in the event they're accidentally cancelled before
  they're finished.  The text on the download page mentions that zipfiles
  are kept for around 48 hours, but that cleanup is actually not a function
  of Exordium itself.  Instead, I just have a cronjob set on the box like so::

    0 2 * * * /usr/bin/find /var/audio/exordiumzips -type f -name "*.zip" -mtime +2 -print -exec unzip -v {} \; -exec rm {} \;

- Tags for information commonly associated with classical music are
  supported, namely: Group/Ensemble, Conductor, and Composer.  *(For ID3
  tags: TPE2, TPE3, and TCOM, respectively.  In Ogg Vorbis, the more
  sensible ENSEMBLE, CONDUCTOR, and COMPOSER.  M4A files only support
  a flag for Composer.)*  Albums will still be
  defined by their main Artist/Album association, and Artist is
  always a required field, whereas Group/Conductor/Composer are all
  optional.  Internally, these are all stored as "artists," so when
  browsing by artist, Exordium should do the right thing and show you
  all albums containing an artist, whether they showed up as artist,
  composer, conductor, or ensemble.

- There are many live concert recordings in my personal library, which I've
  uniformly tagged with an album name starting with "YYYY.MM.DD - Live".
  Given the volume of these albums, Exordium will automatically consider any
  album matching that name as a "live" album.  *(Dashes and underscores are
  also acceptable inbetween the date components.)*  By default, Exordium
  will hide those live albums from its display, since they otherwise often
  get in the way.  A checkbox is available in the lefthand column to turn
  on live album display, though, and it can be toggled at any time.

- The "addition date" of albums into the library is an important data point;
  Exordium's main view is the twenty most recently-added albums.  To that
  point, updates of the music files will allow the album records to be
  updated while keeping the addition time intact.  Some specific cases in
  which this is ensured:

  - Updating album/artist names in the file's tags
  - Moving music files from one directory to another, or renaming the files

  Combining the two may, however, result in the album being deleted from
  the library and then re-added.  If the tags on a collection of files are
  updated (so that the file's checksum changes), **and** the files are
  moved into a separate directory, the album will end up being re-added,
  since there's no reasonable way to associate the updated files with the
  old ones.

  The most common case of that would be if there was a typo in the album
  or artist name for an album, and that typo was replicated in the directory
  structure containing the files.  Fixing the typo would involve changing
  both the tags and the directory names.  In order to keep the addition time
  intact in this case, you would have to perform both steps separately, running
  an update after each one.

Limitations
-----------

There are some inherent limitations of Exordium, based on the assumptions
that have been made during its development (and in my own music library).

- The artist name "Various" is reserved.  Tracks with an artist tag of
  "Various" will not be added to the library.

- Artist and Trackname tags are required.  Tracks will not be added to
  the library if either of those tags are missing.

- If two Various Artists albums with the same album name exist in the
  library, they'll end up stored as one single album in the DB.

- If two directories contain files which seem to be in the same album (by
  the same artist), you'll end up with an album which spans directories.
  Behavior may not be well-defined in that case.

- Exordium completely ignores genre tags.  I've personally always been
  lousy at putting reasonable values in there on my media, and so that's
  been very unimportant to me.  It'd probably be good to support them
  anyway, though.

- Exordium only supports mp3, ogg, and m4a currently, though other
  support should be reasonably simple to add in, so long as Mutagen
  supports the format.

- m4a tags don't seem to allow for Ensemble or Conductor, so that data
  will never be present for m4a files.  (If support for those tags is
  in there somewhere, I'd like to hear about it.)
