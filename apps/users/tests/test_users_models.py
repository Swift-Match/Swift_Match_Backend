import pytest


@pytest.mark.django_db
class TestUserModel:

    def test_user_str_representation(self, create_user):
        """Teste unitário: verifica se o __str__ retorna o username"""
        user = create_user(username="taylor_fan", email="ts@test.com", password="123")
        assert str(user) == "taylor_fan"

    def test_user_default_theme(self, create_user):
        """Teste unitário: verifica se o tema padrão é aplicado corretamente"""
        user = create_user(username="midnights_lover", password="123")
        assert user.tema == "MIDNIGHTS"
        assert user.country == ""
