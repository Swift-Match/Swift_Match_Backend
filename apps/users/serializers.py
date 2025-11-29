from rest_framework import serializers
from .models import User
from apps.social.models import Friendship, GroupMembership 
from django.db.models import Q

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    friends_count = serializers.SerializerMethodField()
    groups_count = serializers.SerializerMethodField()

    tema = serializers.ChoiceField(
        choices=User.TEMA_CHOICES,
        default=User.TEMA_CHOICES[-1][0],  
        required=False
    )


    class Meta:
        model = User
        fields = (
            'username', 
            'first_name', 
            'email', 
            'password', 
            'country', 
            'tema', 
            'friends_count',  
            'groups_count',   
        )

    def create(self, validated_data):
            tema = validated_data.pop('tema', User.TEMA_CHOICES[-1][0])
            country = validated_data.pop('country')
            user = User.objects.create_user(
                username=validated_data['username'],
                email=validated_data['email'],
                password=validated_data['password'],
                first_name=validated_data.get('first_name', ''),
                tema=tema,
                country=country
            )
            return user
    
    def get_friends_count(self, obj) -> int:
        return Friendship.objects.filter(
            Q(from_user=obj) | Q(to_user=obj),
            status='accepted'
        ).count()

    def get_groups_count(self, obj) -> int:
        return GroupMembership.objects.filter(user=obj).count()
    

class UserPublicSerializer(serializers.ModelSerializer):
    """
    Serializer básico para retornar apenas informações públicas de um usuário.
    """
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'profile_picture_url'] 

class UserThemeSerializer(serializers.ModelSerializer):
    tema = serializers.ChoiceField(
        choices=User.TEMA_CHOICES,
        required=True,
        help_text="Escolha o tema do usuário"
    )

    class Meta:
        model = User
        fields = ['tema']


class UserFirstLoginSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['first_login']