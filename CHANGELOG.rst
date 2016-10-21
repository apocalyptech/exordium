1.0.2 (2016-10-21)
------------------

- Fixed packaging manifest to include changelog, and exclude
  rendered HTML documentation (the latter was causing the source
  archive to be twice as large as it should be)

1.0.1 (2016-10-21)
------------------

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
