.. Requirements file

Requirements
============

Exordium requires at least Python 3.8 *(tested on 3.9)*, and Django 4.0.

Exordium makes use of Django's session handling and user backend
mechanisms, both of which are enabled by default.  This shouldn't
be a problem unless they've been purposefully disabled.

Exordium requires the following additional third-party modules:

- mutagen (built on 1.45)
- Pillow (built on 9.0)
- django-tables2 (built on 2.4)
- django-dynamic-preferences (built on 1.11), which in turn requires:

  - six (built on 1.16.0)
  - persisting-theory (built on 0.2.1)

One unit test module additionally requires django-test-migrations (tested
with 1.2.0), but that's not required to run it.

These requirements may be installed with ``pip``, if Exordium itself hasn't
been installed via ``pip`` or some other method which automatically
installs dependencies::

    pip install -r requirements.txt
