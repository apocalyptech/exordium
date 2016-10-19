.. Requirements file

Requirements
============

Exordium requires at least Python 3.4, and Django 1.10.

Exordium makes use of Django's session handling and user backend
mechanisms, both of which are enabled by default.  This shouldn't
be a problem unless they've purposefully disabled.

Exordium requires the following additional third-party modules:

- mutagen (built on 1.34.1)
- Pillow (built on 3.3.1)
- django-tables2 (built on 1.2.5)
- django-dynamic-preferences (built on 0.8.2), which in turn requires:

  - six (built on 1.10.0)
  - persisting_theory (built on 0.2.1)

These requirements may be installed with ``pip``, if Exordium itself hasn't
been installed that way::

    pip install -r requirements.txt
