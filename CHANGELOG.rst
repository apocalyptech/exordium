1.3.2 (2018-09-20)
------------------

**Bugfixes/Tweaks**

- Stupid little formatting fix in README and docs requirements RST

1.3.1 (2018-09-20)
------------------

**Bugfixes/Tweaks**

- Use a label for our "live album" checkbox so the text can be clicked
  in addition to the checkbox itself
- Disallow django-tables2 >= 2.0 until an issue with that has been either
  fixed or denied: https://github.com/jieter/django-tables2/issues/621
  (we can work around, if they opt not to merge that fix, but I'd prefer
  to use the fix on that Issue)

1.3.0 (2018-01-02)
------------------

**Bugfixes/Tweaks**

- Updates to work properly with Django 2.0
- Use time-added as secondary sorting for albums when sorting by Year

1.2.1 (2017-11-28)
------------------

**Bugfixes/Tweaks**

- Updates to documentation, to have ``django-dynamic-preferences``
  properly configured.

1.2.0 (2017-11-28)
------------------

**Bugfixes/Tweaks**

- Updates to work properly with Django 1.11 and
  ``django-dynamic-preferences`` >= 1.0
- Fixed live recording checkbox when not logged in to Django

1.1.1 (2016-12-30)
------------------

**Bugfixes/Tweaks**

- Fixed the release date in the Changelog.  Bah.

1.1.0 (2016-12-30)
------------------

**New Features**

- Added support for M4A audio files

**Bugfixes/Tweaks**

- Added a few more "normalization" characters, for easy searching
  from the web UI and correct association across possibly-
  inconsistent tags.  Specifically: İ, ğ, and ş.  Also fixed
  normalizing filenames (for zipfile downloads) for capital Ç.
- Fixed album summary information when some tracks have classical
  music tags (ensemble, composer, conductor) but other tracks
  don't.  (Explicitly say that not all tracks have the tags.)
- Change the display order of a few elements on the album download
  page, and use an HTML ``<meta>`` tag to automatically queue up
  the download, rather than only having the direct link.
- Override table footers to always include item counts, as was
  present in ``django-tables2`` 1.2.6 but patched out in 1.2.7.
- Use newlines when reporting multiple artists in tables, to keep
  the table width down as much as possible.

1.0.3 (2016-11-22)
------------------

**Bugfixes/Tweaks**

- Fixed admin area to allow blank album art, song, and
  artist fields, where the fields shouldn't be required

1.0.2 (2016-10-21)
------------------

**Bugfixes/Tweaks**

- Fixed packaging manifest to include changelog, and exclude
  rendered HTML documentation (the latter was causing the source
  archive to be twice as large as it should be)

1.0.1 (2016-10-21)
------------------

**Bugfixes/Tweaks**

- Added a "login" link in the sidebar for not-logged-in users
- Fixes for tests which were failing when run against databases
  other than MySQL/MariaDB.  Actual app functionality appears to
  be fine, just a problem with the test suite.

  - Case-related tests
  - Album Art tests

- Tweaked/reworked some documentation
- Set ``setup.py`` development classifier to Production
- Reordered a few fields on the admin screens

1.0.0 (2016-10-18)
------------------

- Initial Release
