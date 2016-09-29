========
Exordium
========

**NOTE:** Exordium is currently a work-in-progress and may exhibit strange
behavior or otherwise be non-feature-complete.  Proceed at your own risk!
That said, it's working quite well for me.

Exordium is a read-only web-based music library system for Django.
Exordium will read mp3 and ogg files from the host filesystem and provide
an online interface to browse, download (as zipfiles or otherwise), and
stream.

The HTML5 media player `jPlayer <http://jplayer.org/>`_ is used to provide
arbitrary streaming of music.

Detailed documentation may eventually show up in the "docs" directory.

The name "Exordium" comes from the fictional technology of the same name in
Alastair Reynolds' "Revelation Space" novels.  It's not a perfect name for
the app, given that the Revelation Space *Exordium* would make a pretty
lousy music library, but at least there's some element of data storage and
retrieval.  Exordium the *web-based music library*, as opposed to its
fictional counterpart, is only capable of retrieving music which has been
imported to it in the past.  I'll be sure to contact all the major news
organizations if I figure out a way to get it to retrieve music stored in the
future.

Requirements
------------

Exordium is only currently tested on Python 3.4 and Django 1.10.

Exordium requires the following additional third-party modules:

- mutagen (built on 1.34.1)
- Pillow (built on 3.3.1)
- django-tables2 (built on 1.2.5)
- django-dynamic-preferences (built on 0.8.2), which in turn requires:
  - six (built on 1.10.0)
  - persisting_theory (built on 0.2.1)

The tests in ``test.py`` make use of the ``exist_ok`` parameter to Python's
``os.makedirs()``, which was not introduced until Python 3.2, so the
tests at least currently require at least Python 3.2.  I suspect that there
may be one or two other functions in use which might cause the base
required Python to be 3.4, but I have yet to investigate closely.

Detailed Operation
------------------

Exordium is designed with several assumptions and peculiarities in mind,
which fit my ideal very well but may not be a good fit for you:

- Except for the Javascript necessary to hook into jPlayer, all content is
  generated server-side.  There is no other Javascript, and the application is
  quite usable from text-based browsers.

- Music files must be accessible via the local filesystem on which Django
  is running, and stored as either mp3 or ogg vorbis.

- The entire music library must be available from a single directory
  prefix.  If subdirs of this root dir span multiple volumes (or network
  mounts), that's fine, but there is NO support for multiple libraries in
  Exordium.

- All music files are managed outside of Exordium.  Exordium itself
  will never attempt to write to your library directory for any reason.  It
  requires read access only.  (Write access to a directory on the
  filesystem is required for zipfile downloads, but that directory need not
  be in your music library.)

- Music files should be, in general, arranged scrupulously: All files
  within a single directory belong to the same album, and an album should
  never span multiple directories.  There's actually plenty of wiggle room
  here, and Exordium should correctly deal with directories full of
  "miscellaneous" files, etc, but in general the library should be
  well-ordered and have albums contained in their own directories.
 
- The artwork for albums should be contained in gif/jpg/png files stored
  alongside the mp3s/oggs, or in the immediate parent folder (in the case
  of multi-disc albums, for instance).  Filenames which start with "cover"
  will be preferred over other graphics in the directory.

- Artwork thumbnails will be stored directly in Django's database, in
  blatant disregard for Django best practices.  IMO the benefits far
  outweigh the performance concerns, given the scale of data involved.

- Music files should be available directly via HTTP/HTTPS, using the same
  directory structure as the library.  This does not have to be on the same
  port or even server as Django, but the direct download and streaming
  functionality rely on having a direct URL to the files.  Album downloads
  via zipfiles will still work even if this is not the case.

- Album zipfile downloads, similarly, require that the zipfile directory be
  accessible directly over the web.  As with the music files, this does not
  need to be on the same port or even server as Django, but Django will not
  serve the zipfile itself.  The reason for this is that I want zipfile
  downloads to be easily resumable in the event they're accidentally
  cancelled before they're finished.  The text on the download page
  mentions that zipfiles are kept for around 48 hours, but that cleanup is
  actually not a function of Exordium itself.  Instead, I just have a
  cronjob set on the box like so::

    0 2 * * * /usr/bin/find /var/audio/exordiumzips -type f -name "*.zip" -mtime +2 -print -exec unzip -v {} \; -exec rm {} \;

- Tracks without an album will be sorted into a "virtual" album entitled
  "Non-Album Tracks: Band Name"

- Tags for information commonly associated with classical music are
  supported, namely: Group/Ensemble, Conductor, and Composer.  (For ID3
  tags: TPE2, TPE3, and TCOM, respectively.  In Ogg Vorbis, the more
  sensible ENSEMBLE, CONDUCTOR, and COMPOSER.)  Albums will still be
  defined by their main Artist/Album association, though, and Artist is
  always a required field, whereas Group/Conductor/Composer are all
  optional.  Internally, these are all stored as "artists," and Exordium
  should do the right thing and show you all albums containing an artist,
  whether they showed up as an Artist or as an Ensemble, for instance.

- There are many live concert recordings in my personal library, which I've
  uniformly tagged with an album name starting with "YYYY.MM.DD - Live".
  Given the volume of these albums, Exordium will automatically tag any
  album matching that name as a "live" album.  (Dashes and underscores are
  also acceptable inbetween the date components.)  By default, Exordium
  will hide those live albums from its display, since they otherwise often
  get in the way.  A checkbox is available in the lefthand column to turn
  on live album display, though, and it can be toggled at any time.

WSGI Deployments on Apache: Locale Issues
-----------------------------------------

If deploying via WSGI (on Apache, at least), there's a serious problem
which can occur if any non-ASCII characters are found in your filenames.
Basically, by default the WSGI process will be launched with a $LANG of
"C", making ascii the default encoding for various things, including the
filesystem encoding as reported by ``sys.getfilesystemencoding()``.  If you
try and import any files with non-ASCII characters in the filename, you can
end up with absurd errors like this in your logs::

    UnicodeEncodeError: 'utf-8' codec can't encode character '\\udcc3' in position 7160: surrogates not allowed

This behavior is especially difficult to track down since it will NOT
be repeatable in any unit tests, nor will it be repeatable when running
the development test server - it'll only ever show up in the WSGI
deployment.

Currently Exordium doesn't have a check for this - I'll hope to
eventually add that in - but for now just make sure that you're specifying
the following after your ``WSGIDaemonProcess`` line::

    lang='en_US.UTF-8' locale='en_US.UTF-8'

Of course, replacing the encoding with the proper one for the data stored
on your filesystem.

There may be some similar problems if more than one encoding is found in
your system's filenames - that's another thing I have yet to investigate.

You can read a bit more on this problem here, FWIW:
http://blog.dscpl.com.au/2014/09/setting-lang-and-lcall-when-using.html

WSGI Deployments on Apache: Process Count
-----------------------------------------

The ``WSGIDaemonProcess`` parameter in Apache lets you specify an arbitrary
number of ``processes`` (in addition to ``threads``).  If ``processes`` is
set to more than 1, problems can be encountered when setting preferences
(such as library path, download URLs, live album display, etc).  Namely,
the preference change will often only be seen by the process in which it
was changed, which can lead to some vexing behavior.

I believe the root of this problem is that the dynamic_preferences module
uses a cache (presumably a builtin Django cache), and that cache must be
configured properly so that multiple processes can share it, but I have not
actually investigated this.  Given that my personal activity needs with
Exordium are quite light, I've just made do with a single process.

Quick start
-----------

1. Add exordium, django_tables2, and dynamic_preferences to your
   ``INSTALLED_APPS`` setting like this::

     INSTALLED_APPS = [
         ...
         'exordium',
         'django_tables2',
         'dynamic_preferences',
     ]

2. Include the exordium URLconf in your project ``urls.py`` like this::

     url(r'^exordium', include('exordium.urls')),

3. Run ``python manage.py migrate exordium`` to create the Exordium models.
   
4. Run ``python manage.py migrate dynamic_preferences`` to create the
   Dynamic Preferences models, if this wasn't already configured on your
   Django install.

5. Run ``python manage.py loaddata --app exordium initial_data`` to load
   some initial data into the database.  (This is not actually strictly
   speaking necessary.)

6. If running this from a webserver with static files present, make sure
   to run ``python manage.py collectstatic`` at some point to get the
   static files put in place properly, or otherwise configure your static
   file delivery solution.

7. Either start the development server with ``python manage.py runserver``
   or bring up your existing server.  Visit the administrative area in
   "Dynamic Preferences > Global preferences" and set the values for the
   following:

   - **Exordium Library Base Path**: This is what defines where your music
     library can be found on disk.
   - **Exordium Media URL**: This is the base URL which provides direct
     access to the files in your library.  Omit the trailing slash, though
     things will probably work fine even if it's in there.  Without this
     set properly, song download links will be broken and the streaming
     player will not work properly.
   - **Exordium Zip File Generation Path**: Path on the filesystem to store
     zipfile album downloads.  This is the one location in which the user
     running Django needs write access.
   - **Exordium Zip File Retrieval URL**: This is the base URL providing
     web access to that zipfile directory.

   Without the last two options, Exordium will still function fine, but the
   album-download button will not be rendered.  Exordium will also function
   without the "*Exordium Media URL*" option being set properly, though
   with the caveats mentioned above.

8. Visit the "Library Upkeep" link from the Exordium main page and click on
   "Add new music" to beginn the initial import into Exordium!

Limitations
-----------

There are some inherent limitations of Exordium, based on the assumptions
that have been made during its development (and in my own music library).
As I think of them I'll add to the list.

- The artist name "Various" is effectively reserved, or at least if there
  is a band named Various, they'll get lumped in with all the other
  Various Artists albums.

- If two Various Artists albums with the same title exist in the library,
  they'll end up stored as one single album in the DB.

- If two directories contain files which seem to be in the same album,
  you'll end up with an album which spans directories.  Behavior may not
  be well-defined in that case.

Migration from Other Libraries
------------------------------

Practically no support is included for converting an existing music library
database in some other app to Exordium.  There IS one administrative
subcommand provided to import album addition times from an Ampache MySQL
database, though, which can be accessed by running::

    python manage.py importmysqlampachedates --dbhost <host> --dbname <name> --dbuser <user>

The subcommand will prompt you for the database password via STDIN.  Note
that this has only been tested with Ampache 3.7.0.
