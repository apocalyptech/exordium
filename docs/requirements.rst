.. Requirements file

Requirements
============

Exordium requires at least Python 3.4 *(tested in 3.4, 3.5, and 3.6)*,
and Django 1.11 or 2.0.  Has not yet been tested with Django 2.1 or
Python 3.7.

Exordium makes use of Django's session handling and user backend
mechanisms, both of which are enabled by default.  This shouldn't
be a problem unless they've been purposefully disabled.

Exordium requires the following additional third-party modules:

- mutagen (built on 1.39)
- Pillow (built on 4.3.0)
- django-tables2 (built on 1.17.1)

  - the 2.x line of django-tables2 currently doesn't fully work, though
    the problems are entirely cosmetic

- django-dynamic-preferences (built on 1.5), which in turn requires:

  - six (built on 1.11.0)
  - persisting-theory (built on 0.2.1)

These requirements may be installed with ``pip``, if Exordium itself hasn't
been installed via ``pip`` or some other method which automatically
installs dependencies::

    pip install -r requirements.txt
