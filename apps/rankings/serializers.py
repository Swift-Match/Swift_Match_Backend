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


class AlbumRankingItemSerializer(serializers.Serializer):
    album_id = serializers.PrimaryKeyRelatedField(
        queryset=Album.objects.all(), 
        source='album',
        write_only=True
    )
    position = serializers.IntegerField(min_value=1)
    

class AlbumRankingSerializer(serializers.Serializer):
    rankings = AlbumRankingItemSerializer(many=True)

    def create(self, validated_data, user):
        rankings_data = validated_data.pop('rankings')
        ranking_objects = []
        
        AlbumRanking.objects.filter(user=user).delete()
        
        positions = [item['position'] for item in rankings_data]
        if len(set(positions)) != len(positions):
            raise serializers.ValidationError("As posições no ranking devem ser únicas.")
        
        for item in rankings_data:
            ranking_objects.append(
                AlbumRanking(
                    user=user,
                    album=item['album'],
                    position=item['position']
                )
            )
        
        AlbumRanking.objects.bulk_create(ranking_objects)
        return ranking_objects



class TrackRankingItemSerializer(serializers.Serializer):
    track_id = serializers.PrimaryKeyRelatedField(
        queryset=Track.objects.all(), 
        source='track',
        write_only=True
    )
    position = serializers.IntegerField(min_value=1)

class TrackRankingSerializer(serializers.Serializer):
    album_id = serializers.PrimaryKeyRelatedField(queryset=Album.objects.all())
    rankings = TrackRankingItemSerializer(many=True)

    def create(self, validated_data, user=None):
        if user is None:
            request = self.context.get('request')
            user = getattr(request, 'user', None)

        album = validated_data.pop('album_id')
        rankings_data = validated_data.pop('rankings')

        positions = [item['position'] for item in rankings_data]
        if len(set(positions)) != len(positions):
            raise serializers.ValidationError({
                'positions': ['As posições no ranking de músicas devem ser únicas.']
            })

        track_ids = [item['track'].id if hasattr(item['track'], 'id') else item['track'] for item in rankings_data]
        valid_tracks = Track.objects.filter(album=album, id__in=track_ids).count()

        if valid_tracks != len(track_ids):
            raise serializers.ValidationError({
                'tracks': [f'Uma ou mais músicas enviadas não pertencem ao álbum "{album.title}".']
            })

        TrackRanking.objects.filter(user=user, track__album=album).delete()

        ranking_objects = []
        for item in rankings_data:
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
        read_only_fields = fields 


class RankedTrackSerializer(serializers.ModelSerializer):
    """Serializer para receber e exibir a posição de uma track."""
    track_id = serializers.PrimaryKeyRelatedField(
        queryset=Track.objects.all(), 
        source='track' 
    )
    title = serializers.CharField(source='track.title', read_only=True)

    class Meta:
        model = RankedTrack
        fields = ('track_id', 'position', 'title')
        
from rest_framework import serializers

class UserRankingCreateSerializer(serializers.Serializer):
    group_ranking = serializers.PrimaryKeyRelatedField(queryset=GroupRanking.objects.all())
    ranked_tracks = RankedTrackSerializer(many=True)  

    def validate(self, attrs):

        request = self.context.get('request')
        
        if not request or not request.user or request.user.is_anonymous:
            raise serializers.ValidationError({
                'user': ['O usuário deve estar autenticado para criar um ranking.']
            })
            
        ranked = attrs.get('ranked_tracks', [])
        positions = [item['position'] for item in ranked]
        if len(set(positions)) != len(positions):
            raise serializers.ValidationError({
                'ranked_tracks': ['As posições devem ser únicas.']
            })
            
        return attrs

    def create(self, validated_data):
    
        user = validated_data.pop('user')  
        ranked_tracks_data = validated_data.pop('ranked_tracks')
        
        user_ranking = UserRanking.objects.create(user=user, **validated_data) 

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
        
        if not Group.objects.filter(id=group.id, members=user).exists():
            raise serializers.ValidationError(
                "Você precisa ser membro deste grupo para adicionar um ranking."
            )
        return data

    def create(self, validated_data):
        validated_data['added_by'] = self.context['request'].user
        group_ranking = super().create(validated_data)
        
        
        return group_ranking