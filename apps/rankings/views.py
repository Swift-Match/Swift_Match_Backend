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

class GroupCompatibilityView(APIView):
    """
    Calcula a compatibilidade média de álbuns de todos os pares em um grupo.
    """
    permission_classes = [IsAuthenticated] 

    serializer_class = EmptyResponseSerializer

    def get(self, request, group_id):
        group = get_object_or_404(Group, pk=group_id)
        
        # 1. Verifica se o usuário logado é membro do grupo
        if not group.members.filter(pk=request.user.id).exists():
            return Response(
                {"error": "Você não é membro deste grupo."}, 
                status=status.HTTP_403_FORBIDDEN
            )

        members = list(group.members.all())
        num_members = len(members)

        if num_members < 2:
            return Response(
                {"compatibility_percent": 0, "message": "O grupo precisa de pelo menos 2 membros para comparação."}, 
                status=status.HTTP_200_OK
            )
        
        member_ids = {member.id for member in members}
        users_with_ranking_ids = set(
            AlbumRanking.objects.filter(user__in=member_ids)
            .values_list('user_id', flat=True)
            .distinct()
        )
        
        if len(users_with_ranking_ids) < num_members:
            non_ranking_ids = member_ids - users_with_ranking_ids
            # OBS: Você precisa garantir que 'User' esteja importado (from apps.users.models import User)
            non_ranking_members = User.objects.filter(id__in=non_ranking_ids)
            non_ranking_usernames = [u.username for u in non_ranking_members]
            
            return Response(
                {"error": f"Não é possível calcular a compatibilidade. Os seguintes membros ainda não submeteram seu ranking de álbuns: {', '.join(non_ranking_usernames)}."}, 
                status=status.HTTP_400_BAD_REQUEST 
            )

        # 2. Calcular a compatibilidade de TODOS os pares (A-B, A-C, B-C, etc.)
        total_compatibility = 0
        pair_comparisons = 0
        detailed_comparisons = []

        # Estruturas para a análise de grupo
        album_positions = defaultdict(list)
        best_match_pair = {"percent": -1, "users": None}
        worst_match_pair = {"percent": 101, "users": None}

        # Usa itertools.combinations para pegar todos os pares únicos
        for user_a, user_b in combinations(members, 2):
            # Chamamos a função que agora retorna a análise detalhada da dupla também
            compatibility, shared_albums, analysis_report = calculate_album_compatibility(user_a, user_b)
            
            # Atualiza o melhor/pior par de match
            if compatibility > best_match_pair["percent"]:
                best_match_pair = {"percent": compatibility, "users": (user_a.username, user_b.username)}
            if compatibility < worst_match_pair["percent"]:
                worst_match_pair = {"percent": compatibility, "users": (user_a.username, user_b.username)}

            total_compatibility += compatibility
            pair_comparisons += 1
            
            detailed_comparisons.append({
                "user_a": user_a.username,
                "user_b": user_b.username,
                "percent": compatibility,
                "shared_albums": shared_albums,
                "duo_analysis": analysis_report # Detalhe do matching da dupla
            })

            # Coletar todas as posições para os álbuns compartilhados (para Desvio Padrão e Média)
            if shared_albums > 0:
                # Necessário buscar o ranking dos álbuns compartilhados novamente de forma otimizada
                # Usaremos um ORM para essa coleta mais eficiente fora do loop de pares,
                # Mas por simplicidade, faremos uma busca auxiliar aqui (idealmente, isso seria pré-buscado)
                
                # Para simplificar, vamos buscar as posições de TODOS os álbuns rankeados no grupo:
                for ranking in AlbumRanking.objects.filter(user__in=members):
                    album_positions[ranking.album.id].append(ranking.position)

        # Verifica se houve alguma comparação de pares
        if pair_comparisons == 0:
            return Response(
                {"compatibility_percent": 0, "message": "O grupo precisa de pelo menos 2 membros com rankings em comum."}, 
                status=status.HTTP_200_OK
            )
            
        # 2. Análise Coletiva (Consenso e Polarização)
        
        group_album_analysis = {}
        for album_id, positions in album_positions.items():
            if len(positions) > 1: # Só faz sentido calcular se mais de um membro rankeou
                
                # Média das Posições (Consenso)
                avg_position = statistics.mean(positions)
                
                # Desvio Padrão (Polarização)
                try:
                    std_dev = statistics.stdev(positions)
                except statistics.StatisticsError:
                    std_dev = 0 # Ocorre se houver apenas um elemento ou posições idênticas
                
                group_album_analysis[album_id] = {
                    "avg_position": round(avg_position, 2),
                    "std_dev": round(std_dev, 2)
                }
        
        # 3. Identificação dos Extremos
        
        # Álbum do Consenso (Menor Média)
        consensus_album_id = min(group_album_analysis, key=lambda id: group_album_analysis[id]["avg_position"], default=None)
        
        # Álbum da Discórdia (Maior Média)
        discord_album_id = max(group_album_analysis, key=lambda id: group_album_analysis[id]["avg_position"], default=None)

        # Álbum da Maior Polarização (Maior Desvio Padrão)
        polarization_album_id = max(group_album_analysis, key=lambda id: group_album_analysis[id]["std_dev"], default=None)


        group_compatibility = round(total_compatibility / pair_comparisons, 2)
        
        # 4. Resposta Final
        return Response({
            "group_name": group.name,
            "members_count": num_members,
            "group_compatibility_percent": group_compatibility,
            
            "collective_analysis": {
                "consensus_album_id": consensus_album_id,
                "discord_album_id": discord_album_id,
                "polarization_album_id": polarization_album_id,
                "best_matching_pair": best_match_pair,
                "worst_matching_pair": worst_match_pair,
                "full_group_ranking_data": group_album_analysis # Dados brutos de todas as médias/polarizações
            },
            
            "detailed_comparisons": detailed_comparisons
        }, status=status.HTTP_200_OK)
    

def check_friendship(user_a, user_b):
    """Verifica se user_a e user_b são amigos (em qualquer direção) e se a amizade é ativa."""
    if user_a.id == user_b.id:
        return True # Usuário é sempre "amigo" de si mesmo para comparação
    
    # Checa se existe uma amizade ativa (status=2) entre A e B ou B e A
    return Friendship.objects.filter(
        Q(user_a=user_a, user_b=user_b) | Q(user_a=user_b, user_b=user_a),
        status=2 # 2 geralmente representa 'Aceita' ou 'Amigos'
    ).exists()
    

class CompatibilityView(APIView):
    """
    Calcula a compatibilidade de ranking de álbuns entre o usuário logado e outro usuário.
    Requer que os dois usuários sejam AMIGOS.
    """
    permission_classes = [IsAuthenticated]

    serializer_class = EmptyResponseSerializer

    def get(self, request, target_user_id):
        user_a = request.user
        try:
            user_b = User.objects.get(pk=target_user_id)
        except User.DoesNotExist:
            return Response({"error": "Usuário alvo não encontrado."}, status=status.HTTP_404_NOT_FOUND)

        # CHECAGEM DE AMIZADE
        if not check_friendship(user_a, user_b):
            return Response(
                {"error": f"Você não pode comparar rankings com {user_b.username}. É necessário ser amigo."}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # CHECAGEM DE COBERTURA DE RANKING (ÁLBUNS)
        user_a_has_rankings = AlbumRanking.objects.filter(user=user_a).exists()
        user_b_has_rankings = AlbumRanking.objects.filter(user=user_b).exists()

        if not user_a_has_rankings or not user_b_has_rankings:
            missing_user = []
            if not user_a_has_rankings:
                missing_user.append(user_a.username)
            if not user_b_has_rankings:
                missing_user.append(user_b.username)

            return Response(
                {"error": f"Não é possível comparar. O(s) usuário(s) {', '.join(missing_user)} ainda não submeteram seu ranking de álbuns."},
                status=status.HTTP_400_BAD_REQUEST 
            )

        # Chama a função utilitária
        compatibility_percent, num_shared_albums, analysis_report = calculate_album_compatibility(user_a, user_b)
        
        # Como a função retorna a porcentagem, simplificamos o retorno aqui.
        if num_shared_albums == 0:
             return Response(
                {"compatibility_percent": 0, "message": "Nenhum álbum em comum rankeado."}, 
                status=status.HTTP_200_OK
            )
            
        return Response({
        "target_user": user_b.username,
        "shared_albums_count": num_shared_albums,
        "compatibility_percent": compatibility_percent,
        "matching_analysis": analysis_report # 🌟 Dados adicionais aqui
    }, status=status.HTTP_200_OK)

