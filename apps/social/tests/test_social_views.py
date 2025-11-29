import pytest
from django.urls import reverse
from rest_framework import status
from apps.social.models import Group, GroupMembership, Friendship, GroupInvite


@pytest.fixture
def user_factory(django_user_model):
    def create_user(**kwargs):
        return django_user_model.objects.create_user(**kwargs)

    return create_user


@pytest.fixture
def user_a(user_factory):
    return user_factory(
        username="user_a_view", email="a_view@test.com", password="password123"
    )


@pytest.fixture
def user_b(user_factory):
    return user_factory(
        username="user_b_view", email="b_view@test.com", password="password123"
    )


@pytest.fixture
def user_c(user_factory):
    return user_factory(
        username="user_c_view", email="c_view@test.com", password="password123"
    )


@pytest.fixture
def api_client():
    from rest_framework.test import APIClient

    return APIClient()


@pytest.mark.django_db
class TestGroupViews:

    def test_group_list_create(self, api_client, user_a):
        """Integração: Cria um grupo e verifica se ele aparece na lista."""
        api_client.force_authenticate(user=user_a)
        url = reverse("group-list-create")

        data = {"name": "Grupo dos Testes"}
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["name"] == "Grupo dos Testes"
        assert response.data["owner"] == user_a.id

        group = Group.objects.get(name="Grupo dos Testes")
        membership = GroupMembership.objects.get(group=group, user=user_a)
        assert membership.is_admin is True

        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["name"] == "Grupo dos Testes"

    def test_group_detail_permission(self, api_client, user_a, user_b):
        """Integração: Apenas membros podem ver detalhes do grupo."""
        group = Group.objects.create(name="Private Group", owner=user_a)
        GroupMembership.objects.create(user=user_a, group=group, is_admin=True)

        url = reverse("group-detail", kwargs={"pk": group.id})

        api_client.force_authenticate(user=user_b)
        response = api_client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

        api_client.force_authenticate(user=user_a)
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "Private Group"

    def test_add_member_view(self, api_client, user_a, user_b, user_c):
        """Integração: Apenas admin pode adicionar membros."""
        group = Group.objects.create(name="Admin Only", owner=user_a)
        GroupMembership.objects.create(user=user_a, group=group, is_admin=True)
        GroupMembership.objects.create(user=user_b, group=group, is_admin=False)

        url = reverse("group-add-member", kwargs={"pk": group.id})
        data = {"user_id": user_c.id}

        api_client.force_authenticate(user=user_b)
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_403_FORBIDDEN

        api_client.force_authenticate(user=user_a)
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED

        assert GroupMembership.objects.filter(group=group, user=user_c).exists()


@pytest.mark.django_db
class TestFriendshipViews:

    def test_send_friend_request(self, api_client, user_a, user_b):
        """Integração: Enviar pedido de amizade."""
        api_client.force_authenticate(user=user_a)
        url = reverse("friendship-request-list-create")

        data = {"to_user": user_b.id}
        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_201_CREATED
        assert Friendship.objects.filter(
            from_user=user_a, to_user=user_b, status="pending"
        ).exists()

    def test_list_received_requests(self, api_client, user_a, user_b):
        """Integração: Listar pedidos recebidos."""
        Friendship.objects.create(from_user=user_b, to_user=user_a, status="pending")

        api_client.force_authenticate(user=user_a)
        url = reverse("friendship-request-list-create")

        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["from_username"] == user_b.username

    def test_manage_friendship_accept(self, api_client, user_a, user_b):
        """Integração: Aceitar pedido de amizade."""
        friendship = Friendship.objects.create(
            from_user=user_b, to_user=user_a, status="pending"
        )

        api_client.force_authenticate(user=user_a)
        url = reverse(
            "friendship-manage", kwargs={"pk": friendship.id, "action": "accept"}
        )

        response = api_client.post(url)

        assert response.status_code == status.HTTP_200_OK
        friendship.refresh_from_db()
        assert friendship.status == "accepted"

    def test_manage_friendship_reject(self, api_client, user_a, user_b):
        """Integração: Rejeitar pedido de amizade."""
        friendship = Friendship.objects.create(
            from_user=user_b, to_user=user_a, status="pending"
        )

        api_client.force_authenticate(user=user_a)
        url = reverse(
            "friendship-manage", kwargs={"pk": friendship.id, "action": "reject"}
        )

        response = api_client.post(url)
        assert response.status_code == status.HTTP_200_OK

        friendship.refresh_from_db()
        assert friendship.status == "rejected"

    def test_friend_list_view(self, api_client, user_a, user_b, user_c):
        """Integração: Listar apenas amigos aceitos."""
        Friendship.objects.create(from_user=user_a, to_user=user_b, status="accepted")
        Friendship.objects.create(from_user=user_c, to_user=user_a, status="pending")

        api_client.force_authenticate(user=user_a)
        url = reverse("friend-list")

        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK

        assert len(response.data) == 1
        assert response.data[0]["username"] == user_b.username


@pytest.mark.django_db
class TestGroupInviteManageView:

    def test_manage_invite_accept(self, api_client, user_a, user_b):
        """Integração: Aceitar convite de grupo."""
        group = Group.objects.create(name="Convite Group", owner=user_a)
        GroupMembership.objects.create(user=user_a, group=group, is_admin=True)

        invite = GroupInvite.objects.create(
            sender=user_a, group=group, receiver=user_b, status="PENDING"
        )

        api_client.force_authenticate(user=user_b)
        url = reverse(
            "group-invite-manage", kwargs={"pk": invite.id, "action": "accept"}
        )

        response = api_client.post(url)
        assert response.status_code == status.HTTP_200_OK

        invite.refresh_from_db()
        assert invite.status == "ACCEPTED"

        assert GroupMembership.objects.filter(group=group, user=user_b).exists()

    def test_manage_invite_invalid_action(self, api_client, user_a, user_b):
        """Integração: Tentar ação inválida no convite."""
        group = Group.objects.create(name="Convite Group 2", owner=user_a)
        invite = GroupInvite.objects.create(
            sender=user_a, group=group, receiver=user_b, status="PENDING"
        )

        api_client.force_authenticate(user=user_b)
        url = reverse(
            "group-invite-manage", kwargs={"pk": invite.id, "action": "dance"}
        )

        response = api_client.post(url)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
