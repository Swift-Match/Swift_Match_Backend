from django.contrib import admin
from .models import Album


@admin.register(Album)
class AlbumAdmin(admin.ModelAdmin):
    list_display = ("title", "release_date")
    search_fields = ("title",)
    list_filter = ("release_date",)
