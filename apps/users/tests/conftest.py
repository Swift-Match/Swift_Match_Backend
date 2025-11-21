import pytest
from rest_framework.test import APIClient

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def create_user(db, django_user_model):
    """Fixture para criar usuários dinamicamente nos testes"""
    def make_user(**kwargs):
        return django_user_model.objects.create_user(**kwargs)
    return make_user