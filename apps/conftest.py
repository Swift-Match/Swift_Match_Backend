import pytest
from rest_framework.test import APIClient
from apps.albums.models import Album
from apps.tracks.models import Track
from apps.social.models import Group 

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def create_user(db, django_user_model):
    """Fixture para criar usuários dinamicamente nos testes"""
    def make_user(**kwargs):
        return django_user_model.objects.create_user(**kwargs)
    return make_user


@pytest.fixture
def user_fixture(create_user):
    """Cria um usuário de teste simples (usando a fixture create_user)."""
    return create_user(
        email='testuser@example.com',
        username='testuser',
        password='password123'
    )

@pytest.fixture
def album_fixture(db):
    """Cria um álbum de teste."""
    return Album.objects.create(
        title='Speak Now (Taylor\'s Version)',
        release_date='2023-07-07'
    )

@pytest.fixture
def track_fixture(db, album_fixture):
    """Cria uma música de teste associada ao álbum."""
    return Track.objects.create(
        album=album_fixture,
        title='Enchanted',
        track_number=10
    )

@pytest.fixture
def group_fixture(db, user_fixture):
    """Cria um grupo de teste."""
    return Group.objects.create(
        name='Grupo Alpha',
        owner=user_fixture
    )