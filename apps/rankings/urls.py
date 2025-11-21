from django.urls import path, include # <--- ADICIONADO: include
from rest_framework.routers import DefaultRouter # <--- NOVO: Importa o Router

from .views import (
    AlbumRankingView, 
    TrackRankingView, 
    CompatibilityView,
    GroupCompatibilityView,
    GroupTrackCompatibilityView,
    GlobalRankingListView,
    TrackCompatibilityView,
    GroupRankingViewSet,
)

# 1. Configurar o Router para o ViewSet
router = DefaultRouter()
# Isso mapeia as operações CRUD do GroupRankingViewSet para /group_rankings/ e /group_rankings/{pk}/
router.register(r'group_rankings', GroupRankingViewSet, basename='group-ranking') 


urlpatterns = [
    # Rotas de Ranking Individual
    path('albums/', AlbumRankingView.as_view(), name='album-ranking'),
    path('tracks/<int:album_id>/', TrackRankingView.as_view(), name='track-ranking-by-album'),
    
    # Rotas de Compatibilidade
    path('compare/albums/<int:target_user_id>/', CompatibilityView.as_view(), name='album-compatibility'),
    path('compare/groups/<int:group_id>/', GroupCompatibilityView.as_view(), name='group-compatibility'),
    path(
        'compare/tracks/<int:target_user_id>/album/<int:album_id>/', 
        TrackCompatibilityView.as_view(), 
        name='track-compatibility-duo'
    ),
    path(
        'compare/groups/<int:group_id>/tracks/<int:album_id>/', 
        GroupTrackCompatibilityView.as_view(), 
        name='group-track-compatibility'
    ),
    
    # Rotas de Ranking Global
    path('global/', GlobalRankingListView.as_view(), name='global-ranking-list'),
    
    # 2. Inclusão das rotas do ViewSet (Substitui a linha errada)
    path('', include(router.urls)), 
    # Observação: Colocando o include no path vazio (''), garante que todas as URLs do ViewSet
    # comecem a partir do prefixo definido no config/urls.py (ex: /api/rankings/group_rankings/)
]