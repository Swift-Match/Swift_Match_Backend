from rest_framework import serializers
from .models import Track

class TrackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Track
        # Retornamos o ID, título, número da faixa e o ID do álbum
        fields = ['id', 'title', 'track_number', 'album']