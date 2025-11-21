from django.contrib import admin
from .models import Track

class TrackInline(admin.TabularInline):
    """Permite editar as músicas dentro do formulário do Álbum."""
    model = Track
    extra = 0 # Não mostra linhas vazias por padrão
    fields = ('track_number', 'title')

# Registra o Track diretamente para visualização
@admin.register(Track)
class TrackAdmin(admin.ModelAdmin):
    list_display = ('title', 'album', 'track_number')
    list_filter = ('album',)
    search_fields = ('title',)

# Opcional: Adicionar o Inline ao AlbumAdmin para cadastro rápido
from apps.albums.admin import AlbumAdmin
AlbumAdmin.inlines = [TrackInline]