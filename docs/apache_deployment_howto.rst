.. Notes on Apache deployments

CentOS 7 Apache/WSGI Deployment HOWTO
=====================================

Exordium is my first application written in Django, and served as
my introduction to Django in general.  This page is more for my own
reference than anyone else's, though perhaps it will come in
useful for someone else with similar requirements who's unfamiliar
with Django.

Requirements
------------

I have a CentOS 7 server which runs Apache and MySQL (well, MariaDB)
which serves a variety of web-based applications (mostly PHP-based),
primarily for my own personal use.  Apache is already set up to handle user
authentication itself, via Apache's native ``Auth*`` configuration
directives, and all my webapps share that common authentication
mechanism.

I have one vhost on SSL which is where the actual webapps live, but
I also have another vhost which uses plain HTTP (and no authentication),
and a subdirectory of that had already been set up in the past to
provide direct access to my music library.  I've always enjoyed having
that in place, because URLs to songs can be constructed which don't
require authentication, can be plugged into .m3u playlists for remote
music listening, and are generally just easier to deal with.  The
directory doesn't have directory indexing enabled, so there's a bit
of obscurity there, though given a link to a single track it wouldn't
be hard to guess my naming conventions and figure out links to other
media.  C'est la vie!

Regardless, there's a couple of differences to a "stock" Django deployment
here, namely that I don't want to use Django's default user authentication
methods, and I'd like to continue to use MariaDB instead of Django's
recommended PostgreSQL.  Fortunately, both are quite easy to configure
in Django.

System Preparation
------------------

The default Python provided by CentOS is still 2.7, and I'd wanted to use
Python 3 for this project.  I used the `IUS Repository <https://ius.io/GettingStarted/>`_
to give me the version I wanted, and used ``python34u`` at the time.  The
full list of packages I installed, after activating IUS, was:

- python34u
- python34u-pip
- python34u-mod_wsgi *(this package was actually only in ius-devel at the time)*
- python34u-devel
- mariadb-devel

The last two packages were required at one point for building the mysql client
library that Python used - it's possible that those aren't required anymore.

Virtenv Creation / Django Installation
--------------------------------------

The next step was to create a virtual environment to hold all the necessary
Django code, and Exordium dependencies.  I chose to put that under a
``/var/www/django`` directory (which is of course not actually inside my
Apache web root).  My initial steps for this were just::

    $ cd /var/www/django
    $ pyvenv-3.4 virtenv
    $ source virtenv/bin/activate
    (virtenv) $ pip install django
    (virtenv) $ pip install mysqlclient

That last step, I believe, is what required the ``python34u-devel`` and ``mariadb-devel``
packages above, since it probably does some actual compilation.

I decided to name my Django project "hex", and created it like so::

    (virtenv) $ pwd
    /var/www/django
    (virtenv) $ django-admin startproject hex

At that point, inside ``/var/www/django`` I had a ``virtenv`` directory
containing a Python virtual environment, and a ``hex`` directory containing
the Django project.

Django Configuration / settings.py
----------------------------------

Here are the relevant values in ``settings.py`` which I'd changed/modified
(I'd also updated ``TIME_ZONE``, ``DEBUG``, etc, but that's irrelevant)::

    ALLOWED_HOSTS = ['servername']

    AUTHENTICATION_BACKENDS = [
        'django.contrib.auth.backends.RemoteUserBackend',
    ]

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': 'hex',
            'USER': 'hex',
            'PASSWORD': 'password',
            'HOST': '127.0.0.1',
            'PORT': '3306',
            'OPTIONS': {
                'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            }
        }
    }

    STATIC_URL = '/hex/static/'
    STATIC_ROOT = '/var/www/django/hex/static'

ALLOWED_HOSTS
    I believe I had to set this, rather than leave it blank, to get Django
    to respond properly via Apache, though I don't actually recall.

AUTHENTICATION_BACKENDS
    This is the section which lets Django use Apache's already-configured
    authentication mechanisms which other apps are using as well.

DATABASES
    Simple MySQL configuration.  The ``OPTIONS`` line lets you avoid some
    warnings which will otherwise pop up while using MySQL in Django.

STATIC_URL and STATIC_ROOT
    Static file configuration for Django.

Once these have been set up, and the necessary database created in MySQL,
Django's basic database models can be created, and we can make sure that
Django recognizes an administrative user.  Apache is handling authentication
in my case, but I still needed to tell Django that "my" user was an
administrator::

    (virtenv) $ cd /var/www/django/hex
    (virtenv) $ python manage.py migrate
    (virtenv) $ python manage.py createsuperuser

Any password given to ``createsuperuser`` won't actually be used in my case,
since ``RemoteUserBackend`` just accepts the information given to it by
Apache about authentication.

At this point, Django functionality can be tested with their test server::

    (virtenv) $ python manage.py runserver 0.0.0.0:8080

WSGI Configuration in Apache
----------------------------

Next up was configuring WSGI/Django inside Apache, so it's accessible via
my existing SSL vhost.  The full config section that I used in the relevant
virtual host, including Django static file configuration, was::

    WSGIDaemonProcess servername socket-timeout=480 processes=1 threads=15 display-name=django python-path=/var/www/django/hex:/var/www/django/virtenv/lib/python3.4/site-packages lang='en_US.UTF-8' locale='en_US.UTF-8'
    WSGIProcessGroup servername
    WSGIScriptAlias /hex /var/www/django/hex/hex/wsgi.py

    Alias /hex/static /var/www/django/hex/static
    <Directory /var/www/django/hex/static>
        Require all granted
    </Directory>

A few notes on some of those options:

socket-timeout
    This is actually just a holdover from before I started using
    ``HttpStreamingResponse`` for the library add/update functions, which
    was causing those pages to take a long time to respond.  Leaving it
    out of the line should be fine since Exordium is pretty responsive
    now.

processes
    I'd originally had this set to ``2``, but as mentioned elsewhere in
    these docs, if you set ``processes`` to a value greater than ``1``, changing
    Exordium's preferences (library paths, zipfile paths, etc) will only
    change the preference effectively in the process it was actually set
    on, which can lead to inconsistency.  I'd like to figure that out
    eventually, but for now I've been happy enough with ``1``.

threads
    Number of threads to use.  Not sure where I got ``15`` from.

python-path
    These are important for ensuring that WSGI is using our virtenv properly.

lang and locale
    By default, WSGI will operate using a ``$LANG`` value of ``C``, which
    causes problems for Exordium if it encounters music files with non-ASCII
    characters in their filenames.  See :doc:`wsgi_deployments` for a bit more
    information, but regardless: just set these to appropriate values for your
    system.

Apache Configuration: mp3/zipfile access
----------------------------------------

Exordium requires that the files in the music library be accessible directly
via a webserver, which I had configured already on a non-SSL Apache vhost.
It also needs a URL for zipfile downloads, if you want album zipfile downloads.
A vhost similar to the following would do the trick::

    <VirtualHost servername:80>
        ServerName servername
        # other common Apache config directives here

        Alias /music /var/audio
        <Directory /var/audio>
            Require all granted
            Options -Indexes
        </Directory>

        Alias /zipfiles /var/www/django/zipfiles
        <Directory /var/www/django/zipfiles>
            Require all granted
            Options -Indexes
        </Directory>

    </VirtualHost>

With that configuration, you'd end up setting the following in Django's settings:

- **Exordium Library Base Path:** ``/var/audio``
- **Exordium Media URL:** ``http://servername/music``
- **Exordium Zip File Generation Path:** ``/var/www/django/zipfiles``
- **Exordium Zip File Retrieval URL:** ``http://servername/zipfiles``

Other Minor Tweaks
------------------

At this point, after an ``apachectl graceful`` Django itself should be
working properly inside the SSL vhost.  Other apps (such as Exordium itself)
can be installed with the virtenv active with simple
``pip install django-exordium`` commands, and following the other instructions
from :doc:`installation`.

One more thing I've done which required some Googling to figure out is that I wanted
Django's base project URL to redirect to Exordium, since Exordium is currently my
only Django app.  My project's ``urls.py`` looks like this, now, to support that::

    from django.conf.urls import include, url
    from django.contrib import admin
    from django.views.generic.base import RedirectView

    urlpatterns = [
        url(r'^/?$', RedirectView.as_view(pattern_name='exordium:index')),
        url(r'^exordium/', include('exordium.urls')),
        url(r'^admin/', admin.site.urls),
    ]
