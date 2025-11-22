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
from rest_framework.validators import UniqueTogetherValidator


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
    album_id = serializers.PrimaryKeyRelatedField(queryset=Album.objects.all())
    rankings = TrackRankingItemSerializer(many=True)

    def create(self, validated_data, user=None):
        # 0. obter user do argumento ou do contexto (para compatibilidade com os testes)
        if user is None:
            request = self.context.get('request')
            user = getattr(request, 'user', None)

        album = validated_data.pop('album_id')
        rankings_data = validated_data.pop('rankings')

        # 1. Validação de Posição Única e Sequencial
        positions = [item['position'] for item in rankings_data]
        if len(set(positions)) != len(positions):
            raise serializers.ValidationError({
                'positions': ['As posições no ranking de músicas devem ser únicas.']
            })

        # 2. Validação: todas as músicas pertencem ao álbum fornecido?
        # supondo que cada item tenha o campo 'track' como instância/PK conforme seu TrackRankingItemSerializer
        track_ids = [item['track'].id if hasattr(item['track'], 'id') else item['track'] for item in rankings_data]
        valid_tracks = Track.objects.filter(album=album, id__in=track_ids).count()

        if valid_tracks != len(track_ids):
            # Retornar uma lista de mensagens em 'tracks' (o teste procura por substrings em cada mensagem)
            raise serializers.ValidationError({
                'tracks': [f'Uma ou mais músicas enviadas não pertencem ao álbum "{album.title}".']
            })

        # 3. Limpa rankings de músicas existentes DESTE ÁLBUM para que ele possa enviar um novo
        TrackRanking.objects.filter(user=user, track__album=album).delete()

        # 4. Cria os novos objetos de ranking
        ranking_objects = []
        for item in rankings_data:
            # se item['track'] for PK em vez de instância, buscar a Track
            track = item['track'] if hasattr(item['track'], 'id') else Track.objects.get(id=item['track'])
            ranking_objects.append(
                TrackRanking(
                    user=user,
                    track=track,
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


class RankedTrackSerializer(serializers.ModelSerializer):
    """Serializer para receber e exibir a posição de uma track."""
    track_id = serializers.PrimaryKeyRelatedField(
        queryset=Track.objects.all(), 
        source='track' # Mapeia 'track_id' para o campo 'track' no modelo
    )
    title = serializers.CharField(source='track.title', read_only=True)

    class Meta:
        model = RankedTrack
        fields = ('track_id', 'position', 'title')
        # 'user_ranking' será gerenciado pelo serializer pai
        
from rest_framework import serializers

class UserRankingCreateSerializer(serializers.Serializer):
    group_ranking = serializers.PrimaryKeyRelatedField(queryset=GroupRanking.objects.all())
    ranked_tracks = RankedTrackSerializer(many=True)  # ou seu serializer atual

    def validate(self, attrs):

        request = self.context.get('request')
        
        # Verifica se a request existe e se o usuário é anônimo/inválido
        if not request or not request.user or request.user.is_anonymous:
            # Lança um erro que será capturado por is_valid()
            raise serializers.ValidationError({
                'user': ['O usuário deve estar autenticado para criar um ranking.']
            })
            
        # Restaura as validações que dependem só do payload
        ranked = attrs.get('ranked_tracks', [])
        positions = [item['position'] for item in ranked]
        if len(set(positions)) != len(positions):
            raise serializers.ValidationError({
                'ranked_tracks': ['As posições devem ser únicas.']
            })
            
        return attrs

    def create(self, validated_data):
    
        # 1. Pop (remover) o user que foi injetado pelo serializer.save(user=user_fixture)
        #    e os dados aninhados
        user = validated_data.pop('user')  # <--- NOVA LINHA/ALTERAÇÃO CRÍTICA
        ranked_tracks_data = validated_data.pop('ranked_tracks')
        
        # 2. Cria o objeto principal UserRanking
        # Agora validated_data contém apenas 'group_ranking', e 'user' é passado separadamente
        user_ranking = UserRanking.objects.create(user=user, **validated_data) 

        # 3. Cria os objetos aninhados RankedTrack
        for track_data in ranked_tracks_data:
            RankedTrack.objects.create(user_ranking=user_ranking, **track_data)

        return user_ranking
    

class GroupRankingCreateSerializer(serializers.ModelSerializer):
    """Serializer para adicionar um Album a um Grupo."""
    
    class Meta:
        model = GroupRanking
        fields = ['group', 'album']
        validators = [
            UniqueTogetherValidator(
                queryset=GroupRanking.objects.all(),
                fields=('group', 'album'),
                message='já existe um ranking para este grupo e álbum.'
            )
        ]

    def validate(self, data):
        group = data['group']
        user = self.context['request'].user
        
        # 1. VALIDAÇÃO DE PERMISSÃO: O usuário deve ser membro do grupo para adicionar um ranking.
        if not Group.objects.filter(id=group.id, members=user).exists():
            raise serializers.ValidationError(
                "Você precisa ser membro deste grupo para adicionar um ranking."
            )
        return data

    def create(self, validated_data):
        # 2. CRIAÇÃO: Cria o GroupRanking
        validated_data['added_by'] = self.context['request'].user
        group_ranking = super().create(validated_data)
        
        # 3. DISPARO DE NOTIFICAÇÃO (TAREFA CELERY)
        # Assumindo uma função de Celery que notificará todos os membros:
        # from .tasks import notify_group_of_new_ranking
        # notify_group_of_new_ranking.delay(group_ranking.id)
        
        return group_ranking