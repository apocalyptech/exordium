========
Exordium
========

**NOTE:** Exordium is currently a work-in-progress and isn't actually
functional in all but the most basic sense.  As of this writing,
you should be able to import/update your library and download
individual tracks, but that's about it.  Missing functionality
includes album art, whole-album downloads, streaming, ogg support,
and probably many other things mentioned later on in this document.
In other words, this is probably NOT for you, yet, and is just on
github for my own purposes.  Proceed at your own risk!

Exordium is a web-based music library system for Django.  Exordium
will read mp3 and ogg files from the host filesystem and provide
an online interface to browse, download (as zipfiles or otherwise),
and stream.

Detailed documentation may eventually show up in the "docs"
directory.

Exordium makes various assumptions:

- Your music files are accessible via the local filesystem on
  which Django is running, and stored as either mp3 or ogg.
- Your music files are stored within a single directory.  If
  subdirs of this root dir span multiple volumes (or network
  mounts), that's fine, but there is NO support for multiple
  libraries in Exordium.
- You manage your library directories manually, or via some other
  means.  Exordium will never attempt to write to your library
  directory for any reason.  It requires read access only.
- Your music files are, in general, arranged scrupulously: All
  files within a single directory belong to the same album, and
  an album will never span multiple directories.  There's actually
  plenty of wiggle room here, and Exordium should correctly deal
  with directories full of "miscellaneous" files, but in general
  your music library dir should be well-ordered.
- The artwork for your albums are contained in gif/jpg/png
  files stored alongside the mp3s/oggs, or in folders "above"
  the files (in the case of multi-disc albums, for instance)
- Django will store your album artwork in the database, rather than
  on the filesystem as is more customary with Django applications.
  I believe the benefits of being able to trivially manage multiply-
  resized images of an album cover related to an album far outweigh
  the performance hits incurred by keeping them in the db.
- Your music files are available via direct HTTP/HTTPS, using the
  same directory structure as on your disk (though not necessarily
  on the same vhost/port/etc that Django is running on)

I took the name Exordium from the fictional technology of the same
name in Alastair Reynolds' "Revelation Space" novels.  It's not a
perfect name for the app, given that the Revelation Space Exordium
would make a pretty lousy music library, but at least there's some
element of data storage and retrieval.  Exordium the web-based
music library is only capable of retrieving music which has been
imported to it in the past, unfortunately.  I'll be sure to contact
all the major news organizations if I figure out a way to get it
to retrieve music stored in the future.

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

The tests in `test.py` make use of the `exist_ok` parameter to Python's
`os.makedirs()`, which was not introduced until Python 3.2, so the
tests at least currently require at least Python 3.2.

A Note for WSGI Deployments
---------------------------

If deploying via WSGI, there's a serious problem which can occur if any
non-ASCII characters are found in your filenames.  Basically, by default
the WSGI process will be launched with a $LANG of "C", making ascii
the default encoding for various things, including the filesystem encoding
as reported by `sys.getfilesystemencoding()`.  If you try and import
any files with non-ASCII characters in the filename, you can end up with
absurd errors like this in your logs:

    UnicodeEncodeError: 'utf-8' codec can't encode character '\\udcc3' in position 7160: surrogates not allowed

This behavior is especially difficult to track down since it will NOT
be repeatable in any unit tests, nor will it be repeatable when running
the development test server - it'll only ever show up in the WSGI
deployment.

Currently Exordium doesn't have a check for this - I'll hope to
eventually add that in - but for now just make sure that you're specifying
the following after your WSGIDaemonProcess line:

    lang='en_US.UTF-8' locale='en_US.UTF-8'

Of course, replacing the encoding with the proper one for the data stored
on your filesystem.

There may be some similar problems if more than one encoding is found in
your system's filenames - that's another thing I have yet to investigate.

You can read a bit more on this problem here, FWIW:
http://blog.dscpl.com.au/2014/09/setting-lang-and-lcall-when-using.html

Quick start
-----------

1. Add exordium, django_tables2, and dynamic_preferences to your
   INSTALLED_APPS setting like this::

   INSTALLED_APPS = [
       ...
       'exordium',
       'django_tables2',
       'dynamic_preferences',
   ]

2. Include the exordium URLconf in your project urls.py like this::

   url(r'^exordium', include('exordium.urls')),

3. Run `python manage.py migrate exordium` to create the Exordium models.
   
4. Run `python manage.py migrate dynamic_preferences` to create the
   Dynamic Preferences models, if this wasn't already configured on your
   Django install.

5. Run `python manage.py loaddata --app exordium initial_data` to load
   some initial data into the database.  (This is not actually strictly
   speaking necessary.)

6. If running this from a webserver with static files present, make sure
   to run `python manage.py collectstatic` at some point to get the
   static files put in place properly, or otherwise configure your static
   file delivery solution.

7. Either start the development server with `python manage.py runserver`
   or bring up your existing server.  Visit the administrative area in
   "Dynamic Preferences > Global preferences" and set the values for
   "Exordium Library Base Path" and "Exordium Media URL".

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

Migrations
----------

Practically no support is included for converting an existing music library
database in some other app to Exordium.  There IS one administrative
subcommand provided to import album addition times from an Ampache MySQL
database, though, which can be accessed by running:

    python manage.py importmysqlampachedates --dbhost <host> --dbname <name> --dbuser <user>

The subcommand will prompt you for the database password via STDIN.  Note
that this has only been tested with Ampache 3.7.0.
