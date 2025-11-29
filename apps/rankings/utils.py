import logging
import statistics
from collections import defaultdict
from typing import Dict

from django.apps import apps
from django.db.models import Avg, Count, F

logger = logging.getLogger(__name__)


def _get_model(app_label: str, model_name: str):
    try:
        return apps.get_model(app_label, model_name)
    except LookupError:
        return None


User = _get_model("users", "User")
Album = _get_model("albums", "Album")
AlbumRanking = _get_model("rankings", "AlbumRanking") or _get_model(
    "albums", "AlbumRanking"
)
Track = _get_model("tracks", "Track")
TrackRanking = _get_model("rankings", "TrackRanking") or _get_model(
    "tracks", "TrackRanking"
)
CountryGlobalRanking = _get_model("rankings", "CountryGlobalRanking")
Group = _get_model("social", "Group")
GroupRanking = _get_model("rankings", "GroupRanking")


def get_album_map() -> Dict[int, object]:
    """
    Retorna { album_id: Album object }.
    Mantido no escopo global para que Celery worker consiga enxergar.
    """
    album_map: Dict[int, object] = {}
    if Album is None:
        logger.warning("Album model not found when building album_map.")
        return album_map

    try:
        for album in Album.objects.all():
            try:
                album_map[int(album.id)] = album
            except Exception:
                continue
    except Exception as e:
        logger.exception("Failed to build album_map: %s", e)
    return album_map


def _calculate_compatibility_from_queryset(shared_rankings, id_field_name):
    """
    Helper que recebe um queryset já convertido em .values(...) com keys:
    - id_field_name (ex: 'album_id' or 'track_id')
    - 'position'
    - 'user_b_position'
    Retorna (percent, count, report)
    """
    num_shared = (
        shared_rankings.count()
        if hasattr(shared_rankings, "count")
        else len(list(shared_rankings))
    )
    if num_shared == 0:
        return 0.0, 0, {}

    min_sum = float("inf")
    max_sum = float("-inf")
    max_diff = -1
    min_diff = float("inf")

    fav_id = None
    least_id = None
    most_div_id = None
    most_conc_id = None

    total_abs_diff = 0

    for item in shared_rankings:
        pos_a = item.get("position")
        pos_b = item.get("user_b_position")
        if pos_a is None or pos_b is None:
            continue

        sum_pos = pos_a + pos_b
        abs_diff = abs(pos_a - pos_b)
        total_abs_diff += abs_diff

        if sum_pos < min_sum:
            min_sum = sum_pos
            fav_id = item.get(id_field_name)

        if sum_pos > max_sum:
            max_sum = sum_pos
            least_id = item.get(id_field_name)

        if abs_diff > max_diff:
            max_diff = abs_diff
            most_div_id = item.get(id_field_name)

        if abs_diff < min_diff:
            min_diff = abs_diff
            most_conc_id = item.get(id_field_name)

    if num_shared == 0:
        return 0.0, 0, {}

    avg_abs_diff = total_abs_diff / num_shared
    max_diff_reference = 5.0
    compatibility_percent = max(0.0, 100.0 * (1 - (avg_abs_diff / max_diff_reference)))

    report = {
        f"favorite_{id_field_name}": fav_id,
        f"least_favorite_{id_field_name}": least_id,
        f"most_divergent_{id_field_name}": most_div_id,
        f"most_concordant_{id_field_name}": most_conc_id,
        "max_position_difference": max_diff,
        "min_position_difference": min_diff,
    }

    return round(compatibility_percent, 2), num_shared, report


def calculate_album_compatibility(user_a, user_b):
    """
    Retorna (percent: float, num_shared_albums: int, analysis_report: dict).
    Compatível com related_name 'user_rankings' no modelo Album (fallback robusto).
    """
    if User is None or AlbumRanking is None or Album is None:
        return 0.0, 0, {}

    if user_a.id == user_b.id:
        return 100.0, 0, {}

    try:
        shared_albums_qs = (
            Album.objects.filter(user_rankings__user=user_a)
            .filter(user_rankings__user=user_b)
            .distinct()
        )
    except Exception:
        album_ids_a = AlbumRanking.objects.filter(user=user_a).values_list(
            "album_id", flat=True
        )
        album_ids_b = AlbumRanking.objects.filter(user=user_b).values_list(
            "album_id", flat=True
        )
        shared_ids = set(album_ids_a).intersection(set(album_ids_b))
        shared_albums_qs = Album.objects.filter(id__in=list(shared_ids))

    num_shared_albums = shared_albums_qs.count()
    if num_shared_albums == 0:
        return 0.0, 0, {}

    min_sum = float("inf")
    max_sum = float("-inf")
    max_diff = -1
    min_diff = float("inf")

    favorite_album = None
    least_favorite_album = None
    most_divergent_album = None
    most_concordant_album = None

    total_abs_diff = 0
    processed_count = 0

    for album in shared_albums_qs:
        try:
            pos_a = AlbumRanking.objects.get(user=user_a, album=album).position
            pos_b = AlbumRanking.objects.get(user=user_b, album=album).position
        except AlbumRanking.DoesNotExist:
            continue

        processed_count += 1
        sum_pos = pos_a + pos_b
        abs_diff = abs(pos_a - pos_b)
        total_abs_diff += abs_diff

        if sum_pos < min_sum:
            min_sum = sum_pos
            favorite_album = album.id

        if sum_pos > max_sum:
            max_sum = sum_pos
            least_favorite_album = album.id

        if abs_diff > max_diff:
            max_diff = abs_diff
            most_divergent_album = album.id

        if abs_diff < min_diff:
            min_diff = abs_diff
            most_concordant_album = album.id

    if processed_count == 0:
        return 0.0, 0, {}

    avg_abs_diff = total_abs_diff / processed_count
    max_diff_reference = 5.0
    compatibility_percent = max(0.0, 100.0 * (1 - (avg_abs_diff / max_diff_reference)))

    analysis_report = {
        "favorite_album_id": favorite_album,
        "least_favorite_album_id": least_favorite_album,
        "most_divergent_album_id": most_divergent_album,
        "most_concordant_album_id": most_concordant_album,
        "max_position_difference": max_diff,
        "min_position_difference": min_diff,
    }

    return round(compatibility_percent, 2), processed_count, analysis_report


def calculate_track_compatibility(user_a, user_b, album):
    """
    Calcula compatibilidade entre TrackRanking de dois usuários PARA UM ÁLBUM ESPECÍFICO.
    Retorna (percent, num_shared_tracks, analysis_report).
    """
    if TrackRanking is None or Track is None:
        return 0.0, 0, {}

    if user_a.id == user_b.id:
        return 100.0, 0, {}

    rankings_a = TrackRanking.objects.filter(user=user_a, track__album=album).order_by(
        "track_id"
    )
    rankings_b = TrackRanking.objects.filter(user=user_b, track__album=album).order_by(
        "track_id"
    )
    track_ids_b = rankings_b.values_list("track_id", flat=True)

    shared_rankings_qs = (
        rankings_a.filter(track_id__in=track_ids_b)
        .annotate(user_b_position=F("track__user_rankings__position"))
        .filter(track__user_rankings__user=user_b)
        .values("track_id", "position", "user_b_position")
        .distinct()
    )

    return _calculate_compatibility_from_queryset(shared_rankings_qs, "track_id")


def calculate_global_ranking():
    """
    Executa o cálculo do ranking de álbuns para todos os países
    onde há pelo menos 2 usuários com rankings submetidos.
    Popula/atualiza CountryGlobalRanking.
    """
    if User is None or AlbumRanking is None or CountryGlobalRanking is None:
        logger.error("Required models not available for calculate_global_ranking.")
        return

    print("--- INICIANDO CÁLCULO GLOBAL DE RANKING ---")

    try:
        countries_data = (
            User.objects.filter(album_rankings__isnull=False)
            .values("country")
            .annotate(user_count=Count("id", distinct=True))
            .filter(user_count__gte=2)
        )
    except Exception:
        try:
            countries_data = (
                AlbumRanking.objects.values("user__country")
                .annotate(user_count=Count("user", distinct=True))
                .filter(user__country__isnull=False)
            )
        except Exception as e:
            logger.exception("Failed to obtain countries_data: %s", e)
            countries_data = []

    album_map = get_album_map()
    track_map = {t.id: t for t in Track.objects.all()} if Track is not None else {}

    for country_info in countries_data:
        country = country_info.get("country") or country_info.get("user__country")
        user_count = country_info.get("user_count") or country_info.get("user_count", 0)

        if not country:
            continue

        print(f"Processando país: {country} (users={user_count})")

        country_user_ids = list(
            User.objects.filter(country=country).values_list("id", flat=True)
        )

        album_stats = (
            AlbumRanking.objects.filter(user_id__in=country_user_ids)
            .values("album_id")
            .annotate(avg_position=Avg("position"), count=Count("position"))
            .order_by("avg_position")
        )

        full_positions = defaultdict(list)
        for ranking in AlbumRanking.objects.filter(user_id__in=country_user_ids):
            full_positions[ranking.album_id].append(ranking.position)

        analysis_data = {}

        for stats in album_stats:
            album_id = stats.get("album_id")
            positions = full_positions.get(album_id, [])

            if len(positions) > 1:
                try:
                    std_dev = statistics.stdev(positions)
                except statistics.StatisticsError:
                    std_dev = 0.0
            else:
                std_dev = 0.0

            album_obj = album_map.get(int(album_id)) if album_id is not None else None
            album_title = getattr(album_obj, "title", None) if album_obj else None

            analysis_data[int(album_id)] = {
                "album_title": album_title,
                "avg_rank": (
                    round(stats.get("avg_position", 0), 2)
                    if stats.get("avg_position") is not None
                    else None
                ),
                "std_dev_rank": round(std_dev, 2),
                "votes": stats.get("count", 0),
            }

        consensus_album_id = None
        polarization_album_id = None
        if analysis_data:
            try:
                consensus_album_id = min(
                    analysis_data,
                    key=lambda k: (
                        analysis_data[k]["avg_rank"]
                        if analysis_data[k]["avg_rank"] is not None
                        else float("inf")
                    ),
                )
            except Exception:
                consensus_album_id = None
            try:
                polarization_album_id = max(
                    analysis_data,
                    key=lambda k: analysis_data[k].get("std_dev_rank", -1),
                )
            except Exception:
                polarization_album_id = None

        try:
            consensus_album_id_int = (
                int(consensus_album_id) if consensus_album_id is not None else None
            )
        except Exception:
            consensus_album_id_int = None
        try:
            polarization_album_id_int = (
                int(polarization_album_id)
                if polarization_album_id is not None
                else None
            )
        except Exception:
            polarization_album_id_int = None

        try:
            ranking_obj, created = CountryGlobalRanking.objects.update_or_create(
                country_name=country,
                defaults={
                    "user_count": user_count,
                    "consensus_album": (
                        album_map.get(consensus_album_id_int)
                        if consensus_album_id_int is not None
                        else None
                    ),
                    "polarization_album": (
                        album_map.get(polarization_album_id_int)
                        if polarization_album_id_int is not None
                        else None
                    ),
                    "analysis_data": analysis_data,
                },
            )
            print(
                f"✅ Ranking de {country} {'criado' if created else 'atualizado'}. Usuários: {user_count}"
            )
        except Exception as e:
            logger.exception(
                "Failed to update_or_create CountryGlobalRanking for %s: %s", country, e
            )
            continue

        member_track_rankings = (
            TrackRanking.objects.filter(user_id__in=country_user_ids).select_related(
                "track"
            )
            if TrackRanking is not None
            else []
        )

        track_positions = defaultdict(list)
        for ranking in member_track_rankings:
            track_positions[ranking.track_id].append(ranking.position)

        global_consensus_track_id = None
        min_global_avg = float("inf")

        track_analysis_by_album = defaultdict(
            lambda: {"top_track_id": None, "tracks": {}}
        )
        polarization_track_id_by_album = {}

        for track_id, positions in track_positions.items():
            track_obj = track_map.get(track_id)
            if not track_obj:
                continue

            try:
                avg_position = statistics.mean(positions)
            except Exception:
                avg_position = float("inf")
            votes = len(positions)
            try:
                std_dev = statistics.stdev(positions) if votes > 1 else 0.0
            except statistics.StatisticsError:
                std_dev = 0.0

            analysis = {
                "track_title": getattr(track_obj, "title", None),
                "album_id": getattr(track_obj, "album_id", None),
                "avg_rank": (
                    round(avg_position, 2)
                    if isinstance(avg_position, (int, float))
                    else None
                ),
                "std_dev_rank": round(std_dev, 2),
                "votes": votes,
            }

            if isinstance(avg_position, (int, float)) and avg_position < min_global_avg:
                min_global_avg = avg_position
                global_consensus_track_id = track_id

            album_id = analysis["album_id"]
            track_analysis_by_album[album_id]["tracks"][track_id] = analysis

            current_top = track_analysis_by_album[album_id]["top_track_id"]
            if current_top is None or (
                analysis["avg_rank"] is not None
                and (
                    track_analysis_by_album[album_id]["tracks"]
                    .get(current_top, {})
                    .get("avg_rank", float("inf"))
                    > analysis["avg_rank"]
                )
            ):
                track_analysis_by_album[album_id]["top_track_id"] = track_id

            current_polarized = polarization_track_id_by_album.get(album_id)
            cur_std = (
                track_analysis_by_album[album_id]["tracks"]
                .get(current_polarized, {})
                .get("std_dev_rank", -1)
            )
            if (current_polarized is None) or (analysis["std_dev_rank"] > cur_std):
                polarization_track_id_by_album[album_id] = track_id

        serialized_track_analysis = {}
        for a_id, info in track_analysis_by_album.items():
            tracks_serialized = {
                str(tid): tinfo for tid, tinfo in info["tracks"].items()
            }
            serialized_track_analysis[str(a_id)] = {
                "top_track_id": info["top_track_id"],
                "tracks": tracks_serialized,
            }

        existing = ranking_obj.analysis_data or {}
        existing = dict(existing)
        existing["track_analysis_by_album"] = serialized_track_analysis
        existing["track_polarization_by_album"] = {
            str(k): v for k, v in polarization_track_id_by_album.items()
        }
        ranking_obj.analysis_data = existing
        ranking_obj.global_consensus_track_id = global_consensus_track_id
        ranking_obj.save()

        print(f"✅ Ranking de {country} atualizado (Álbuns e Tracks).")

    print("--- CÁLCULO GLOBAL FINALIZADO ---")


def calculate_group_internal_coherence(group) -> float:
    """
    CIGG (0..100). Implementação fixa para os testes:
    - usa AlbumRanking e GroupRanking do app 'rankings'
    - MAX_DIFFERENCE = 5 (constante)
    - ignora álbuns com < 2 votos
    - se houver múltiplos votos user+album, a última entrada (order by id) sobrescreve
    """
    try:
        AlbumRankingLocal = apps.get_model("rankings", "AlbumRanking")
        GroupRankingLocal = apps.get_model("rankings", "GroupRanking")
    except LookupError:
        return 0.0

    if GroupRankingLocal is None:
        return 0.0

    matched_album_ids = list(
        GroupRankingLocal.objects.filter(group=group).values_list("album_id", flat=True)
    )
    if not matched_album_ids:
        return 0.0

    member_ids = list(group.members.values_list("id", flat=True))
    if len(member_ids) < 2:
        return 0.0

    rows = (
        AlbumRankingLocal.objects.filter(
            user_id__in=member_ids, album_id__in=matched_album_ids
        )
        .order_by("id")
        .values_list("user_id", "album_id", "position")
    )

    rankings_by_album: Dict[int, Dict[int, float]] = {}
    for user_id, album_id, pos in rows:
        try:
            position = float(pos)
        except Exception:
            continue
        rankings_by_album.setdefault(album_id, {})[user_id] = position

    MAX_DIFFERENCE = 5.0

    total_similarity = 0.0
    total_pairs = 0

    for album_id, umap in rankings_by_album.items():
        if len(umap) < 2:
            continue

        users = list(umap.keys())
        album_sum = 0.0
        album_comps = 0
        for i in range(len(users)):
            for j in range(i + 1, len(users)):
                r1 = umap[users[i]]
                r2 = umap[users[j]]
                diff = abs(r1 - r2)
                similarity = 1.0 - (diff / MAX_DIFFERENCE)
                if similarity < 0.0:
                    similarity = 0.0
                album_sum += similarity
                album_comps += 1

        total_similarity += album_sum
        total_pairs += album_comps

    if total_pairs == 0:
        return 0.0

    ratio = total_similarity / total_pairs
    return ratio * 100.0
