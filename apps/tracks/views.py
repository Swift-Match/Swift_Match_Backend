from rest_framework import generics
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from .models import Track
from .serializers import TrackSerializer


class TrackListByAlbumView(generics.ListAPIView):
    """
    Retorna uma lista de músicas (tracks) pertencentes a um álbum específico.
    URL esperada: /api/tracks/album/<int:album_id>/
    """

    serializer_class = TrackSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        album_id = self.kwargs["album_id"]

        return Track.objects.filter(album_id=album_id).order_by("track_number")
