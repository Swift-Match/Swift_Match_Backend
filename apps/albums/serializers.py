from rest_framework import serializers
from .models import Album

class AlbumSerializer(serializers.ModelSerializer):
  
    class Meta:
        model = Album
        fields = [
            'id', 
            'title', 
            'release_date', 
            'cover_image_url'
        ]