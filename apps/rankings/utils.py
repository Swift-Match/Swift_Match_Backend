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


def get_album_map():
    return {album.id: album for album in Album.objects.all()}

def calculate_global_ranking():
    """
    Executa o cálculo do ranking de álbuns para todos os países
    onde há pelo menos 2 usuários ativos.
    """
    print("--- INICIANDO CÁLCULO GLOBAL DE RANKING ---")
    
    # 1. Agrupar usuários por país e contar quantos há em cada país
    # Filtrar apenas países com pelo menos 2 usuários com ranking submetido
    countries_data = User.objects.filter(
        # Certifica-se que o usuário rankeou algo
        albumranking__isnull=False,
        # Você pode querer adicionar um filtro de 'is_active' se tiver
    ).values('country').annotate(
        user_count=Count('id', distinct=True)
    ).filter(user_count__gte=2) # Pelo menos 2 usuários para análise

    album_map = get_album_map()

    track_map = {track.id: track for track in Track.objects.all()}

    for country_info in countries_data:
        country = country_info['country']
        user_count = country_info['user_count']
        
        # 2. Encontrar todos os rankings de álbuns para este país
        country_user_ids = User.objects.filter(country=country).values_list('id', flat=True)

        # Agregação de todos os rankings de álbuns dos usuários do país
        album_stats = AlbumRanking.objects.filter(
            user_id__in=country_user_ids
        ).values('album_id').annotate(
            avg_position=Avg('position'),
            # Desvio padrão para medir a polarização (StdDev requer PostgreSQL, senão use estatísticas em Python)
            # Se você usa PostgreSQL:
            # std_dev_position=StdDev('position'),
            
            # Se não usa PostgreSQL (fallback em Python):
            count=Count('position')
            
        ).order_by('avg_position') # O menor AVG é o álbum mais votado

        # 3. Processamento para Polarização (Se não usar StdDev do ORM)
        full_positions = defaultdict(list)
        for ranking in AlbumRanking.objects.filter(user_id__in=country_user_ids):
             full_positions[ranking.album_id].append(ranking.position)

        # 4. Compilar Análise Detalhada
        analysis_data = {}
        
        for stats in album_stats:
            album_id = stats['album_id']
            positions = full_positions[album_id]
            
            if len(positions) > 1:
                # Calcula Desvio Padrão usando a biblioteca Python (para compatibilidade)
                std_dev = statistics.stdev(positions)
            else:
                std_dev = 0
                
            analysis_data[album_id] = {
                "album_title": album_map.get(album_id).title,
                "avg_rank": round(stats['avg_position'], 2),
                "std_dev_rank": round(std_dev, 2), # Polarização!
                "votes": stats['count'] 
            }

        # 5. Encontrar os Extremos Nacionais
        
        # Consenso (Menor Média)
        consensus_album_id = min(analysis_data, key=lambda k: analysis_data[k]['avg_rank']) if analysis_data else None
        
        # Polarização (Maior Desvio Padrão)
        polarization_album_id = max(analysis_data, key=lambda k: analysis_data[k]['std_dev_rank']) if analysis_data else None
        
        # 6. Salvar ou Atualizar o Model Global
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

        # 7. ANÁLISE DE MÚSICAS POR PAÍS
        
        # 7.1. Busca de Posições (Otimizada para o país atual)
        member_track_rankings = TrackRanking.objects.filter(
            user_id__in=country_user_ids
        ).select_related('track')
        
        track_positions = defaultdict(list)
        for ranking in member_track_rankings:
            # Garante que o track_id está correto e agrupado pelo país
            track_positions[ranking.track_id].append(ranking.position)

        # 7.2. Cálculo de Média e Desvio Padrão por Música
        
        global_consensus_track_id = None
        min_global_avg = float('inf')
        
        track_analysis_by_album = defaultdict(lambda: {"top_track_id": None, "tracks": {}})
        polarization_track_id_by_album = {}

        for track_id, positions in track_positions.items():
            if not track_map.get(track_id): continue # Ignora se a track não foi encontrada
            
            avg_position = statistics.mean(positions)
            votes = len(positions)
            
            try:
                std_dev = statistics.stdev(positions)
            except statistics.StatisticsError:
                std_dev = 0
                
            analysis = {
                "track_title": track_map[track_id].title,
                "album_id": track_map[track_id].album_id,
                "avg_rank": round(avg_position, 2),
                "std_dev_rank": round(std_dev, 2), 
                "votes": votes
            }

            # 7.3. Determinar Consenso Global (Música favorita de TODOS os álbuns)
            if avg_position < min_global_avg:
                min_global_avg = avg_position # Corrigi a variável
                global_consensus_track_id = track_id

            # 7.4. Determinar Consenso e Polarização POR ÁLBUM
            album_id = analysis['album_id']
            track_analysis_by_album[album_id]["tracks"][track_id] = analysis
            
            # Consenso por Álbum
            if (track_analysis_by_album[album_id]["top_track_id"] is None or 
                analysis['avg_rank'] < track_analysis_by_album[album_id]["tracks"][track_analysis_by_album[album_id]["top_track_id"]]['avg_rank']):
                
                track_analysis_by_album[album_id]["top_track_id"] = track_id
                
            # Polarização por Álbum (Maior Desvio Padrão)
            current_polarized_track_id = polarization_track_id_by_album.get(album_id)
            if (current_polarized_track_id is None or 
                analysis['std_dev_rank'] > track_analysis_by_album[album_id]["tracks"][current_polarized_track_id]['std_dev_rank']):
                
                polarization_track_id_by_album[album_id] = track_id

        # 8. ATUALIZAR MODEL GLOBAL COM DADOS DE TRACKS
        
        # O objeto 'ranking_obj' já está definido no passo 6 (álbuns), mas para garantir
        # a atomicidade (e evitar dois saves), você pode fazer a atualização no final.
        # Vamos usar o 'ranking_obj' que já foi criado/atualizado na fase 1.
        
        # Adiciona a análise de tracks ao JSON existente
        ranking_obj.analysis_data['track_analysis_by_album'] = dict(track_analysis_by_album)
        ranking_obj.analysis_data['track_polarization_by_album'] = polarization_track_id_by_album
        
        # Define o campo Foreign Key
        ranking_obj.global_consensus_track_id = global_consensus_track_id
        
        ranking_obj.save()

        print(f"✅ Ranking de {country} atualizado (Álbuns e Tracks).")

    print("--- CÁLCULO GLOBAL FINALIZADO ---")

def get_group_preference_vector(group):
    """Calcula o vetor de preferência (ranking médio) para um grupo."""
    
    member_ids = group.members.values_list('id', flat=True)
    
    group_rankings = UserRanking.objects.filter(
        user_id__in=member_ids
    ).values('track').annotate(
        avg_ranking=Avg('ranking')
    )
    
    # Retorna {track_id: ranking_medio}
    return {
        ranking['track']: ranking['avg_ranking']
        for ranking in group_rankings
    }

def calculate_group_internal_coherence(group) -> float:
    """
    Calcula a Taxa de Compatibilidade Interna Geral do Grupo (CIGG)
    com base na média da similaridade dos rankings de todos os membros
    para os álbuns que o grupo 'matchou'.
    """
    
    # 1. Encontrar os Álbuns Matchados pelo Grupo
    # Substitua 'GroupAlbumMatch' pelo nome real do seu modelo de match de álbum
    try:
        matched_album_ids = GroupRanking.objects.filter(
            group=group
        ).values_list('album_id', flat=True)
    except NameError:
         # Se GroupAlbumMatch não existe, assumimos que a lista de IDs de álbum é passada
         # Para este exemplo, vamos simular que não há álbuns matchados.
         return 0.0
         
    if not matched_album_ids:
        return 0.0

    member_ids = group.members.values_list('id', flat=True)
    if len(member_ids) < 2:
        return 0.0 # Coerência de grupo não se aplica a 0 ou 1 pessoa.

    # 2. Obter Rankings de todos os Membros para esses Álbuns
    # Assumindo que UserRanking armazena o ranking de um Álbum/Track
    all_rankings = UserRanking.objects.filter(
        user_id__in=member_ids,
        album_id__in=matched_album_ids 
        # ATENÇÃO: Se UserRanking é para Track, use Track em vez de Album
    ).values('user', 'album', 'ranking')
    
    # Organiza os rankings por álbum e usuário
    rankings_by_album = {}
    for r in all_rankings:
        album_id = r['album']
        user_id = r['user']
        ranking = r['ranking']
        
        if album_id not in rankings_by_album:
            rankings_by_album[album_id] = {}
        
        rankings_by_album[album_id][user_id] = ranking

    total_coherence_score = 0
    total_comparisons = 0
    MAX_DIFFERENCE = 5  # Diferença máxima entre rankings (ex: 5 - 0)

    # 3. Calcular a Coerência Média (Comparação par a par)
    
    for album_id, user_rankings in rankings_by_album.items():
        # Obtém a lista de rankings para o álbum, apenas de quem votou
        ranked_users = list(user_rankings.keys())
        
        # Compara cada par de usuários que ranquearam o álbum
        for i in range(len(ranked_users)):
            for j in range(i + 1, len(ranked_users)):
                user1_ranking = user_rankings[ranked_users[i]]
                user2_ranking = user_rankings[ranked_users[j]]
                
                # Diferença de Ranking (0 a 5)
                difference = abs(user1_ranking - user2_ranking)
                
                # Converte Incompatibilidade para Similaridade (0.0 a 1.0)
                similarity = 1.0 - (difference / MAX_DIFFERENCE)
                
                total_coherence_score += similarity
                total_comparisons += 1

    if total_comparisons == 0:
        return 0.0
        
    # CIGG é a média de similaridade de todos os pares em todos os álbuns
    cigg_ratio = total_coherence_score / total_comparisons
    
    # Retorna porcentagem (0.0 a 100.0)
    return cigg_ratio * 100