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
    
    
]