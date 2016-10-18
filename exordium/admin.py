from django.contrib import admin
from django.http import HttpResponseRedirect

from .models import Artist, Album, Song

class SongInline(admin.TabularInline):
    model = Song
    list_display = ()
    fields = ('tracknum', 'artist', 'title')
    readonly_fields = ('tracknum', 'artist', 'title')
    extra = 0
    ordering = ['tracknum']
    show_change_link = True
    can_delete = True

    def has_add_permission(self, request):
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

    def has_add_permission(self, request):
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
    inlines = [SongInline]
    list_display = ('artist', 'name', 'year', 'has_album_art', 'time_added')
    search_fields = ['name', 'normname', 'artist__name', 'artist__normname']

admin.site.register(Artist, ArtistAdmin)
admin.site.register(Album, AlbumAdmin)
admin.site.register(Song)
