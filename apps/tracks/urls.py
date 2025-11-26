from django.urls import path
from .views import TrackListByAlbumView

urlpatterns = [
    # Rota para pegar músicas de um álbum específico pelo ID do álbum
    path('album/<int:album_id>/', TrackListByAlbumView.as_view(), name='track-list-by-album'),
]