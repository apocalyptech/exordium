.. Apache/WSGI Deployment Issues

Apache/WSGI Deployment Issues
=============================

Locale Issues
-------------

If deploying via Apache/WSGI, there's a serious problem
which can occur if any non-ASCII characters are found in your filenames.
Basically, by default the WSGI process will be launched with a ``$LANG`` of
``C``, making ascii the default encoding for various things, including the
filesystem encoding as reported by ``sys.getfilesystemencoding()``.  If you
try and import any files with non-ASCII characters in the filename, you can
end up with absurd errors like this in your logs::

    UnicodeEncodeError: 'utf-8' codec can't encode character '\\udcc3' in position 7160: surrogates not allowed

This behavior is especially difficult to track down since it will NOT
be repeatable in any unit tests, nor will it be repeatable when running
the development test server - it'll only ever show up in the WSGI
deployment.

Currently Exordium doesn't have a check for this - I'll hope to
eventually add that in - but for now just make sure that you're specifying
the following after your ``WSGIDaemonProcess`` line::

    lang='en_US.UTF-8' locale='en_US.UTF-8'

Of course, replacing the encoding with the proper one for the data stored
on your filesystem.

There may be some similar problems if more than one encoding is found in
your system's filenames - that's another thing I have yet to investigate.

You can read a bit more on this problem here, FWIW:
http://blog.dscpl.com.au/2014/09/setting-lang-and-lcall-when-using.html

Process Count
-------------

The ``WSGIDaemonProcess`` parameter in Apache lets you specify an arbitrary
number of ``processes`` (in addition to ``threads``).  If ``processes`` is
set to more than ``1``, problems can be encountered when setting preferences
(such as library path, download URLs, live album display, etc).  Namely,
the preference change will often only be seen by the process in which it
was changed, which can lead to some vexing behavior.

I believe the root of this problem is that the dynamic_preferences module
probably uses a cache (presumably a builtin Django cache), and that cache must
be configured properly so that multiple processes can share it.  I have not
actually investigated this, though.  Given that my personal activity needs
with Exordium are quite light, I've just made do with a single process.
