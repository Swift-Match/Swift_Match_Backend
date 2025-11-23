from django.urls import path
from .views import (
    RegisterUserView, 
    UserProfileView, 
    UserThemeUpdateView, 
    UserThemeListView,
    UserFirstLoginView
)

urlpatterns = [
    # POST para /api/users/register/
    path('register/', RegisterUserView.as_view(), name='user-register'),
    path('me/', UserProfileView.as_view(), name='user-profile'),
    path('me/theme/', UserThemeUpdateView.as_view(), name='user-update-theme'),  # PUT/PATCH
    path('themes/', UserThemeListView.as_view(), name='user-list-themes'),       # GET
    path('me/first-login/', UserFirstLoginView.as_view(), name='user-first-login'),
]