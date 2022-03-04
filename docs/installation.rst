.. Installation

Installation
============

These instructions assume that you already have a Django project up and
running.  For instructions on setting up Django for the first time, if
installing a brand new application server just for a web music library
doesn't deter you, djangoproject.com has some good documentation:

- https://docs.djangoproject.com/en/4.0/intro/install/
- https://docs.djangoproject.com/en/4.0/intro/tutorial01/

Once Django is installed and running:

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
         'dynamic_preferences.users.apps.UserPreferencesConfig',
     ]

3. *(Optional)* For jPlayer streaming to work properly on a "live"
   install, the `Cross-Origin-Opener-Policy <https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Cross-Origin-Opener-Policy>`_
   HTTP header has to be set properly.  (This will generally not
   be an issue when running Django in "test" mode via ``runserver``.)
   Django defaults to using ``same-origin``, but unless your static
   content delivery also uses the same header, launching the streaming
   window will fail.  You can set the header to ``same-origin-allow-popups``
   inside ``settings.py`` to make this work, or ensure that your static
   files set the proper header.  (Making sure static files use
   ``Cross-Origin-Opener-Policy: same-origin`` just like Django will
   do the trick.)  Setting the Django default can be done with::

    SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin-allow-popups'

   If your static content isn't served from the same protocol/hostname/port
   as Django itself, you will likely have to set either Django or your
   static files' value to ``unsafe-none`` instead.

4. Include the exordium URLconf in your project ``urls.py`` like this::

     path('exordium/', include('exordium.urls')),
   
5. Run ``python manage.py migrate dynamic_preferences`` to create the
   Dynamic Preferences models, if this wasn't already configured on your
   Django install.

6. Run ``python manage.py migrate exordium`` to create the Exordium models.

7. Run ``python manage.py loaddata --app exordium initial_data`` to load
   some initial data into the database.  *(This is not actually strictly
   speaking necessary - the app will create the necessary data
   automatically if it's not found.)*

8. If running this from a "real" webserver, ensure that it's configured
   to serve Django static files. Then run ``python manage.py collectstatic``
   to get Exordium's static files in place.  If you didn't want to set
   ``same-origin-allow-popups`` for Django's COOP header, make sure that
   your server sends a ``Cross-Origin-Opener-Policy: same-origin`` header
   along with these static files, or possibly ``unsafe-none`` if the
   static files protocol/hostname/port doesn't match Django's.

9. Either start the development server with ``python manage.py runserver``
   or bring up your existing server.  Also ensure that you have a webserver
   configured to allow access directly to your music library files, and 
   optionally to the zipfile downloads Exordium will create.
   
10. Visit the administrative area in *Dynamic Preferences > Global preferences*
    and set the values for the following:

    - **Exordium Library Base Path**: This is what defines where your music
      library can be found on disk.
    - **Exordium Media URL for HTML5**: This is the base URL which provides
      direct access to the files in your library, used by the HTML streaming
      player.  Omit the trailing slash, though things will probably work fine
      even if it's in there.  Without this set properly, the streaming
      player will not work properly.  Note that if your base URL for Exordium
      is https, this will have to be https as well, to avoid browser errors.
    - **Exordium Media URL for m3u**: This is the base URL which provides
      direct access to the files in your library, used by the m3u Playlist
      functionality, and also the direct song download links when enumerating
      tracks.  This can be the same as the HTML5 URL.  Omit the slash, though
      things will probably work fine even if it's in there.  Without this set
      properly, m3u playlists and direct track downloads will not work
      properly.  This URL can be http even if the main site is https.
    - **Exordium Zip File Generation Path**: Path on the filesystem to store
      zipfile album downloads.  This is the one location in which the user
      running Django needs write access.
    - **Exordium Zip File Retrieval URL**: This is the base URL providing
      web access to that zipfile directory.  Note that if your base URL for
      Exordium is https, this will have to be https as well, to avoid
      browser errors.

    Without the last two options, Exordium will still function fine, but the
    album-download button will not be rendered.  Exordium will also function
    without the "*Exordium Media URL*" options being set properly, though
    with the caveats mentioned above.

11. If Zipfile downloads are configured, a process should be put into place
    to delete the zipfiles after a period of time.  I personally use a cronjob
    to do this::

      0 2 * * * /usr/bin/find /var/audio/exordiumzips -type f -name "*.zip" -mtime +2 -print -exec unzip -v {} \; -exec rm {} \;

12. Visit the **Library Upkeep** link from the Exordium main page and click on
    "Start Process" to begin the initial import into Exordium!
