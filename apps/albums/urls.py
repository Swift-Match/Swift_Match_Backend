from django.urls import path
from .views import AlbumListView

urlpatterns = [
    path('all/', AlbumListView.as_view(), name='album-list-all'),
]