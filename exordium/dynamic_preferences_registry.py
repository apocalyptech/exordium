#!/usr/bin/env python
# vim: set expandtab tabstop=4 shiftwidth=4:

from dynamic_preferences.types import StringPreference, BooleanPreference, Section
from dynamic_preferences.registries import global_preferences_registry
from dynamic_preferences.users.registries import user_preferences_registry

exordium = Section('exordium')

@global_preferences_registry.register
class LibraryPath(StringPreference):
    section = exordium
    name = 'base_path'
    default = '/var/audio'
    verbose_name = 'Exordium Library Base Path'
    help_text = 'Where on the filesystem can music files be found?'

@global_preferences_registry.register
class LibraryUrlHTML5(StringPreference):
    section = exordium
    name = 'media_url_html5'
    default = 'http://localhost/media'
    verbose_name = 'Exordium Media URL for HTML5'
    help_text = 'What is a direct URL to the media directory, for HTML5 streaming?'

@global_preferences_registry.register
class LibraryUrlM3U(StringPreference):
    section = exordium
    name = 'media_url_m3u'
    default = 'http://localhost/media'
    verbose_name = 'Exordium Media URL for m3u'
    help_text = 'What is a direct URL to the media directory, for m3u playlists?'

@global_preferences_registry.register
class ZipfileCreationPath(StringPreference):
    section = exordium
    name = 'zipfile_path'
    default = ''
    verbose_name = 'Exordium Zip File Generation Path'
    help_text = 'Where on the filesystem can we write zipfiles?'

@global_preferences_registry.register
class ZipfileUrl(StringPreference):
    section = exordium
    name = 'zipfile_url'
    default = ''
    verbose_name = 'Exordium Zip File Retrieval URL'
    help_text = 'What is a direct URL to where zipfiles can be found?'

@user_preferences_registry.register
class ShowLiveRecordings(BooleanPreference):
    section = exordium
    name = 'show_live'
    default = False
    verbose_name = 'Show Live Recordings'
    help_text = 'Do we show live recordings in album lists?'

