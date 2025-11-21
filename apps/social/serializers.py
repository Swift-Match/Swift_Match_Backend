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
    

class FriendshipRequestSerializer(serializers.ModelSerializer):
    # Campos de leitura para a resposta
    from_username = serializers.ReadOnlyField(source='from_user.username')
    to_username = serializers.ReadOnlyField(source='to_user.username')

    class Meta:
        model = Friendship
        fields = ('id', 'from_user', 'from_username', 'to_user', 'to_username', 'status', 'created_at')
        read_only_fields = ('from_user', 'status') # O remetente e o status inicial são definidos na View
        extra_kwargs = {
            'to_user': {'write_only': True} # Campo de destino só é necessário na requisição POST
        }

    def validate(self, data):
        request_user = self.context['request'].user
        to_user = data.get('to_user')

        # 1. Não pode enviar amizade para si mesmo
        if request_user == to_user:
            raise serializers.ValidationError("Você não pode enviar um pedido de amizade para você mesmo.")

        # 2. Verifica se o pedido já existe em qualquer direção
        # (A para B) ou (B para A)
        existing_request = Friendship.objects.filter(
            models.Q(from_user=request_user, to_user=to_user) | 
            models.Q(from_user=to_user, to_user=request_user)
        ).first()

        if existing_request:
            if existing_request.status == 'accepted':
                raise serializers.ValidationError("Vocês já são amigos.")
            
            # Se já existir um pedido pendente (em qualquer direção)
            if existing_request.status == 'pending':
                if existing_request.from_user == request_user:
                    raise serializers.ValidationError("Você já enviou um pedido para este usuário.")
                else:
                    raise serializers.ValidationError("Este usuário já te enviou um pedido. Aceite-o em vez de enviar outro.")

        return data
    
