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

