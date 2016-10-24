========
Exordium
========

Exordium is a read-only web-based music library system for Django.
Exordium will read mp3 and ogg files from the host filesystem and provide
an online interface to browse, download (as zipfiles or otherwise), and
stream.

The HTML5 media player `jPlayer <http://jplayer.org/>`_ is used to provide
arbitrary streaming of music.

Exordium was built with a very specific set of operational goals and does
not attempt to be a generic library suitable for widespread use.  There are,
in fact, no configuration options beyond those to define the file paths/URLs
necessary for basic usage.  Patches to add/change functionality will be
happily received so long as they don't interfere with or disable the current
functionality by default, but there is no internal development goal to make
Exordium a generic solution.

Detailed information about what Exordium expects from your library, and its
assumptions and limitations, can be found either in the ``docs/`` directory,
`Exordium's Website <http://apocalyptech.com/exordium>`_, or
`exordium.readthedocs.io <http://exordium.readthedocs.io/>`_.  It's
highly recommended to at least glance through these to get a feel for how
Exordium will function.

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

Exordium requires at least Python 3.4 *(tested in 3.4 and 3.5)*,
and Django 1.10.

Exordium requires the following additional third-party modules:

- mutagen (built on 1.34.1)
- Pillow (built on 3.3.1)
- django-tables2 (built on 1.2.5)
- django-dynamic-preferences (built on 0.8.2), which in turn requires:

  - six (built on 1.10.0)
  - persisting_theory (built on 0.2.1)

Getting Exordium
----------------

Exordium is available to install on PyPI via ``pip install django-exordium``.
PyPI also hosts Python packages for Exordium in both source and
`Wheel <https://pypi.python.org/pypi/wheel>`_ formats, at 
https://pypi.python.org/pypi/django-exordium/.  Source and Wheel downloads
of all released versions can also be found at Exordium's hompeage at
http://apocalyptech.com/exordium/.

Exordium sourcecode is hosted at `GitHub <https://github.com/apocalyptech/exordium/>`_,
and sourcecode archives of released versions can be found there at
https://github.com/apocalyptech/exordium/releases

Installation
------------

These instructions assume that you already have a Django project up and
running.

1. Install Exordium via ``pip install django-exordium``

   - If Exordium hasn't been installed via ``pip`` or some other method which
     automatically installs dependencies, install its dependencies::

        pip install -r requirements.txt

2. Add exordium, django_tables2, and dynamic_preferences to your
   ``INSTALLED_APPS`` setting like this::

     INSTALLED_APPS = [
         ...
         'exordium',
         'django_tables2',
         'dynamic_preferences',
     ]

3. Include the exordium URLconf in your project ``urls.py`` like this::

     url(r'^exordium/', include('exordium.urls')),

4. Run ``python manage.py migrate exordium`` to create the Exordium models.
   
5. Run ``python manage.py migrate dynamic_preferences`` to create the
   Dynamic Preferences models, if this wasn't already configured on your
   Django install.

6. Run ``python manage.py loaddata --app exordium initial_data`` to load
   some initial data into the database.  *(This is not actually strictly
   speaking necessary - the app will create the necessary data
   automatically if it's not found.)*

7. If running this from a "real" webserver, ensure that it's configured
   to serve Django static files. Then run ``python manage.py collectstatic``
   to get Exordium's static files in place.

8. Either start the development server with ``python manage.py runserver``
   or bring up your existing server.  Also ensure that you have a webserver
   configured to allow access directly to your music library files, and 
   optionally to the zipfile downloads Exordium will create.
   
9. Visit the administrative area in *Dynamic Preferences > Global preferences*
   and set the values for the following:

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

10. If Zipfile downloads are configured, a process should be put into place
    to delete the zipfiles after a period of time.  I personally use a cronjob
    to do this::

      0 2 * * * /usr/bin/find /var/audio/exordiumzips -type f -name "*.zip" -mtime +2 -print -exec unzip -v {} \; -exec rm {} \;

11. Visit the **Library Upkeep** link from the Exordium main page and click on
    "Start Process" to begin the initial import into Exordium!
