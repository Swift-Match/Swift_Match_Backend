from rest_framework import generics, status, serializers
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from .models import Group, GroupMembership, GroupInvite
from apps.users.models import User
from drf_yasg.utils import swagger_auto_schema
from django.db.models import Q
from .serializers import (
    GroupSerializer,
    FriendshipRequestSerializer,
    AddMemberSerializer,
    FriendSerializer,
)
from .models import Friendship
from django.db import transaction


class EmptyResponseSerializer(serializers.Serializer):
    pass


class GroupListCreateView(generics.ListCreateAPIView):
    """
    GET: Lista todos os grupos que o usuário logado participa.
    POST: Cria um novo grupo e define o usuário logado como dono e primeiro membro.
    """

    serializer_class = GroupSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Group.objects.filter(members=self.request.user).distinct()

    def perform_create(self, serializer):
        group = serializer.save(owner=self.request.user)
        GroupMembership.objects.create(
            group=group, user=self.request.user, is_admin=True
        )


class GroupDetailView(generics.RetrieveAPIView):
    """
    GET: Detalhes de um grupo específico.
    """

    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "pk"

    def get_object(self):
        obj = super().get_object()
        if not obj.members.filter(pk=self.request.user.id).exists():
            self.permission_denied(
                self.request,
                message="Você não tem permissão para visualizar este grupo.",
            )
        return obj


class GroupAddMemberView(GenericAPIView):
    """
    POST: Adiciona um novo membro ao grupo (requer permissão de administrador).
    """

    serializer_class = AddMemberSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        group = get_object_or_404(Group, pk=pk)
        current_user_membership = get_object_or_404(
            GroupMembership, group=group, user=request.user
        )

        if not current_user_membership.is_admin:
            return Response(
                {"error": "Você precisa ser administrador para adicionar membros."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = AddMemberSerializer(data=request.data, context={"group": group})
        serializer.is_valid(raise_exception=True)

        user_to_add = serializer.validated_data["user_id"]

        GroupMembership.objects.create(group=group, user=user_to_add, is_admin=False)

        return Response(
            {
                "message": f"Usuário {user_to_add.username} adicionado ao grupo '{group.name}'."
            },
            status=status.HTTP_201_CREATED,
        )


class FriendshipRequestListView(generics.ListCreateAPIView):
    """
    GET: Lista todos os pedidos de amizade PENDENTES recebidos pelo usuário logado.
    POST: Envia um novo pedido de amizade para outro usuário.
    """

    serializer_class = FriendshipRequestSerializer
    permission_classes = [IsAuthenticated]

    swagger_fake_method = "post"

    def get_queryset(self):
        return Friendship.objects.filter(
            to_user=self.request.user, status="pending"
        ).order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(from_user=self.request.user, status="pending")

    @swagger_auto_schema(
        operation_id="social_friendship_request_create",
        request_body=FriendshipRequestSerializer,
        responses={201: EmptyResponseSerializer},
    )
    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)


class EmptySerializer(serializers.Serializer):
    pass


class FriendshipManageView(APIView):
    """
    POST: Aceita ou Rejeita um pedido de amizade recebido.
    URL: /api/social/friendships/<request_id>/<action>/
    """

    serializer_class = EmptyResponseSerializer
    permission_classes = [IsAuthenticated]

    swagger_fake_method = "post"

    @swagger_auto_schema(
        operation_id="social_friendship_manage_action",
        request_body=EmptyResponseSerializer,
        responses={200: EmptyResponseSerializer},
    )
    def post(self, request, pk, action):
        friendship = get_object_or_404(
            Friendship, pk=pk, to_user=request.user, status="pending"
        )

        if action == "accept":
            friendship.status = "accepted"
            message = f"Pedido de amizade de {friendship.from_user.username} aceito. Vocês agora são amigos!"
            status_code = status.HTTP_200_OK

        elif action == "reject":
            friendship.status = "rejected"
            message = f"Pedido de amizade de {friendship.from_user.username} rejeitado."
            status_code = status.HTTP_200_OK

        else:
            return Response(
                {"error": "Ação inválida. Use 'accept' ou 'reject'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        friendship.save()

        return Response({"message": message}, status=status_code)


class GroupInviteManageView(APIView):
    """
    POST: Aceita ou Rejeita um convite de grupo recebido.
    URL: /api/social/groups/invites/<invite_id>/<action>/
    """

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_id="social_group_invite_manage",
        request_body=None,
        responses={
            200: "Mensagem de sucesso (convite aceito/rejeitado).",
            400: "Ação inválida ou convite não encontrado/expirado.",
        },
    )
    def post(self, request, pk, action):
        with transaction.atomic():

            try:
                invite = GroupInvite.objects.get(
                    pk=pk, receiver=request.user, status="PENDING"
                )
            except GroupInvite.DoesNotExist:
                return Response(
                    {
                        "error": "Convite não encontrado, já foi gerenciado ou você não é o destinatário."
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

            if action == "accept":

                invite.group.members.add(request.user)

                invite.status = "ACCEPTED"
                message = (
                    f"Você aceitou o convite e entrou no grupo '{invite.group.name}'!"
                )

            elif action == "reject":
                invite.status = "REJECTED"
                message = "Você rejeitou o convite."

            else:
                return Response(
                    {"error": "Ação inválida. Use 'accept' ou 'reject'."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            invite.save()

            return Response({"message": message}, status=status.HTTP_200_OK)


class FriendListView(APIView):
    """
    Retorna a lista de todos os amigos (com status 'accepted') do usuário logado.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        active_friendships = Friendship.objects.filter(
            Q(from_user=user) | Q(to_user=user), status="accepted"
        ).select_related("from_user", "to_user")

        friend_ids = []
        for friendship in active_friendships:
            if friendship.from_user.id == user.id:
                friend_ids.append(friendship.to_user.id)
            else:
                friend_ids.append(friendship.from_user.id)

        friends = User.objects.filter(id__in=friend_ids)

        serializer = FriendSerializer(friends, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)


class UserSearchView(generics.ListAPIView):
    """
    GET: Pesquisa usuários pelo username.
    URL de exemplo: /api/social/users/search/?query=termo
    """

    serializer_class = FriendSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        search_term = self.request.query_params.get("query", "")

        user = self.request.user

        if search_term:
            queryset = (
                User.objects.filter(
                    Q(username__icontains=search_term) | Q(email__icontains=search_term)
                )
                .exclude(pk=user.pk)
                .distinct()
            )

            return queryset[:10]

        return User.objects.none()


class SendFriendshipRequestToUserView(APIView):
    """
    POST: Envia um pedido de amizade do usuário logado para um usuário específico
    cujo ID (pk) é passado na URL (útil para perfis 'visitante').
    URL Exemplo: /api/social/users/123/request-friendship/
    """

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_id="social_send_friendship_request_by_id",
        request_body=EmptyResponseSerializer,
        responses={
            201: "Pedido de amizade enviado com sucesso.",
            200: "Pedido de amizade aceito automaticamente.",
            400: "Erro de validação (já são amigos, pedido pendente, etc.)",
            404: "Usuário destinatário não encontrado.",
        },
    )
    def post(self, request, pk):
        sender = request.user

        try:
            receiver = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response(
                {"error": "Usuário destinatário não encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if sender.pk == receiver.pk:
            return Response(
                {"error": "Você não pode enviar um pedido de amizade para si mesmo."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        existing_friendship = Friendship.objects.filter(
            Q(from_user=sender, to_user=receiver)
            | Q(from_user=receiver, to_user=sender)
        ).first()

        if existing_friendship:
            if existing_friendship.status == "accepted":
                return Response(
                    {"error": f"Vocês já são amigos de {receiver.username}."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            elif existing_friendship.status == "pending":
                if existing_friendship.from_user == sender:
                    return Response(
                        {
                            "error": "Um pedido de amizade para este usuário já está pendente."
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                else:
                    existing_friendship.status = "accepted"
                    existing_friendship.save()
                    return Response(
                        {
                            "message": f"Pedido de amizade aceito automaticamente! Vocês agora são amigos de {receiver.username}."
                        },
                        status=status.HTTP_200_OK,
                    )

        try:
            Friendship.objects.create(
                from_user=sender, to_user=receiver, status="pending"
            )
            return Response(
                {"message": f"Pedido de amizade enviado para {receiver.username}."},
                status=status.HTTP_201_CREATED,
            )
        except Exception:
            return Response(
                {"error": "Erro interno ao criar pedido de amizade."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
