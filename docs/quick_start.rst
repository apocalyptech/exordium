.. Quick start guide

Quick Start
===========

1. If Exordium hasn't been installed via ``pip`` or some other method which
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
   or bring up your existing server.  Visit the administrative area in
   *Dynamic Preferences > Global preferences* and set the values for the
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

9. If Zipfile downloads are configured, a process should be put into place
   to delete the zipfiles after a period of time.  I personally use a cronjob
   to do this::

      0 2 * * * /usr/bin/find /var/audio/exordiumzips -type f -name "*.zip" -mtime +2 -print -exec unzip -v {} \; -exec rm {} \;

10. Visit the **Library Upkeep** link from the Exordium main page and click on
    "Start Process" to begin the initial import into Exordium!
