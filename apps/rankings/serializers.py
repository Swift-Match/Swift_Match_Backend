from rest_framework import serializers
from .models import (
    AlbumRanking, 
    TrackRanking, 
    CountryGlobalRanking,
    UserRanking,
    RankedTrack,
    GroupRanking,
)
from apps.albums.models import Album
from apps.tracks.models import Track
from apps.social.models import Group

# Serializer para um único item do ranking (recebido dentro de uma lista)
class AlbumRankingItemSerializer(serializers.Serializer):
    album_id = serializers.PrimaryKeyRelatedField(
        queryset=Album.objects.all(), 
        source='album',
        write_only=True
    )
    position = serializers.IntegerField(min_value=1)
    
    # Validações extras serão feitas na View

# Serializer principal para receber a lista de rankings
class AlbumRankingSerializer(serializers.Serializer):
    # Recebe uma lista de objetos AlbumRankingItemSerializer
    rankings = AlbumRankingItemSerializer(many=True)

    def create(self, validated_data, user):
        rankings_data = validated_data.pop('rankings')
        ranking_objects = []
        
        # 1. Limpa rankings existentes do usuário para que ele possa enviar um novo
        AlbumRanking.objects.filter(user=user).delete()
        
        # 2. Verifica se as posições são únicas e sequenciais (1, 2, 3...)
        positions = [item['position'] for item in rankings_data]
        if len(set(positions)) != len(positions):
            raise serializers.ValidationError("As posições no ranking devem ser únicas.")
        
        # 3. Cria os novos objetos de ranking
        for item in rankings_data:
            ranking_objects.append(
                AlbumRanking(
                    user=user,
                    album=item['album'],
                    position=item['position']
                )
            )
        
        # Cria os objetos em massa para performance
        AlbumRanking.objects.bulk_create(ranking_objects)
        return ranking_objects


# O Serializer de TrackRanking seguirá uma lógica muito similar.
# Para manter o foco, vamos implementar a View de Álbum agora.

# Serializer para um único item do ranking de música (recebido dentro de uma lista)
class TrackRankingItemSerializer(serializers.Serializer):
    track_id = serializers.PrimaryKeyRelatedField(
        queryset=Track.objects.all(), 
        source='track',
        write_only=True
    )
    position = serializers.IntegerField(min_value=1)

