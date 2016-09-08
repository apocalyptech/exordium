from django.contrib import admin
from django.http import HttpResponseRedirect

from .models import Artist, Album, Song

# Register your models here.
admin.site.register(Artist)
admin.site.register(Album)
admin.site.register(Song)
