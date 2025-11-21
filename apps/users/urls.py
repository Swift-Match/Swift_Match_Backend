from django.urls import path
from .views import RegisterUserView, UserProfileView

urlpatterns = [
    # POST para /api/users/register/
    path('register/', RegisterUserView.as_view(), name='user-register'),
    path('me/', UserProfileView.as_view(), name='user-profile'),
]