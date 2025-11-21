import pytest
from django.db import transaction # <--- IMPORTANTE
from django.db.utils import IntegrityError
from django.utils import timezone

from apps.social.models import Friendship, Group, GroupMembership, GroupInvite
from apps.users.models import User

# Marca todos os testes neste módulo para usar o banco de dados
pytestmark = pytest.mark.django_db

# --- FIXTURE ESSENCIAL ---
@pytest.fixture
def user_factory(django_user_model):
    """Cria usuários dinamicamente para os testes."""
    def create_user(**kwargs):
        return django_user_model.objects.create_user(**kwargs)
    return create_user

# ======================================
# Testes do Modelo Friendship
# ======================================

class TestFriendshipModel:
    """Testa o modelo Friendship (Pedido de Amizade)."""

    def test_friendship_creation(self, user_factory):
        user1 = user_factory(username='Alice', password='123')
        user2 = user_factory(username='Bob', password='123')
        
        friendship = Friendship.objects.create(from_user=user1, to_user=user2)

        assert friendship.from_user == user1
        assert friendship.to_user == user2
        assert friendship.status == 'pending'
        assert str(friendship) == f"Pedido de {user1} para {user2} (pending)"

    def test_friendship_status_choices(self, user_factory):
        user1 = user_factory(username='Alice', password='123')
        user2 = user_factory(username='Bob', password='123')
        user3 = user_factory(username='Charlie', password='123')
        
        Friendship.objects.create(from_user=user1, to_user=user2, status='accepted')
        assert Friendship.objects.get(from_user=user1).status == 'accepted'
        
        Friendship.objects.create(from_user=user2, to_user=user3, status='rejected')
        assert Friendship.objects.get(from_user=user2, to_user=user3).status == 'rejected'

    def test_friendship_unique_together(self, user_factory):
        """Deve impedir a criação de pedidos duplicados."""
        user1 = user_factory(username='Alice', password='123')
        user2 = user_factory(username='Bob', password='123')
        
        # Cria o primeiro pedido
        Friendship.objects.create(from_user=user1, to_user=user2)
        
        # CORREÇÃO: Use transaction.atomic() para isolar a falha
        # Isso impede que a transação principal seja abortada pelo erro de integridade
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                Friendship.objects.create(from_user=user1, to_user=user2)
            
        # Agora podemos continuar usando o banco na mesma transação de teste
        # A ordem inversa é permitida pelo banco
        Friendship.objects.create(from_user=user2, to_user=user1)
        assert Friendship.objects.count() == 2

# ======================================
# Testes do Modelo Group
# ======================================

class TestGroupModel:
    """Testa o modelo Group (Grupo de Amigos)."""

    def test_group_creation(self, user_factory):
        owner = user_factory(username='Owner', password='123')
        group = Group.objects.create(name='Grupo Alpha', owner=owner)

        assert group.name == 'Grupo Alpha'
        assert str(group) == 'Grupo Alpha'

    def test_group_name_must_be_unique(self, user_factory):
        owner = user_factory(username='Owner', password='123')
        Group.objects.create(name='Grupo Beta', owner=owner)
        
        with pytest.raises(IntegrityError):
            with transaction.atomic(): # CORREÇÃO
                Group.objects.create(name='Grupo Beta', owner=owner)

# ======================================
# Testes do Modelo GroupMembership
# ======================================

class TestGroupMembershipModel:
    
    @pytest.fixture
    def setup_group_and_users(self, user_factory):
        owner = user_factory(username='Owner', password='123')
        member1 = user_factory(username='Member1', password='123')
        member2 = user_factory(username='Member2', password='123')
        group = Group.objects.create(name='Grupo Teste', owner=owner)
        return owner, member1, member2, group

    def test_membership_creation(self, setup_group_and_users):
        owner, member1, _, group = setup_group_and_users
        membership = GroupMembership.objects.create(user=member1, group=group)

        assert membership.user == member1
        assert membership.is_admin is False
        assert str(membership) == f"{member1.username} em {group.name}"
        
    def test_membership_admin_creation(self, setup_group_and_users):
        owner, _, member2, group = setup_group_and_users
        membership = GroupMembership.objects.create(user=member2, group=group, is_admin=True)
        assert membership.is_admin is True

    def test_membership_unique_together(self, setup_group_and_users):
        owner, member1, _, group = setup_group_and_users
        GroupMembership.objects.create(user=member1, group=group)
        
        with pytest.raises(IntegrityError):
            with transaction.atomic(): # CORREÇÃO
                GroupMembership.objects.create(user=member1, group=group)

# ======================================
# Testes do Modelo GroupInvite
# ======================================

class TestGroupInviteModel:
    
    @pytest.fixture
    def setup_group_invite(self, user_factory):
        sender = user_factory(username='Sender', password='123')
        receiver = user_factory(username='Receiver', password='123')
        owner = user_factory(username='Owner', password='123')
        group = Group.objects.create(name='Grupo Convite', owner=owner)
        return sender, receiver, group

    def test_invite_creation(self, setup_group_invite):
        sender, receiver, group = setup_group_invite
        invite = GroupInvite.objects.create(
            sender=sender, group=group, receiver=receiver
        )
        assert invite.status == 'PENDING'
        assert str(invite) == f"Convite para {receiver.username} no grupo {group.name} - Status: PENDING"
        
    def test_invite_status_choices(self, setup_group_invite):
        sender, receiver, group = setup_group_invite
        
        invite_accepted = GroupInvite.objects.create(
            sender=sender, group=group, receiver=receiver, status='ACCEPTED'
        )
        assert invite_accepted.status == 'ACCEPTED'
        
        # Cria um novo receiver para testar outro convite no mesmo grupo
        receiver2 = User.objects.create_user(username='Receiver2', email='r2@test.com', password='123')
        invite_rejected = GroupInvite.objects.create(
            sender=sender, group=group, receiver=receiver2, status='REJECTED'
        )
        assert invite_rejected.status == 'REJECTED'

    def test_invite_unique_together_pending(self, setup_group_invite):
        """Testa unique_together com PENDING."""
        sender, receiver, group = setup_group_invite
        
        # Primeiro convite pendente
        GroupInvite.objects.create(
            sender=sender, group=group, receiver=receiver, status='PENDING'
        )
        
        # Tenta criar um segundo convite pendente (deve falhar e ser capturado atomicamente)
        with pytest.raises(IntegrityError):
            with transaction.atomic(): # CORREÇÃO
                GroupInvite.objects.create(
                    sender=sender, group=group, receiver=receiver, status='PENDING'
                )
            
        # Altera o status do primeiro para 'REJECTED'
        invite = GroupInvite.objects.get(receiver=receiver, group=group)
        invite.status = 'REJECTED'
        invite.save()
        
        # Agora deve permitir criar um novo convite PENDING
        GroupInvite.objects.create(
            sender=sender, group=group, receiver=receiver, status='PENDING'
        )
        
        assert GroupInvite.objects.filter(group=group, receiver=receiver).count() == 2