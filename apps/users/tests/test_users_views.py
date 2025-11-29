import pytest
from django.urls import reverse
from rest_framework import status


@pytest.mark.django_db
class TestUserViews:

    def test_register_user_integration(self, api_client):
        """Teste de Integração: Fluxo completo de cadastro"""
        url = reverse("user-register")
        data = {
            "username": "integration_user",
            "email": "int@test.com",
            "password": "strongpassword123",
            "country": "BR",
            "first_name": "Integration",
        }

        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["message"] == "Usuário criado com sucesso!"

        from django.contrib.auth import get_user_model

        assert get_user_model().objects.filter(username="integration_user").exists()

    def test_user_profile_unauthorized(self, api_client):
        """Teste de Integração: Tentar acessar perfil sem token"""
        url = reverse("user-profile")
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_user_profile_success(self, api_client, create_user):
        """Teste de Integração: Acessar perfil autenticado"""
        user = create_user(username="auth_user", password="123", email="auth@test.com")

        api_client.force_authenticate(user=user)

        url = reverse("user-profile")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["username"] == "auth_user"
        assert response.data["email"] == "auth@test.com"
