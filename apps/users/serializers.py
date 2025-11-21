from rest_framework import serializers
from .models import User
from apps.social.models import Friendship, GroupMembership 
from django.db.models import Q

class UserRegistrationSerializer(serializers.ModelSerializer):
    # O campo password precisa ser write_only para não aparecer na resposta
    password = serializers.CharField(write_only=True)
    friends_count = serializers.SerializerMethodField()
    groups_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'username', 
            'first_name', 
            'email', 
            'password', 
            'country', 
            'friends_count',  
            'groups_count',   
        )

    def create(self, validated_data):
        # Sobrescreve o método create para usar 'create_user' 
        # e garantir que a senha seja salva como hash (segurança!)
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', '')
        )
        return user
    
    def get_friends_count(self, obj) -> int:
        # Contagem de amizades aceitas (onde o usuário é from_user OU to_user)
        return Friendship.objects.filter(
            Q(from_user=obj) | Q(to_user=obj),
            status='accepted'
        ).count()

    def get_groups_count(self, obj) -> int:
        # Contagem de grupos onde o usuário é membro
        return GroupMembership.objects.filter(user=obj).count()
    

class UserPublicSerializer(serializers.ModelSerializer):
    """
    Serializer básico para retornar apenas informações públicas de um usuário.
    """
    class Meta:
        model = User
        # Inclua apenas campos não-sensíveis que você precisa para exibir 
        # o remetente/destinatário do convite.
        fields = ['id', 'username', 'first_name', 'last_name', 'profile_picture_url'] 
        # Ajuste os campos conforme seu modelo CustomUser