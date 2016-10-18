.. Requirements file

Requirements
============

Exordium is only currently tested on Python 3.4 and Django 1.10.
Exordium makes use of Django's session handling (enabled by default
in Django), so session support must be enabled in Django.  A user
backend must exist as well.

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

The tests in ``test.py`` make use of the ``exist_ok`` parameter to Python's
``os.makedirs()``, which was not introduced until Python 3.2, so the
tests at least currently require at least Python 3.2.  I suspect that there
may be one or two other functions in use which might cause the base
required Python to be 3.4, but I have yet to investigate closely.
