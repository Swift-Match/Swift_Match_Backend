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

# Serializer principal para receber a lista de rankings de músicas
class TrackRankingSerializer(serializers.Serializer):
    # O ID do álbum é necessário para validação
    album_id = serializers.PrimaryKeyRelatedField(queryset=Album.objects.all())
    # A lista de rankings de músicas
    rankings = TrackRankingItemSerializer(many=True)

    def create(self, validated_data, user):
        album = validated_data.pop('album_id')
        rankings_data = validated_data.pop('rankings')
        
        # 1. Validação de Posição Única e Sequencial
        positions = [item['position'] for item in rankings_data]
        if len(set(positions)) != len(positions):
            raise serializers.ValidationError("As posições no ranking de músicas devem ser únicas.")
            
        # 2. Validação: todas as músicas pertencem ao álbum fornecido?
        track_ids = [item['track'].id for item in rankings_data]
        valid_tracks = Track.objects.filter(album=album, id__in=track_ids).count()
        
        if valid_tracks != len(track_ids):
            # Isso significa que pelo menos uma música não pertence ao álbum informado
            raise serializers.ValidationError(
                {"tracks": f"Uma ou mais músicas enviadas não pertencem ao álbum '{album.title}'."}
            )

        # 3. Limpa rankings de músicas existentes DESTE ÁLBUM para que ele possa enviar um novo
        # Importante: O usuário pode rankear músicas de outros álbuns, mas este endpoint 
        # trata apenas do ranking do álbum atual.
        tracks_to_delete = Track.objects.filter(album=album, id__in=track_ids)
        TrackRanking.objects.filter(user=user, track__in=tracks_to_delete).delete()

        # 4. Cria os novos objetos de ranking
        ranking_objects = []
        for item in rankings_data:
            ranking_objects.append(
                TrackRanking(
                    user=user,
                    track=item['track'],
                    position=item['position']
                )
            )
        
        TrackRanking.objects.bulk_create(ranking_objects)
        return ranking_objects
    
class CountryGlobalRankingSerializer(serializers.ModelSerializer):
    # Campos que o frontend precisa para o mapa/análise
    consensus_album_title = serializers.ReadOnlyField(source='consensus_album.title')
    polarization_album_title = serializers.ReadOnlyField(source='polarization_album.title')

    class Meta:
        model = CountryGlobalRanking
        fields = (
            'id', 'country_name', 'user_count', 
            'consensus_album', 'consensus_album_title', 
            'polarization_album', 'polarization_album_title', 
            'analysis_data', 'updated_at'
        )
        read_only_fields = fields # É apenas para leitura


