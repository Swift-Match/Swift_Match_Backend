from rest_framework import status, viewsets, serializers
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Q # Importado para a checagem de amizade
from .models import AlbumRanking, TrackRanking, GroupRanking, CountryGlobalRanking
from django.shortcuts import get_object_or_404
from apps.albums.models import Album
from apps.social.models import Group, Friendship 
from itertools import combinations
from apps.users.models import User
from collections import defaultdict
import statistics
from .utils import calculate_album_compatibility, calculate_track_compatibility
from apps.tracks.models import Track
from rest_framework import generics
from .serializers import (
    CountryGlobalRankingSerializer,
    GroupRankingCreateSerializer,
    AlbumRankingSerializer,
    TrackRankingSerializer
)

class EmptyResponseSerializer(serializers.Serializer):
    """
    Serializer placeholder para views que só usam GET ou retornam JSON customizado.
    Serve apenas para satisfazer a checagem de schema do Swagger.
    """
    pass

class AlbumRankingView(APIView):
    """
    Permite ao usuário autenticado enviar seu ranking de álbuns.
    """
    permission_classes = [IsAuthenticated] # O usuário PRECISA estar logado
    serializer_class = AlbumRankingSerializer

    def post(self, request):
        serializer = AlbumRankingSerializer(data=request.data)
        if serializer.is_valid():
            try:
                # Passa o usuário logado para o método create do serializer
                serializer.create(serializer.validated_data, user=request.user)
                return Response(
                    {"message": "Ranking de álbuns salvo com sucesso!"}, 
                    status=status.HTTP_201_CREATED
                )
            except serializers.ValidationError as e:
                return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    # Adicionar um método GET aqui seria útil para visualizar o ranking atual do usuário
    def get(self, request):
        rankings = AlbumRanking.objects.filter(user=request.user).order_by('position')
        
        # Um Serializer de leitura seria ideal aqui, mas vamos simplificar por enquanto:
        data = [{
            'album_id': r.album.id, 
            'album_title': r.album.title, 
            'position': r.position
        } for r in rankings]
        
        return Response(data, status=status.HTTP_200_OK)
    
class TrackRankingView(APIView):
    """
    Permite ao usuário autenticado enviar/visualizar seu ranking de músicas para um álbum específico.
    """
    permission_classes = [IsAuthenticated]

    serializer_class = TrackRankingSerializer

    # O album_id vem da URL
    def post(self, request, album_id):
        # Adiciona o album_id ao corpo da requisição para o Serializer
        data = request.data.copy()
        data['album_id'] = album_id 
        
        serializer = TrackRankingSerializer(data=data)
        
        if serializer.is_valid():
            try:
                serializer.create(serializer.validated_data, user=request.user)
                return Response(
                    {"message": f"Ranking de músicas para o álbum '{Album.objects.get(id=album_id).title}' salvo com sucesso!"}, 
                    status=status.HTTP_201_CREATED
                )
            except serializers.ValidationError as e:
                return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def get(self, request, album_id):
        album = get_object_or_404(Album, pk=album_id)
        
        # Filtra o ranking do usuário logado para as músicas deste álbum
        rankings = TrackRanking.objects.filter(
            user=request.user, 
            track__album=album
        ).select_related('track').order_by('position')
        
        data = {
            "album_title": album.title,
            "rankings": [{
                'track_id': r.track.id, 
                'track_title': r.track.title, 
                'position': r.position
            } for r in rankings]
        }
        
        return Response(data, status=status.HTTP_200_OK)

