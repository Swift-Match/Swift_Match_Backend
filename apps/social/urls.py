from django.urls import path
from .views import (
    GroupListCreateView, 
    GroupDetailView, 
    GroupAddMemberView,
    FriendshipRequestListView,
    FriendshipManageView,
    GroupInviteManageView,
    FriendListView,
    UserSearchView,
    SendFriendshipRequestToUserView
)


urlpatterns = [
    path('groups/', GroupListCreateView.as_view(), name='group-list-create'),
    
    path('groups/<int:pk>/', GroupDetailView.as_view(), name='group-detail'),
    
    path('groups/<int:pk>/add-member/', GroupAddMemberView.as_view(), name='group-add-member'),

    path('friendships/', FriendshipRequestListView.as_view(), name='friendship-request-list-create'),
    
    path('friendships/<int:pk>/<str:action>/', FriendshipManageView.as_view(), name='friendship-manage'),

    path(
        'groups/invites/<int:pk>/<str:action>/', 
        GroupInviteManageView.as_view(), 
        name='group-invite-manage'
    ),

    path('friends/', FriendListView.as_view(), name='friend-list'),

    path('users/<int:pk>/request-friendship/', SendFriendshipRequestToUserView.as_view(), name='send-friendship-request-to-user'),

    path('users/search/', UserSearchView.as_view(), name='user-search'),
]