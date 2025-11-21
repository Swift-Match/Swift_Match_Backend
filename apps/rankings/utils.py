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

def calculate_album_compatibility(user_a, user_b):
    """
    Calcula a compatibilidade do ranking de álbuns entre dois usuários.
    Retorna (percentual_compatibilidade, num_shared_albums).
    """
    if user_a.id == user_b.id:
        return 100, 0

    rankings_a = AlbumRanking.objects.filter(user=user_a).order_by('album_id')
    rankings_b = AlbumRanking.objects.filter(user=user_b).order_by('album_id')

    shared_rankings = rankings_a.filter(album__in=rankings_b.values('album')).values(
        'album_id', 
        'position', 
        user_b_position=F('album__user_rankings__position')
    ).filter(album__user_rankings__user=user_b)
    
    num_shared_albums = shared_rankings.count()

    if num_shared_albums == 0:
        return 0, 0

    # 1. Métrica: Média da Diferença Absoluta por Álbum
    avg_abs_diff = sum(abs(item['position'] - item['user_b_position']) for item in shared_rankings) / num_shared_albums
    
    # 2. Conversão para Porcentagem (0% se a diferença média for >= 5 posições)
    max_diff_reference = 5 
    compatibility_percent = max(0, 100 * (1 - (avg_abs_diff / max_diff_reference)))
    
    min_sum = float('inf')
    max_sum = float('-inf')
    max_diff = -1
    min_diff = float('inf')
    
    favorite_album = None
    least_favorite_album = None
    most_divergent_album = None
    most_concordant_album = None
    
    avg_abs_diff = 0
    
    for item in shared_rankings:
        pos_a = item['position']
        pos_b = item['user_b_position']
        
        sum_pos = pos_a + pos_b
        abs_diff = abs(pos_a - pos_b)
        avg_abs_diff += abs_diff

        # 1. Favorito Comum (Menor Soma de Posições)
        if sum_pos < min_sum:
            min_sum = sum_pos
            favorite_album = item['album_id'] 

        # 2. Menos Favorito Comum (Maior Soma de Posições)
        if sum_pos > max_sum:
            max_sum = sum_pos
            least_favorite_album = item['album_id']

        # 3. Maior Divergência (Maior Diferença Absoluta)
        if abs_diff > max_diff:
            max_diff = abs_diff
            most_divergent_album = item['album_id']

        # 4. Maior Concordância (Menor Diferença Absoluta)
        if abs_diff < min_diff:
            min_diff = abs_diff
            most_concordant_album = item['album_id']

    avg_abs_diff /= num_shared_albums
    
    max_diff_reference = 5 
    compatibility_percent = max(0, 100 * (1 - (avg_abs_diff / max_diff_reference)))
    
    analysis_report = {
        "favorite_album_id": favorite_album,
        "least_favorite_album_id": least_favorite_album,
        "most_divergent_album_id": most_divergent_album,
        "most_concordant_album_id": most_concordant_album,
        "max_position_difference": max_diff,
        "min_position_difference": min_diff,
    }
    
    return round(compatibility_percent, 2), num_shared_albums, analysis_report

def calculate_track_compatibility(user_a, user_b, album):
    """
    Calcula a compatibilidade de ranking de MÚSICAS de um álbum específico
    entre dois usuários, e gera o relatório de análise.
    Retorna (percentual_compatibilidade, num_shared_tracks, analysis_report).
    """
    if user_a.id == user_b.id:
        return 100, 0, None

    # Filtra os rankings de músicas APENAS para o álbum fornecido
    rankings_a = AlbumRanking.objects.filter(
        user=user_a, 
        track__album=album
    ).order_by('track_id')
    
    rankings_b = AlbumRanking.objects.filter(
        user=user_b, 
        track__album=album
    ).order_by('track_id')

    # Fazer JOIN para encontrar apenas as músicas rankeadas por AMBOS
    shared_rankings = rankings_a.filter(
        track__in=rankings_b.values('track')
    ).values(
        'track_id', 
        'position', 
        user_b_position=F('track__user_rankings__position')
    ).filter(track__user_rankings__user=user_b)
    
    num_shared_tracks = shared_rankings.count()

    if num_shared_tracks == 0:
        # Se não houver músicas em comum rankeadas neste álbum, retorna 0
        return 0, 0, None

    # --- Lógica de Análise (Métricas) ---
    min_sum = float('inf')
    max_sum = float('-inf')
    max_diff = -1
    min_diff = float('inf')
    
    favorite_track = None
    least_favorite_track = None
    most_divergent_track = None
    most_concordant_track = None
    
    avg_abs_diff = 0
    
    for item in shared_rankings:
        pos_a = item['position']
        pos_b = item['user_b_position']
        
        sum_pos = pos_a + pos_b
        abs_diff = abs(pos_a - pos_b)
        avg_abs_diff += abs_diff

        # 1. Favorita Comum (Menor Soma de Posições)
        if sum_pos < min_sum:
            min_sum = sum_pos
            favorite_track = item['track_id'] 

        # 2. Menos Favorita Comum (Maior Soma de Posições)
        if sum_pos > max_sum:
            max_sum = sum_pos
            least_favorite_track = item['track_id']

        # 3. Maior Divergência (Maior Diferença Absoluta)
        if abs_diff > max_diff:
            max_diff = abs_diff
            most_divergent_track = item['track_id']

        # 4. Maior Concordância (Menor Diferença Absoluta)
        if abs_diff < min_diff:
            min_diff = abs_diff
            most_concordant_track = item['track_id']

    avg_abs_diff /= num_shared_tracks
    
    max_diff_reference = 5 # Mantemos a mesma referência de compatibilidade
    compatibility_percent = max(0, 100 * (1 - (avg_abs_diff / max_diff_reference)))
    
    analysis_report = {
        "favorite_track_id": favorite_track,
        "least_favorite_track_id": least_favorite_track,
        "most_divergent_track_id": most_divergent_track,
        "most_concordant_track_id": most_concordant_track,
        "max_position_difference": max_diff,
        "min_position_difference": min_diff,
    }
    
    return round(compatibility_percent, 2), num_shared_tracks, analysis_report


