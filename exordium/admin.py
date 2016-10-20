from django.contrib import admin
from django.http import HttpResponseRedirect

from .models import Artist, Album, Song, AlbumArt

class SongInline(admin.TabularInline):
    model = Song
    list_display = ()
    fields = ('tracknum', 'artist', 'title')
    readonly_fields = ('tracknum', 'artist', 'title')
    extra = 0
    ordering = ['tracknum']
    show_change_link = True
    can_delete = True

    # Purposefully not testing this 'cause I'm not sure how,
    # and the admin functionality is secondary at best
    def has_add_permission(self, request):  # pragma: no cover
        return False

class AlbumInline(admin.TabularInline):
    model = Album
    list_display = ()
    fields = ('name', 'year', 'live', 'has_album_art', 'time_added')
    readonly_fields = ('name', 'year', 'live', 'has_album_art', 'time_added')
    extra = 0
    ordering = ['name']
    show_change_link = True
    can_delete = True

    # Purposefully not testing this 'cause I'm not sure how,
    # and the admin functionality is secondary at best
    def has_add_permission(self, request):  # pragma: no cover
        return False

class AlbumArtInline(admin.TabularInline):
    model = AlbumArt
    list_display = ()
    fields = ('size', 'resolution')
    readonly_fields = ('size', 'resolution')
    extra = 0
    ordering = ['size']
    show_change_link = True
    can_delete = True

    # Purposefully not testing this 'cause I'm not sure how,
    # and the admin functionality is secondary at best
    def has_add_permission(self, request):  # pragma: no cover
        return False

class ArtistAdmin(admin.ModelAdmin):
    search_fields = ['name', 'normname']
    inlines = [AlbumInline]

class AlbumAdmin(admin.ModelAdmin):
    fieldsets = [
        ('Basic Information', {'fields':
            ['artist', 'name', 'normname', 'year',
            'miscellaneous', 'live']}),
        ('Date Information', {'fields': ['time_added']}),
        ('Album Art Information', {'fields':
            ['art_filename', 'art_ext', 'art_mime',
            'art_mtime']}),
    ]
    inlines = [SongInline, AlbumArtInline]
    list_display = ('artist', 'name', 'year', 'has_album_art', 'time_added')
    search_fields = ['name', 'normname', 'artist__name', 'artist__normname']

class SongAdmin(admin.ModelAdmin):
    fieldsets = [
        ('Regular Tag Information', {'fields':
            ['artist', 'album', 'title', 'normtitle',
            'year', 'tracknum']}),
        ('Classical Tag Information', {'fields':
            ['group', 'composer', 'conductor']}),
        ('Raw Artist Tag Information', {'fields':
            ['raw_artist', 'raw_group', 'raw_composer', 'raw_conductor'],
            'classes': ['collapse']}),
        ('Technical Information', {'fields':
            ['filename', 'filetype', 'bitrate', 'mode', 'size', 'length',
            'sha256sum']}),
        ('Date Information', {'fields': ['time_added', 'time_updated']}),
    ]
    list_display = ('artist', 'album', 'title', 'year')
    search_fields = ['title']

class AlbumArtAdmin(admin.ModelAdmin):
    list_display = ('get_artist', 'album', 'size', 'resolution')

    # Purposefully not testing this 'cause I'm not sure how,
    # and the admin functionality is secondary at best
    def has_add_permission(self, request):  # pragma: no cover
        return False

admin.site.register(Artist, ArtistAdmin)
admin.site.register(Album, AlbumAdmin)
admin.site.register(Song, SongAdmin)
admin.site.register(AlbumArt, AlbumArtAdmin)
