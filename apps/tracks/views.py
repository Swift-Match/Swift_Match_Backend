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
    permission_classes = [IsAuthenticatedOrReadOnly] # Permite leitura para não logados, se quiser

    def get_queryset(self):
        # Pega o ID do álbum passado na URL
        album_id = self.kwargs['album_id']
        
        # Filtra as músicas desse álbum e ordena pelo número da faixa
        return Track.objects.filter(album_id=album_id).order_by('track_number')