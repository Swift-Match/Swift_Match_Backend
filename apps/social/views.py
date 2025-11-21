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
    AddMemberSerializer,
    FriendshipRequestSerializer,
    AddMemberSerializer,
    FriendSerializer
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
        # Retorna grupos onde o usuário logado é membro
        return Group.objects.filter(members=self.request.user).distinct()

    def perform_create(self, serializer):
        # 1. Define o usuário logado como dono
        group = serializer.save(owner=self.request.user)
        # 2. Adiciona o dono como primeiro membro e administrador
        GroupMembership.objects.create(
            group=group, 
            user=self.request.user, 
            is_admin=True
        )

class GroupDetailView(generics.RetrieveAPIView):
    """
    GET: Detalhes de um grupo específico.
    """
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'pk'

    def get_object(self):
        obj = super().get_object()
        # Garante que apenas membros do grupo possam ver os detalhes
        if not obj.members.filter(pk=self.request.user.id).exists():
            self.permission_denied(
                self.request, 
                message="Você não tem permissão para visualizar este grupo."
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

        # 1. Checa se o usuário logado é administrador
        if not current_user_membership.is_admin:
            return Response(
                {"error": "Você precisa ser administrador para adicionar membros."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = AddMemberSerializer(data=request.data, context={'group': group})
        serializer.is_valid(raise_exception=True)
        
        user_to_add = serializer.validated_data['user_id']
        
        # 2. Adiciona o novo membro
        GroupMembership.objects.create(
            group=group,
            user=user_to_add,
            is_admin=False # Membro novo não é admin por padrão
        )

        return Response(
            {"message": f"Usuário {user_to_add.username} adicionado ao grupo '{group.name}'."},
            status=status.HTTP_201_CREATED
        )
    

class FriendshipRequestListView(generics.ListCreateAPIView):
    """
    GET: Lista todos os pedidos de amizade PENDENTES recebidos pelo usuário logado.
    POST: Envia um novo pedido de amizade para outro usuário.
    """
    serializer_class = FriendshipRequestSerializer
    permission_classes = [IsAuthenticated]

    swagger_fake_method = 'post'

    def get_queryset(self):
        # Lista pedidos pendentes que o usuário logado recebeu
        return Friendship.objects.filter(
            to_user=self.request.user, 
            status='pending'
        ).order_by('-created_at')

    def perform_create(self, serializer):
        # Define o usuário logado como o remetente
        serializer.save(from_user=self.request.user, status='pending')

    @swagger_auto_schema(
        operation_id='social_friendship_request_create', 
        request_body=FriendshipRequestSerializer, 
        responses={201: EmptyResponseSerializer} 
    )

    def post(self, request, *args, **kwargs):
        # Chama a função de criação herdada do ListCreateAPIView
        return self.create(request, *args, **kwargs)

