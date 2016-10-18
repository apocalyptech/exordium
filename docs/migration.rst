.. Migration docs

Migration from Other Libraries
==============================

Practically no support is included for converting an existing music library
database in some other app to Exordium.  There IS one administrative
subcommand provided to import album addition times from an Ampache MySQL
database, though, which can be accessed by running::

    python manage.py importmysqlampachedates --dbhost <host> --dbname <name> --dbuser <user>

The subcommand will prompt you for the database password via STDIN.  Note
that this has only been tested with Ampache 3.7.0.
