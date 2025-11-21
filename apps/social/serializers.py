from rest_framework import serializers
from .models import Group, GroupMembership, User, Friendship, GroupInvite
from apps.users.serializers import UserPublicSerializer # Reutiliza o Serializer de User


class GroupMemberSerializer(serializers.ModelSerializer):
    # Serializer básico para listar os membros (mostra o username e ID)
    user_id = serializers.ReadOnlyField(source='user.id')
    username = serializers.ReadOnlyField(source='user.username')
    
    class Meta:
        model = GroupMembership
        fields = ('user_id', 'username', 'is_admin', 'joined_at')
        
class GroupSerializer(serializers.ModelSerializer):
    members = GroupMemberSerializer(source='groupmembership_set', many=True, read_only=True)
    owner_username = serializers.ReadOnlyField(source='owner.username')

    class Meta:
        model = Group
        fields = ('id', 'name', 'owner', 'owner_username', 'created_at', 'members')
        read_only_fields = ('owner',) # O dono será definido automaticamente na View

# --- Serializer para Adicionar Membro (Input) ---
class AddMemberSerializer(serializers.Serializer):
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), 
        write_only=True,
        error_messages={'does_not_exist': 'Usuário com este ID não existe.'}
    )

    def validate_user_id(self, user):
        # Evita que o dono do grupo se adicione através deste endpoint se já for membro
        if GroupMembership.objects.filter(group=self.context['group'], user=user).exists():
            raise serializers.ValidationError("Este usuário já é membro do grupo.")
        return user
    

