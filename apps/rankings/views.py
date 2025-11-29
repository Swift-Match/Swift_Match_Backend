from rest_framework import status, viewsets, serializers
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Q
from .models import AlbumRanking, TrackRanking, GroupRanking, CountryGlobalRanking
from django.shortcuts import get_object_or_404
from apps.albums.models import Album
from apps.social.models import Group, Friendship
from itertools import combinations
from apps.users.models import User
from collections import defaultdict
import statistics
from .utils import calculate_album_compatibility, calculate_track_compatibility
from rest_framework import generics
from .serializers import (
    CountryGlobalRankingSerializer,
    GroupRankingCreateSerializer,
    AlbumRankingSerializer,
    TrackRankingSerializer,
)


def _get_user_from_request(request):
    """
    Extrai o usuário autenticado a partir do token Bearer enviado pelo frontend.
    Retorna None se o token for inválido ou ausente.
    """
    auth_header = request.headers.get("Authorization")

    if not auth_header or not auth_header.startswith("Bearer "):
        return None

    token = auth_header.split(" ")[1]

    from rest_framework_simplejwt.tokens import AccessToken

    try:
        access_token = AccessToken(token)
        user_id = access_token["user_id"]

        from django.contrib.auth import get_user_model

        User = get_user_model()

        return User.objects.get(id=user_id)

    except Exception:
        return None


class EmptyResponseSerializer(serializers.Serializer):
    """
    Serializer placeholder para views que só usam GET ou retornam JSON customizado.
    Serve apenas para satisfazer a checagem de schema do Swagger.
    """

    pass


class TrackRankingView(APIView):
    """
    Permite ao usuário autenticado enviar/visualizar seu ranking de músicas para um álbum específico.
    """

    permission_classes = [IsAuthenticated]

    serializer_class = TrackRankingSerializer

    def post(self, request, album_id):
        data = request.data.copy()
        data["album_id"] = album_id

        serializer = TrackRankingSerializer(data=data)

        if serializer.is_valid():
            try:
                serializer.create(serializer.validated_data, user=request.user)
                return Response(
                    {
                        "message": f"Ranking de músicas para o álbum '{Album.objects.get(id=album_id).title}' salvo com sucesso!"
                    },
                    status=status.HTTP_201_CREATED,
                )
            except serializers.ValidationError as e:
                return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request, album_id):
        album = get_object_or_404(Album, pk=album_id)

        rankings = (
            TrackRanking.objects.filter(user=request.user, track__album=album)
            .select_related("track")
            .order_by("position")
        )

        data = {
            "album_title": album.title,
            "rankings": [
                {
                    "track_id": r.track.id,
                    "track_title": r.track.title,
                    "position": r.position,
                }
                for r in rankings
            ],
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

        if not group.members.filter(pk=request.user.id).exists():
            return Response(
                {"error": "Você não é membro deste grupo."},
                status=status.HTTP_403_FORBIDDEN,
            )

        members = list(group.members.all())
        num_members = len(members)

        if num_members < 2:
            return Response(
                {
                    "compatibility_percent": 0,
                    "message": "O grupo precisa de pelo menos 2 membros para comparação.",
                },
                status=status.HTTP_200_OK,
            )

        member_ids = {member.id for member in members}
        users_with_ranking_ids = set(
            AlbumRanking.objects.filter(user__in=member_ids)
            .values_list("user_id", flat=True)
            .distinct()
        )

        if len(users_with_ranking_ids) < num_members:
            non_ranking_ids = member_ids - users_with_ranking_ids
            non_ranking_members = User.objects.filter(id__in=non_ranking_ids)
            non_ranking_usernames = [u.username for u in non_ranking_members]

            return Response(
                {
                    "error": f"Não é possível calcular a compatibilidade. Os seguintes membros ainda não submeteram seu ranking de álbuns: {', '.join(non_ranking_usernames)}."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        total_compatibility = 0
        pair_comparisons = 0
        detailed_comparisons = []

        album_positions = defaultdict(list)
        best_match_pair = {"percent": -1, "users": None}
        worst_match_pair = {"percent": 101, "users": None}

        for user_a, user_b in combinations(members, 2):
            compatibility, shared_albums, analysis_report = (
                calculate_album_compatibility(user_a, user_b)
            )

            if compatibility > best_match_pair["percent"]:
                best_match_pair = {
                    "percent": compatibility,
                    "users": (user_a.username, user_b.username),
                }
            if compatibility < worst_match_pair["percent"]:
                worst_match_pair = {
                    "percent": compatibility,
                    "users": (user_a.username, user_b.username),
                }

            total_compatibility += compatibility
            pair_comparisons += 1

            detailed_comparisons.append(
                {
                    "user_a": user_a.username,
                    "user_b": user_b.username,
                    "percent": compatibility,
                    "shared_albums": shared_albums,
                    "duo_analysis": analysis_report,
                }
            )

            if shared_albums > 0:

                for ranking in AlbumRanking.objects.filter(user__in=members):
                    album_positions[ranking.album.id].append(ranking.position)

        if pair_comparisons == 0:
            return Response(
                {
                    "compatibility_percent": 0,
                    "message": "O grupo precisa de pelo menos 2 membros com rankings em comum.",
                },
                status=status.HTTP_200_OK,
            )

        group_album_analysis = {}
        for album_id, positions in album_positions.items():
            if len(positions) > 1:

                avg_position = statistics.mean(positions)

                try:
                    std_dev = statistics.stdev(positions)
                except statistics.StatisticsError:
                    std_dev = 0

                group_album_analysis[album_id] = {
                    "avg_position": round(avg_position, 2),
                    "std_dev": round(std_dev, 2),
                }

        consensus_album_id = min(
            group_album_analysis,
            key=lambda id: group_album_analysis[id]["avg_position"],
            default=None,
        )

        discord_album_id = max(
            group_album_analysis,
            key=lambda id: group_album_analysis[id]["avg_position"],
            default=None,
        )

        polarization_album_id = max(
            group_album_analysis,
            key=lambda id: group_album_analysis[id]["std_dev"],
            default=None,
        )

        group_compatibility = round(total_compatibility / pair_comparisons, 2)

        return Response(
            {
                "group_name": group.name,
                "members_count": num_members,
                "group_compatibility_percent": group_compatibility,
                "collective_analysis": {
                    "consensus_album_id": consensus_album_id,
                    "discord_album_id": discord_album_id,
                    "polarization_album_id": polarization_album_id,
                    "best_matching_pair": best_match_pair,
                    "worst_matching_pair": worst_match_pair,
                    "full_group_ranking_data": group_album_analysis,
                },
                "detailed_comparisons": detailed_comparisons,
            },
            status=status.HTTP_200_OK,
        )


def check_friendship(user_a, user_b):
    """
    Verifica se user_a e user_b são amigos (em qualquer direção) e se a amizade é ativa.
    Retorna True também quando user_a == user_b (auto-comparação permitida).
    """
    if user_a.id == user_b.id:
        return True

    return Friendship.objects.filter(
        (Q(from_user=user_a) & Q(to_user=user_b))
        | (Q(from_user=user_b) & Q(to_user=user_a)),
        status=2,
    ).exists()


class CompatibilityView(APIView):
    """
    Calcula a compatibilidade de ranking de álbuns entre o usuário logado e outro usuário.
    (REMOVIDA a checagem de amizade: qualquer usuário autenticado pode comparar)
    """

    permission_classes = [AllowAny]
    serializer_class = EmptyResponseSerializer

    def get(self, request, target_user_id):
        # autenticação manual (mantida)
        user_a = _get_user_from_request(request)
        if not user_a:
            return Response(
                {"detail": "Authentication credentials were not provided."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            user_b = User.objects.get(pk=target_user_id)
        except User.DoesNotExist:
            return Response(
                {"error": "Usuário alvo não encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )

        user_a_has_rankings = AlbumRanking.objects.filter(user=user_a).exists()
        user_b_has_rankings = AlbumRanking.objects.filter(user=user_b).exists()

        if not user_a_has_rankings or not user_b_has_rankings:
            missing_user = []
            if not user_a_has_rankings:
                missing_user.append(user_a.username)
            if not user_b_has_rankings:
                missing_user.append(user_b.username)

            return Response(
                {
                    "error": f"Não é possível comparar. O(s) usuário(s) {', '.join(missing_user)} ainda não submeteram seu ranking de álbuns."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        compatibility_percent, num_shared_albums, analysis_report = (
            calculate_album_compatibility(user_a, user_b)
        )

        if num_shared_albums == 0:
            return Response(
                {
                    "compatibility_percent": 0,
                    "message": "Nenhum álbum em comum rankeado.",
                },
                status=status.HTTP_200_OK,
            )

        return Response(
            {
                "target_user": user_b.username,
                "shared_albums_count": num_shared_albums,
                "compatibility_percent": compatibility_percent,
                "matching_analysis": analysis_report,
            },
            status=status.HTTP_200_OK,
        )


class TrackCompatibilityView(APIView):
    """
    Calcula a compatibilidade de ranking de músicas de um álbum específico entre o usuário logado e outro usuário.
    (REMOVIDA a checagem de amizade)
    """

    permission_classes = [AllowAny]
    serializer_class = EmptyResponseSerializer

    def get(self, request, target_user_id, album_id):
        user_a = _get_user_from_request(request)
        if not user_a:
            return Response(
                {"detail": "Authentication credentials were not provided."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            user_b = User.objects.get(pk=target_user_id)
            album = Album.objects.get(pk=album_id)
        except User.DoesNotExist:
            return Response(
                {"error": "Usuário alvo não encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Album.DoesNotExist:
            return Response(
                {"error": "Álbum não encontrado."}, status=status.HTTP_404_NOT_FOUND
            )

        user_a_has_rankings = TrackRanking.objects.filter(
            user=user_a, track__album=album
        ).exists()
        user_b_has_rankings = TrackRanking.objects.filter(
            user=user_b, track__album=album
        ).exists()

        if not user_a_has_rankings or not user_b_has_rankings:
            missing_user = []
            if not user_a_has_rankings:
                missing_user.append(user_a.username)
            if not user_b_has_rankings:
                missing_user.append(user_b.username)

            return Response(
                {
                    "error": f"Não é possível comparar. O(s) usuário(s) {', '.join(missing_user)} ainda não submeteram seu ranking de músicas para o álbum '{album.title}'."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        compatibility_percent, num_shared_tracks, analysis_report = (
            calculate_track_compatibility(user_a, user_b, album)
        )

        if num_shared_tracks == 0:
            return Response(
                {
                    "compatibility_percent": 0,
                    "message": f"Nenhuma música do álbum '{album.title}' rankeada por ambos.",
                },
                status=status.HTTP_200_OK,
            )

        return Response(
            {
                "target_user": user_b.username,
                "album_title": album.title,
                "shared_tracks_count": num_shared_tracks,
                "compatibility_percent": compatibility_percent,
                "matching_analysis": analysis_report,
            },
            status=status.HTTP_200_OK,
        )


class GroupTrackCompatibilityView(APIView):
    """
    Calcula a compatibilidade média de MÚSICAS de um álbum em um grupo,
    identificando a música do Consenso, Discórdia e Polarização.
    """

    permission_classes = [IsAuthenticated]

    serializer_class = EmptyResponseSerializer

    def get(self, request, group_id, album_id):
        group = get_object_or_404(Group, pk=group_id)
        album = get_object_or_404(Album, pk=album_id)

        if not group.members.filter(pk=request.user.id).exists():
            return Response(
                {"error": "Você não é membro deste grupo."},
                status=status.HTTP_403_FORBIDDEN,
            )

        members = list(group.members.all())
        num_members = len(members)

        if num_members < 2:
            return Response(
                {
                    "compatibility_percent": 0,
                    "message": "O grupo precisa de pelo menos 2 membros para comparação.",
                },
                status=status.HTTP_200_OK,
            )

        member_ids = {member.id for member in members}

        users_with_track_ranking_ids = set(
            TrackRanking.objects.filter(user__in=member_ids, track__album=album)
            .values_list("user_id", flat=True)
            .distinct()
        )

        if len(users_with_track_ranking_ids) < num_members:
            non_ranking_ids = member_ids - users_with_track_ranking_ids
            non_ranking_members = User.objects.filter(id__in=non_ranking_ids)
            non_ranking_usernames = [u.username for u in non_ranking_members]

            return Response(
                {
                    "error": f"Não é possível calcular a compatibilidade de músicas para '{album.title}'. Os seguintes membros ainda não submeteram seu ranking para este álbum: {', '.join(non_ranking_usernames)}."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        track_positions = defaultdict(list)

        member_track_rankings = TrackRanking.objects.filter(
            user__in=members, track__album=album
        ).select_related("track")

        for ranking in member_track_rankings:
            track_positions[ranking.track.id].append(ranking.position)

        total_compatibility = 0
        pair_comparisons = 0
        detailed_comparisons = []
        best_match_pair = {"percent": -1, "users": None}
        worst_match_pair = {"percent": 101, "users": None}

        for user_a, user_b in combinations(members, 2):
            compatibility, shared_tracks, analysis_report = (
                calculate_track_compatibility(user_a, user_b, album)
            )

            total_compatibility += compatibility
            pair_comparisons += 1

            if compatibility > best_match_pair["percent"]:
                best_match_pair = {
                    "percent": compatibility,
                    "users": (user_a.username, user_b.username),
                }
            if compatibility < worst_match_pair["percent"]:
                worst_match_pair = {
                    "percent": compatibility,
                    "users": (user_a.username, user_b.username),
                }

            detailed_comparisons.append(
                {
                    "user_a": user_a.username,
                    "user_b": user_b.username,
                    "percent": compatibility,
                    "shared_tracks": shared_tracks,
                    "duo_analysis": analysis_report,
                }
            )

        if pair_comparisons == 0:
            return Response(
                {
                    "compatibility_percent": 0,
                    "message": f"Nenhum membro rankeou músicas em comum no álbum '{album.title}'.",
                },
                status=status.HTTP_200_OK,
            )

        group_track_analysis = {}
        for track_id, positions in track_positions.items():
            if len(positions) > 1:
                avg_position = statistics.mean(positions)

                try:
                    std_dev = statistics.stdev(positions)
                except statistics.StatisticsError:
                    std_dev = 0

                group_track_analysis[track_id] = {
                    "avg_position": round(avg_position, 2),
                    "std_dev": round(std_dev, 2),
                }

        consensus_track_id = min(
            group_track_analysis,
            key=lambda id: group_track_analysis[id]["avg_position"],
            default=None,
        )

        discord_track_id = max(
            group_track_analysis,
            key=lambda id: group_track_analysis[id]["avg_position"],
            default=None,
        )

        polarization_track_id = max(
            group_track_analysis,
            key=lambda id: group_track_analysis[id]["std_dev"],
            default=None,
        )

        group_compatibility = round(total_compatibility / pair_comparisons, 2)

        return Response(
            {
                "group_name": group.name,
                "album_title": album.title,
                "group_compatibility_percent": group_compatibility,
                "collective_analysis": {
                    "consensus_track_id": consensus_track_id,
                    "discord_track_id": discord_track_id,
                    "polarization_track_id": polarization_track_id,
                    "best_matching_pair": best_match_pair,
                    "worst_matching_pair": worst_match_pair,
                    "full_group_ranking_data": group_track_analysis,
                },
                "detailed_comparisons": detailed_comparisons,
            },
            status=status.HTTP_200_OK,
        )


class GlobalRankingListView(generics.ListAPIView):
    """
    Retorna o ranking global de álbuns para todos os países
    (Dados pré-calculados para o mapa).
    """

    queryset = CountryGlobalRanking.objects.all().select_related(
        "consensus_album", "polarization_album"
    )
    serializer_class = CountryGlobalRankingSerializer
    permission_classes = [AllowAny]


class GroupRankingViewSet(viewsets.ModelViewSet):
    """Endpoint para adicionar/gerenciar álbuns a serem rankeados pelos grupos."""

    queryset = GroupRanking.objects.all()
    serializer_class = GroupRankingCreateSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return GroupRanking.objects.filter(group__members=user).order_by("-id")

    def perform_create(self, serializer):
        serializer.save(added_by=self.request.user)


class AlbumRankingView(APIView):

    def put(self, request):
        """
        Permite ao usuário autenticado atualizar (sobrescrever) seu ranking de álbuns.
        Reutiliza a lógica de validação e salvamento do POST (Create).
        """
        serializer = AlbumRankingSerializer(data=request.data)
        if serializer.is_valid():
            try:
                serializer.create(serializer.validated_data, user=request.user)
                return Response(
                    {"message": "Ranking de álbuns atualizado com sucesso!"},
                    status=status.HTTP_200_OK,
                )
            except serializers.ValidationError as e:
                return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserRankedTitlesView(APIView):
    """
    Retorna:
      - albums_ranked_via_albums: títulos de álbuns ranqueados via AlbumRanking
      - albums_ranked_via_tracks: títulos de álbuns que possuem tracks ranqueadas (via TrackRanking -> track.album)
      - ranked_track_titles: títulos das tracks ranqueadas
      - combined_albums: união das duas listas acima (sem duplicatas), preservando ordem
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user

        albums_via_album = list(
            AlbumRanking.objects.filter(user=user, album__isnull=False)
            .values_list("album__title", flat=True)
            .distinct()
        )

        albums_via_tracks = list(
            TrackRanking.objects.filter(
                user=user, track__isnull=False, track__album__isnull=False
            )
            .values_list("track__album__title", flat=True)
            .distinct()
        )

        track_titles = list(
            TrackRanking.objects.filter(user=user, track__isnull=False)
            .values_list("track__title", flat=True)
            .distinct()
        )

        combined = []
        seen = set()
        for t in albums_via_album + albums_via_tracks:
            if t not in seen:
                seen.add(t)
                combined.append(t)

        response_data = {
            "albums_ranked_via_albums": albums_via_album,
            "albums_ranked_via_tracks": albums_via_tracks,
            "ranked_track_titles": track_titles,
            "combined_albums": combined,
        }

        return Response(response_data, status=status.HTTP_200_OK)


class OtherUserRankedTitlesView(APIView):
    """
    Retorna os títulos de álbuns e tracks ranqueados por um usuário específico,
    identificado pelo ID (pk) na URL.
    URL: /api/rankings/user/<int:pk>/ranked-titles/
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, pk, *args, **kwargs):
        target_user = get_object_or_404(User, pk=pk)

        albums_via_album = list(
            AlbumRanking.objects.filter(user=target_user, album__isnull=False)
            .values_list("album__title", flat=True)
            .distinct()
        )

        albums_via_tracks = list(
            TrackRanking.objects.filter(
                user=target_user, track__isnull=False, track__album__isnull=False
            )
            .values_list("track__album__title", flat=True)
            .distinct()
        )

        track_titles = list(
            TrackRanking.objects.filter(user=target_user, track__isnull=False)
            .values_list("track__title", flat=True)
            .distinct()
        )

        combined = []
        seen = set()
        for t in albums_via_album + albums_via_tracks:
            if t not in seen:
                seen.add(t)
                combined.append(t)

        response_data = {
            "albums_ranked_via_albums": albums_via_album,
            "albums_ranked_via_tracks": albums_via_tracks,
            "ranked_track_titles": track_titles,
            "combined_albums": combined,
        }

        return Response(response_data, status=status.HTTP_200_OK)
