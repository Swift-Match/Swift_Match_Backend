import pytest
from rest_framework.exceptions import ValidationError
from apps.social.models import Friendship, Group, GroupMembership, GroupInvite
from apps.social.serializers import (
    FriendshipRequestSerializer, 
    AddMemberSerializer,
    GroupInviteCreateSerializer,
    GroupMemberSerializer
)

# --- FIXTURES DE FÁBRICA ---

@pytest.fixture
def user_factory(django_user_model):
    def create_user(**kwargs):
        # Usa create_user para garantir que senhas sejam hasheadas corretamente
        return django_user_model.objects.create_user(**kwargs)
    return create_user

# --- FIXTURES DE USUÁRIO ESPECÍFICAS ---

@pytest.fixture
def user_a(user_factory):
    return user_factory(username='user_a_test', email='a_test@test.com', password='password123')

@pytest.fixture
def user_b(user_factory):
    return user_factory(username='user_b_test', email='b_test@test.com', password='password123')

@pytest.fixture
def user_c(user_factory):
    return user_factory(username='user_c_test', email='c_test@test.com', password='password123')

# --- FIXTURES DE GRUPO ---

@pytest.fixture
def group_owned_by_a(user_a):
    """Cria um grupo e adiciona o owner como membro/admin."""
    group = Group.objects.create(name='Grupo A', owner=user_a)
    GroupMembership.objects.create(user=user_a, group=group, is_admin=True)
    return group

@pytest.fixture
def group_member_b(group_owned_by_a, user_b):
    """Adiciona user_b como membro normal ao Grupo A."""
    GroupMembership.objects.create(user=user_b, group=group_owned_by_a, is_admin=False)
    return group_owned_by_a

# --- TESTES ---

@pytest.mark.django_db
class TestFriendshipRequestSerializer:
    
    # Teste Unitário - Criação válida
    def test_valid_creation(self, user_a, user_b):
        """Teste: Criação bem-sucedida de um pedido de amizade."""
        data = {'to_user': user_b.id}
        # Mock simples do objeto request
        mock_request = type('Request', (object,), {'user': user_a})
        context = {'request': mock_request} 
        
        serializer = FriendshipRequestSerializer(data=data, context=context)
        assert serializer.is_valid(raise_exception=True)
        
        friendship = serializer.save(from_user=user_a) # Simula perform_create
        assert friendship.from_user == user_a
        assert friendship.to_user == user_b
        assert friendship.status == 'pending'

    # Teste de Validação Parametrizado (Caso 1: Enviar para si mesmo)
    def test_validation_send_to_self(self, user_a):
        """Teste: Não permite enviar pedido de amizade para si mesmo."""
        data = {'to_user': user_a.id}
        mock_request = type('Request', (object,), {'user': user_a})
        context = {'request': mock_request}
        
        serializer = FriendshipRequestSerializer(data=data, context=context)
        
        with pytest.raises(ValidationError) as excinfo:
            serializer.is_valid(raise_exception=True)
            
        assert "Você não pode enviar um pedido de amizade para você mesmo." in str(excinfo.value)

    # Teste de Validação Parametrizado (Caso 2: Já são amigos)
    def test_validation_already_friends(self, user_a, user_b):
        """Teste: Não permite enviar se a amizade já foi aceita (A->B)."""
        Friendship.objects.create(from_user=user_a, to_user=user_b, status='accepted')
        
        data = {'to_user': user_b.id}
        mock_request = type('Request', (object,), {'user': user_a})
        context = {'request': mock_request}
        
        serializer = FriendshipRequestSerializer(data=data, context=context)

        with pytest.raises(ValidationError) as excinfo:
            serializer.is_valid(raise_exception=True)
            
        assert "Vocês já são amigos." in str(excinfo.value)
        
    # Teste de Validação Parametrizado (Caso 3: Pedido pendente já enviado)
    def test_validation_request_already_sent(self, user_a, user_b):
        """Teste: Não permite enviar se o pedido (A->B) já está pendente."""
        Friendship.objects.create(from_user=user_a, to_user=user_b, status='pending')
        
        data = {'to_user': user_b.id}
        mock_request = type('Request', (object,), {'user': user_a})
        context = {'request': mock_request}
        
        serializer = FriendshipRequestSerializer(data=data, context=context)

        with pytest.raises(ValidationError) as excinfo:
            serializer.is_valid(raise_exception=True)
            
        assert "Você já enviou um pedido para este usuário." in str(excinfo.value)

    # Teste de Validação Parametrizado (Caso 4: Pedido pendente recebido)
    def test_validation_request_received(self, user_a, user_b):
        """Teste: Não permite enviar (A->B) se B já enviou (B->A)."""
        Friendship.objects.create(from_user=user_b, to_user=user_a, status='pending')
        
        data = {'to_user': user_b.id}
        mock_request = type('Request', (object,), {'user': user_a})
        context = {'request': mock_request}
        
        serializer = FriendshipRequestSerializer(data=data, context=context)

        with pytest.raises(ValidationError) as excinfo:
            serializer.is_valid(raise_exception=True)
            
        assert "Este usuário já te enviou um pedido. Aceite-o em vez de enviar outro." in str(excinfo.value)

# ---------------------------------------------------------------------------------------

@pytest.mark.django_db
class TestAddMemberSerializer:
    
    # Teste Unitário - Criação válida
    def test_valid_member_to_add(self, group_owned_by_a, user_c):
        """Teste: Garante que um novo usuário (C) pode ser validado para adição."""
        data = {'user_id': user_c.id}
        context = {'group': group_owned_by_a} # O grupo é passado no contexto da View
        
        serializer = AddMemberSerializer(data=data, context=context)
        assert serializer.is_valid(raise_exception=True)
        assert serializer.validated_data['user_id'] == user_c

    # Teste de Validação Parametrizado (Caso 1: Já é membro)
    def test_validation_already_member(self, group_member_b, user_b):
        """Teste: Não permite adicionar um usuário que já é membro (user_b)."""
        data = {'user_id': user_b.id}
        context = {'group': group_member_b} # group_member_b já tem user_b como membro
        
        serializer = AddMemberSerializer(data=data, context=context)
        
        with pytest.raises(ValidationError) as excinfo:
            serializer.is_valid(raise_exception=True)
            
        assert "Este usuário já é membro do grupo." in str(excinfo.value)
        
    # Teste de Validação Parametrizado (Caso 2: ID não existe)
    def test_validation_user_does_not_exist(self, group_owned_by_a):
        """Teste: ID de usuário inválido deve levantar a mensagem de erro padrão."""
        data = {'user_id': 999999} # ID inexistente
        context = {'group': group_owned_by_a}
        
        serializer = AddMemberSerializer(data=data, context=context)
        
        with pytest.raises(ValidationError) as excinfo:
            serializer.is_valid(raise_exception=True)
            
        # Verifica a mensagem customizada de erro do PrimaryKeyRelatedField
        assert 'Usuário com este ID não existe.' in str(excinfo.value)

# ---------------------------------------------------------------------------------------

@pytest.mark.django_db
class TestGroupInviteCreateSerializer:

    # Teste Unitário - Criação válida
    def test_valid_invite_creation(self, group_owned_by_a, user_c):
        """Teste: Criação bem-sucedida de um GroupInvite (A convida C)."""
        data = {'group': group_owned_by_a.id, 'receiver': user_c.id}
        serializer = GroupInviteCreateSerializer(data=data)
        
        assert serializer.is_valid(raise_exception=True)
        # O sender é preenchido na View, o save() abaixo simula:
        invite = serializer.save(sender=group_owned_by_a.owner) 
        
        assert invite.group == group_owned_by_a
        assert invite.receiver == user_c
        assert invite.status == 'PENDING'

    # Teste de Validação Parametrizado (Caso 1: Receiver já é membro)
    def test_validation_receiver_already_member(self, group_member_b, user_b, user_a):
        """Teste: Não permite convidar um usuário que já é membro (user_b)."""
        data = {'group': group_member_b.id, 'receiver': user_b.id}
        serializer = GroupInviteCreateSerializer(data=data)
        
        with pytest.raises(ValidationError) as excinfo:
            serializer.is_valid(raise_exception=True)
            
        assert "Este usuário já é membro deste grupo." in str(excinfo.value)

    # Teste de Validação Parametrizado (Caso 2: Convite pendente já existe)
    def test_validation_pending_invite_exists(self, group_owned_by_a, user_c, user_a):
        """Teste: Não permite criar novo convite se um PENDENTE já existe para o mesmo grupo/receiver."""
        # Cria o primeiro convite PENDENTE
        GroupInvite.objects.create(
            sender=user_a, group=group_owned_by_a, receiver=user_c, status='PENDING'
        )
        
        data = {'group': group_owned_by_a.id, 'receiver': user_c.id}
        serializer = GroupInviteCreateSerializer(data=data)
        
        with pytest.raises(ValidationError) as excinfo:
            serializer.is_valid(raise_exception=True)
            
        # Verifica se a mensagem de erro é a personalizada OU a padrão do DRF (unique_together)
        error_msg = str(excinfo.value)
        assert "Já existe um convite pendente para este usuário neste grupo." in error_msg or \
               "unique set" in error_msg or \
               "unique" in error_msg
        
    # Teste de Validação Parametrizado (Caso 3: Convite REJEITADO permite novo convite)
    def test_validation_rejected_invite_allows_new(self, group_owned_by_a, user_c, user_a):
        """Teste: Permite criar um novo convite se o anterior foi REJEITADO."""
        # Cria o convite REJEITADO
        GroupInvite.objects.create(
            sender=user_a, group=group_owned_by_a, receiver=user_c, status='REJECTED'
        )
        
        data = {'group': group_owned_by_a.id, 'receiver': user_c.id}
        serializer = GroupInviteCreateSerializer(data=data)
        
        # Deve passar
        assert serializer.is_valid(raise_exception=True) 
        assert GroupInvite.objects.count() == 1 # Apenas o REJECTED existe antes de salvar o novo

        # Salva o novo PENDENTE
        serializer.save(sender=user_a)
        assert GroupInvite.objects.count() == 2