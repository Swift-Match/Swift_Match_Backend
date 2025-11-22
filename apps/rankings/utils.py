from apps.users.models import User
from apps.rankings.models import AlbumRanking
from django.db.models import F
from apps.tracks.models import Track
from django.db.models import Avg, StdDev, Count
from apps.users.models import User
from apps.albums.models import Album
from .models import AlbumRanking, CountryGlobalRanking, UserRanking, GroupRanking
import statistics
from .models import TrackRanking
from django.db.models import Avg
from apps.social.models import Group
from collections import defaultdict
from django.apps import apps
from typing import Dict
import logging


logger = logging.getLogger(__name__)


def _calculate_compatibility_from_queryset(shared_rankings, id_field_name):
    """
    Helper que recebe um queryset já convertido em .values(...) com keys:
    - id_field_name (ex: 'album_id' or 'track_id')
    - 'position'
    - 'user_b_position'
    Retorna (percent, count, report)
    """
    num_shared = shared_rankings.count()
    if num_shared == 0:
        return 0.0, 0, {}

    min_sum = float('inf')
    max_sum = float('-inf')
    max_diff = -1
    min_diff = float('inf')

    fav_id = None
    least_id = None
    most_div_id = None
    most_conc_id = None

    total_abs_diff = 0

    for item in shared_rankings:
        pos_a = item['position']
        pos_b = item['user_b_position']
        sum_pos = pos_a + pos_b
        abs_diff = abs(pos_a - pos_b)
        total_abs_diff += abs_diff

        if sum_pos < min_sum:
            min_sum = sum_pos
            fav_id = item[id_field_name]

        if sum_pos > max_sum:
            max_sum = sum_pos
            least_id = item[id_field_name]

        if abs_diff > max_diff:
            max_diff = abs_diff
            most_div_id = item[id_field_name]

        if abs_diff < min_diff:
            min_diff = abs_diff
            most_conc_id = item[id_field_name]

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
    Compatível com related_name 'user_rankings' no modelo Album.
    """
    if user_a.id == user_b.id:
        return 100.0, 0, {}

    # NOTE: seu Album expõe a relação reversa como `user_rankings`
    shared_albums_qs = Album.objects.filter(
        user_rankings__user=user_a
    ).filter(
        user_rankings__user=user_b
    ).distinct()

    num_shared_albums = shared_albums_qs.count()
    if num_shared_albums == 0:
        return 0.0, 0, {}

    min_sum = float('inf')
    max_sum = float('-inf')
    max_diff = -1
    min_diff = float('inf')

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


def calculate_track_compatibility(user_a, user_b):
    """
    Calcula compatibilidade entre TrackRanking de dois usuários.
    Retorna (percent, num_shared_tracks, analysis_report).
    """
    if user_a.id == user_b.id:
        return 100.0, 0, {}

    rankings_a = TrackRanking.objects.filter(user=user_a).order_by('track_id')
    rankings_b = TrackRanking.objects.filter(user=user_b).order_by('track_id')

    shared_rankings = rankings_a.filter(track__in=rankings_b.values('track')).values(
        'track_id',
        'position',
        user_b_position=F('track__user_rankings__position')
    ).filter(track__user_rankings__user=user_b)

    return _calculate_compatibility_from_queryset(shared_rankings, 'track_id')

def get_album_map():
    return {album.id: album for album in Album.objects.all()}

def calculate_global_ranking():
    """
    Executa o cálculo do ranking de álbuns para todos os países
    onde há pelo menos 2 usuários com rankings submetidos.
    """
    print("--- INICIANDO CÁLCULO GLOBAL DE RANKING ---")

    # Usa related_name correto 'album_rankings' no User
    countries_data = User.objects.filter(
        album_rankings__isnull=False,
    ).values('country').annotate(
        user_count=Count('id', distinct=True)
    ).filter(user_count__gte=2)

    album_map = get_album_map()
    track_map = {track.id: track for track in Track.objects.all()}

    for country_info in countries_data:
        country = country_info['country']
        user_count = country_info['user_count']

        # ids dos usuários do país
        country_user_ids = list(User.objects.filter(country=country).values_list('id', flat=True))

        # agregação de álbuns (média + contagem)
        album_stats = AlbumRanking.objects.filter(
            user_id__in=country_user_ids
        ).values('album_id').annotate(
            avg_position=Avg('position'),
            count=Count('position')
        ).order_by('avg_position')

        # coleta todas as posições por álbum (fallback para stddev em Python)
        full_positions = defaultdict(list)
        for ranking in AlbumRanking.objects.filter(user_id__in=country_user_ids):
            full_positions[ranking.album_id].append(ranking.position)

        analysis_data = {}

        for stats in album_stats:
            album_id = stats['album_id']
            positions = full_positions.get(album_id, [])

            if len(positions) > 1:
                std_dev = statistics.stdev(positions)
            else:
                std_dev = 0.0

            album_obj = album_map.get(album_id)
            album_title = album_obj.title if album_obj else None

            analysis_data[album_id] = {
                "album_title": album_title,
                "avg_rank": round(stats['avg_position'], 2) if stats['avg_position'] is not None else None,
                "std_dev_rank": round(std_dev, 2),
                "votes": stats['count']
            }

        # extremos nacionais
        consensus_album_id = min(analysis_data, key=lambda k: analysis_data[k]['avg_rank']) if analysis_data else None
        polarization_album_id = max(analysis_data, key=lambda k: analysis_data[k]['std_dev_rank']) if analysis_data else None

        # salva/atualiza CountryGlobalRanking
        ranking_obj, created = CountryGlobalRanking.objects.update_or_create(
            country_name=country,
            defaults={
                'user_count': user_count,
                'consensus_album': album_map.get(consensus_album_id),
                'polarization_album': album_map.get(polarization_album_id),
                'analysis_data': analysis_data
            }
        )
        print(f"✅ Ranking de {country} {'criado' if created else 'atualizado'}. Usuários: {user_count}")

        # ANALISE DE TRACKS POR PAÍS
        member_track_rankings = TrackRanking.objects.filter(
            user_id__in=country_user_ids
        ).select_related('track')

        track_positions = defaultdict(list)
        for ranking in member_track_rankings:
            track_positions[ranking.track_id].append(ranking.position)

        global_consensus_track_id = None
        min_global_avg = float('inf')

        # estrutura temporária: album_id (int) -> { "top_track_id": id, "tracks": { track_id: analysis } }
        track_analysis_by_album = defaultdict(lambda: {"top_track_id": None, "tracks": {}})
        polarization_track_id_by_album = {}

        for track_id, positions in track_positions.items():
            track_obj = track_map.get(track_id)
            if not track_obj:
                continue

            avg_position = statistics.mean(positions)
            votes = len(positions)
            try:
                std_dev = statistics.stdev(positions) if votes > 1 else 0.0
            except statistics.StatisticsError:
                std_dev = 0.0

            analysis = {
                "track_title": track_obj.title,
                "album_id": track_obj.album_id,
                "avg_rank": round(avg_position, 2),
                "std_dev_rank": round(std_dev, 2),
                "votes": votes
            }

            # consenso global (música com menor avg)
            if avg_position < min_global_avg:
                min_global_avg = avg_position
                global_consensus_track_id = track_id

            album_id = analysis['album_id']
            track_analysis_by_album[album_id]["tracks"][track_id] = analysis

            # top track por álbum (menor avg_rank)
            current_top = track_analysis_by_album[album_id]["top_track_id"]
            if current_top is None or analysis['avg_rank'] < track_analysis_by_album[album_id]["tracks"][current_top]['avg_rank']:
                track_analysis_by_album[album_id]["top_track_id"] = track_id

            # polarização por álbum (maior std_dev)
            current_polarized = polarization_track_id_by_album.get(album_id)
            cur_std = track_analysis_by_album[album_id]["tracks"].get(current_polarized, {}).get('std_dev_rank', -1)
            if (current_polarized is None) or (analysis['std_dev_rank'] > cur_std):
                polarization_track_id_by_album[album_id] = track_id

        # serializa chaves como strings para JSONField
        serialized_track_analysis = {}
        for a_id, info in track_analysis_by_album.items():
            tracks_serialized = {str(tid): tinfo for tid, tinfo in info["tracks"].items()}
            serialized_track_analysis[str(a_id)] = {
                "top_track_id": info["top_track_id"],
                "tracks": tracks_serialized
            }

        # atualiza ranking_obj.analysis_data com segurança (cópia)
        existing = ranking_obj.analysis_data or {}
        existing = dict(existing)  # copia para evitar mutação inesperada
        existing['track_analysis_by_album'] = serialized_track_analysis
        existing['track_polarization_by_album'] = {str(k): v for k, v in polarization_track_id_by_album.items()}
        ranking_obj.analysis_data = existing
        ranking_obj.global_consensus_track_id = global_consensus_track_id
        ranking_obj.save()

        print(f"✅ Ranking de {country} atualizado (Álbuns e Tracks).")

    print("--- CÁLCULO GLOBAL FINALIZADO ---")

def _get_model(app_label: str, model_name: str):
    try:
        return apps.get_model(app_label, model_name)
    except LookupError:
        return None


def calculate_group_internal_coherence(group) -> float:
    """
    CIGG (0..100). Implementação fixa para os testes:
    - usa AlbumRanking e GroupRanking do app 'rankings'
    - MAX_DIFFERENCE = 5 (constante)
    - ignora álbuns com < 2 votos
    - se houver múltiplos votos user+album, a última entrada (order by id) sobrescreve
    """
    try:
        AlbumRanking = apps.get_model('rankings', 'AlbumRanking')
        GroupRanking = apps.get_model('rankings', 'GroupRanking')
    except LookupError:
        return 0.0

    matched_album_ids = list(GroupRanking.objects.filter(group=group).values_list('album_id', flat=True))
    if not matched_album_ids:
        return 0.0

    member_ids = list(group.members.values_list('id', flat=True))
    if len(member_ids) < 2:
        return 0.0

    # pegamos rows ordenadas por id para que a última entrada sobrescreva
    rows = AlbumRanking.objects.filter(
        user_id__in=member_ids,
        album_id__in=matched_album_ids
    ).order_by('id').values_list('user_id', 'album_id', 'position')

    rankings_by_album: Dict[int, Dict[int, float]] = {}
    for user_id, album_id, pos in rows:
        try:
            position = float(pos)
        except Exception:
            continue
        # atribuição sobrescreve entradas anteriores com a mesma (user,album)
        rankings_by_album.setdefault(album_id, {})[user_id] = position

    MAX_DIFFERENCE = 5.0

    total_similarity = 0.0
    total_pairs = 0
    debug = []

    for album_id, umap in rankings_by_album.items():
        if len(umap) < 2:
            debug.append((album_id, "ignored_single_vote"))
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

        debug.append((album_id, album_sum, album_comps))
        total_similarity += album_sum
        total_pairs += album_comps

    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("CIGG debug group=%s matched_albums=%s", getattr(group, "id", group), matched_album_ids)
        for d in debug:
            logger.debug(" album debug: %s", d)
        logger.debug(" total_similarity=%s total_pairs=%s MAX_DIFFERENCE=%s", total_similarity, total_pairs, MAX_DIFFERENCE)

    if total_pairs == 0:
        return 0.0

    ratio = total_similarity / total_pairs
    return ratio * 100.0