from django.urls import path
from .views import (
    GroupListCreateView, 
    GroupDetailView, 
    GroupAddMemberView,
    FriendshipRequestListView,
    FriendshipManageView,
    GroupInviteManageView,
    FriendListView
)


urlpatterns = [
    # GET: Lista meus grupos; POST: Cria novo grupo
    path('groups/', GroupListCreateView.as_view(), name='group-list-create'),
    
    # GET: Detalhes do grupo (ex: /api/social/groups/1/)
    path('groups/<int:pk>/', GroupDetailView.as_view(), name='group-detail'),
    
    # POST: Adiciona membro ao grupo (ex: /api/social/groups/1/add-member/)
    path('groups/<int:pk>/add-member/', GroupAddMemberView.as_view(), name='group-add-member'),

    # GET: Lista pedidos recebidos (pendentes); POST: Envia um novo pedido
    path('friendships/', FriendshipRequestListView.as_view(), name='friendship-request-list-create'),
    
    # POST: Aceita ou rejeita o pedido (Ex: /api/social/friendships/123/accept/)
    path('friendships/<int:pk>/<str:action>/', FriendshipManageView.as_view(), name='friendship-manage'),

    # Rota para aceitar ou rejeitar um convite de grupo
    path(
        'groups/invites/<int:pk>/<str:action>/', 
        GroupInviteManageView.as_view(), 
        name='group-invite-manage'
    ),

    # Rota para /api/social/friends/ (ou similar, dependendo do seu config/urls.py)
    path('friends/', FriendListView.as_view(), name='friend-list'),
]