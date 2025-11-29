from django.urls import path
from .views import (
    RegisterUserView, 
    UserProfileView, 
    UserThemeUpdateView, 
    UserThemeListView,
    UserFirstLoginView,
    UserThemeRetrieveView,
    OtherUserProfileView
)

urlpatterns = [
    path('register/', RegisterUserView.as_view(), name='user-register'),
    path('me/', UserProfileView.as_view(), name='user-profile'),
    path('me/theme/', UserThemeUpdateView.as_view(), name='user-update-theme'),  
    path('themes/', UserThemeListView.as_view(), name='user-list-themes'),       
    path('me/first-login/', UserFirstLoginView.as_view(), name='user-first-login'),
    path('me/current-theme/', UserThemeRetrieveView.as_view(), name='user-get-current-theme'),
    path('<int:pk>/', OtherUserProfileView.as_view(), name='other-user-profile'),
]


