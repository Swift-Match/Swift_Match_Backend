from django.urls import path
from .views import TrackListByAlbumView

urlpatterns = [
    path(
        "album/<int:album_id>/",
        TrackListByAlbumView.as_view(),
        name="track-list-by-album",
    ),
]
