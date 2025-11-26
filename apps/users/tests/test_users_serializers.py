import pytest
from apps.users.serializers import UserRegistrationSerializer
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.mark.django_db
class TestUserSerializer:

    def test_serializer_hashes_password(self):
        """Teste Unitário: Garante que o serializer usa create_user e hasheia a senha"""
        data = {
            "username": "security_test",
            "email": "sec@test.com",
            "password": "plain_password_123",
            "country": "BR",
            "first_name": "Sec"
        }
        serializer = UserRegistrationSerializer(data=data)
        assert serializer.is_valid()
        user = serializer.save()
        
        assert user.password != "plain_password_123"
        assert user.check_password("plain_password_123")

    @pytest.mark.parametrize("field, value, error_code", [
        ("username", "", "blank"),            # Username vazio retorna código 'blank'
        ("email", "not-an-email", "invalid"), # Email ruim retorna código 'invalid'
        ("password", "", "blank"),            # Senha vazia retorna código 'blank'
    ])
    def test_registration_serializer_invalid_data(self, field, value, error_code):
        """Teste Parametrizado: Valida campos obrigatórios e formatos"""
        data = {
            "username": "valid_user",
            "email": "valid@email.com",
            "password": "validpass123",
            "first_name": "Test"
        }
        # Sobrescreve o campo específico com o valor inválido
        data[field] = value
        
        serializer = UserRegistrationSerializer(data=data)
        
        assert not serializer.is_valid()
        
        # CORREÇÃO: Verificamos o atributo .code do objeto de erro, não a string da mensagem
        # serializer.errors[field][0] é um objeto ErrorDetail
        assert serializer.errors[field][0].code == error_code

    def test_serializer_read_only_fields(self, create_user):
        """Teste Unitário: Verifica campos calculados (friends/groups count)"""
        user = create_user(username="counter_test", password="123")
        
        serializer = UserRegistrationSerializer(user)
        data = serializer.data
        
        assert data['friends_count'] == 0
        assert data['groups_count'] == 0
        assert 'password' not in data