from rest_framework import generics
from rest_framework.permissions import AllowAny # Importar permissão pública
from .models import Album
from .serializers import AlbumSerializer

class AlbumListView(generics.ListAPIView):
    """
    Endpoint público para listar todos os álbuns disponíveis para ranking,
    ordenados pela data de lançamento.
    """
    queryset = Album.objects.all().order_by('release_date')
    serializer_class = AlbumSerializer
    permission_classes = [AllowAny]