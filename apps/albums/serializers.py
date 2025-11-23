from rest_framework import serializers
from .models import Album

class AlbumSerializer(serializers.ModelSerializer):
    """
    Serializer para listar detalhes completos do Álbum.
    """
    class Meta:
        model = Album
        fields = [
            'id', 
            'title', 
            'release_date', 
            'cover_image_url'
        ]