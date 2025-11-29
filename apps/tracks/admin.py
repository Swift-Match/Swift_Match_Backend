from django.contrib import admin
from .models import Track

class TrackInline(admin.TabularInline):
    """Permite editar as músicas dentro do formulário do Álbum."""
    model = Track
    extra = 0 
    fields = ('track_number', 'title')

@admin.register(Track)
class TrackAdmin(admin.ModelAdmin):
    list_display = ('title', 'album', 'track_number')
    list_filter = ('album',)
    search_fields = ('title',)

from apps.albums.admin import AlbumAdmin
AlbumAdmin.inlines = [TrackInline]