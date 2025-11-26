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

class EmptySerializer(serializers.Serializer):
    pass

class FriendshipManageView(APIView):
    """
    POST: Aceita ou Rejeita um pedido de amizade recebido.
    URL: /api/social/friendships/<request_id>/<action>/
    """
    serializer_class = EmptyResponseSerializer
    permission_classes = [IsAuthenticated]

    swagger_fake_method = 'post'

    @swagger_auto_schema(
        operation_id='social_friendship_manage_action',
        request_body=EmptyResponseSerializer,
        responses={200: EmptyResponseSerializer}
    )

    def post(self, request, pk, action):
        # Encontra o pedido pelo ID e verifica se ele foi enviado PARA o usuário logado
        friendship = get_object_or_404(
            Friendship, 
            pk=pk, 
            to_user=request.user, 
            status='pending'
        )
        
        if action == 'accept':
            friendship.status = 'accepted'
            message = f"Pedido de amizade de {friendship.from_user.username} aceito. Vocês agora são amigos!"
            status_code = status.HTTP_200_OK
        
        elif action == 'reject':
            friendship.status = 'rejected'
            message = f"Pedido de amizade de {friendship.from_user.username} rejeitado."
            status_code = status.HTTP_200_OK
            
        else:
            return Response(
                {"error": "Ação inválida. Use 'accept' ou 'reject'."}, 
                status=status.HTTP_400_BAD_REQUEST
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
        operation_id='social_group_invite_manage',
        request_body=None, # Não requer corpo de requisição
        responses={
            200: "Mensagem de sucesso (convite aceito/rejeitado).",
            400: "Ação inválida ou convite não encontrado/expirado."
        }
    )
    def post(self, request, pk, action):
        # O decorador @transaction.atomic garante que se qualquer etapa falhar, nada é salvo no DB.
        with transaction.atomic():
            
            # 1. Busca e valida o convite
            try:
                invite = GroupInvite.objects.get(
                    pk=pk, 
                    # Apenas o usuário que recebeu o convite pode gerenciá-lo
                    receiver=request.user, 
                    status='PENDING' # Deve estar pendente
                )
            except GroupInvite.DoesNotExist:
                return Response(
                    {"error": "Convite não encontrado, já foi gerenciado ou você não é o destinatário."},
                    status=status.HTTP_404_NOT_FOUND
                )

            if action == 'accept':
                # 2. Adiciona o usuário ao grupo
                
                # O GroupMembership é criado automaticamente via M2M, mas 
                # como você tem um 'through' model (GroupMembership), 
                # você deve criar a instância 'GroupMembership' explicitamente ou usar add()
                
                # Usando add() (método mais simples, garante que não haja duplicidade)
                invite.group.members.add(request.user) 
                
                invite.status = 'ACCEPTED'
                message = f"Você aceitou o convite e entrou no grupo '{invite.group.name}'!"
                
            elif action == 'reject':
                # 3. Rejeita o convite
                invite.status = 'REJECTED'
                message = "Você rejeitou o convite."
                
            else:
                return Response(
                    {"error": "Ação inválida. Use 'accept' ou 'reject'."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 4. Salva a mudança de status no convite
            invite.save()
            
            return Response({"message": message}, status=status.HTTP_200_OK)
        

class FriendListView(APIView):
    """
    Retorna a lista de todos os amigos (com status 'accepted') do usuário logado.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        
        # 1. Busca amizades ativas onde o usuário logado é from_user OU to_user
        # O status deve ser a string 'accepted', não o inteiro 2.
        active_friendships = Friendship.objects.filter(
            Q(from_user=user) | Q(to_user=user), 
            status='accepted' # CORREÇÃO: Usar a string literal 'accepted'
        ).select_related('from_user', 'to_user') # CORREÇÃO: Usar from_user e to_user
        
        friend_ids = []
        for friendship in active_friendships:
            # Adiciona o ID do outro usuário (o amigo)
            # CORREÇÃO: Checar from_user e to_user
            if friendship.from_user.id == user.id:
                friend_ids.append(friendship.to_user.id)
            else:
                friend_ids.append(friendship.from_user.id)

        # 2. Busca os objetos User dos IDs encontrados
        friends = User.objects.filter(id__in=friend_ids)
        
        # 3. Serializa e retorna
        serializer = FriendSerializer(friends, many=True)
        
        return Response(serializer.data, status=status.HTTP_200_OK)
    

class UserSearchView(generics.ListAPIView):
    """
    GET: Pesquisa usuários pelo username.
    URL de exemplo: /api/social/users/search/?query=termo
    """
    serializer_class = FriendSerializer # Reutilizamos este serializer para retornar o usuário
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # 1. Obtém o termo de busca da query string (URL)
        search_term = self.request.query_params.get('query', '')
        
        # 2. Ignora o usuário logado na pesquisa
        user = self.request.user

        if search_term:
            # Filtra usuários cujo username contenha o termo de busca (case-insensitive)
            # e exclui o próprio usuário logado.
            queryset = User.objects.filter(
                Q(username__icontains=search_term) | Q(email__icontains=search_term)
            ).exclude(pk=user.pk).distinct()
            
            # Limita a busca a, por exemplo, 10 resultados para performance
            return queryset[:10] 
        
        # Se não houver termo de busca, retorna um queryset vazio para evitar listar todos
        return User.objects.none()

class SendFriendshipRequestToUserView(APIView):
    """
    POST: Envia um pedido de amizade do usuário logado para um usuário específico
    cujo ID (pk) é passado na URL (útil para perfis 'visitante').
    URL Exemplo: /api/social/users/123/request-friendship/
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_id='social_send_friendship_request_by_id',
        request_body=EmptyResponseSerializer, # Não requer corpo (o id está na URL)
        responses={
            201: 'Pedido de amizade enviado com sucesso.',
            200: 'Pedido de amizade aceito automaticamente.', # Adicionado para reciprocidade
            400: 'Erro de validação (já são amigos, pedido pendente, etc.)',
            404: 'Usuário destinatário não encontrado.'
        }
    )
    def post(self, request, pk):
        sender = request.user
        
        # 1. Busca o usuário destinatário (Receiver)
        try:
            receiver = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response(
                {"error": "Usuário destinatário não encontrado."},
                status=status.HTTP_404_NOT_FOUND
            )

        # 2. Pre-validações: Não pode ser para si mesmo
        if sender.pk == receiver.pk:
            return Response(
                {"error": "Você não pode enviar um pedido de amizade para si mesmo."},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # 3. Verifica se já existe uma amizade (Aceita, Pendente ou Reversa)
        existing_friendship = Friendship.objects.filter(
            Q(from_user=sender, to_user=receiver) | Q(from_user=receiver, to_user=sender)
        ).first()

        if existing_friendship:
            if existing_friendship.status == 'accepted':
                return Response(
                    {"error": f"Vocês já são amigos de {receiver.username}."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            elif existing_friendship.status == 'pending':
                # Se for um pedido pendente (de A para B), não envia de novo
                if existing_friendship.from_user == sender:
                    return Response(
                        {"error": "Um pedido de amizade para este usuário já está pendente."},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                else: # Se o outro usuário (Receiver) enviou o pedido (B para A), ACEITA AUTOMATICAMENTE
                    existing_friendship.status = 'accepted'
                    existing_friendship.save()
                    return Response(
                        {"message": f"Pedido de amizade aceito automaticamente! Vocês agora são amigos de {receiver.username}."},
                        status=status.HTTP_200_OK # 200 OK porque a ação foi concluída
                    )
            # Regra de Negócio: Se for 'rejected', podemos permitir um novo envio.
            # Se você não quiser que o usuário possa enviar novamente após rejeição, adicione o status 'rejected' aqui.

        # 4. Cria o novo pedido de amizade
        try:
            Friendship.objects.create(
                from_user=sender,
                to_user=receiver,
                status='pending'
            )
            return Response(
                {"message": f"Pedido de amizade enviado para {receiver.username}."},
                status=status.HTTP_201_CREATED
            )
        except Exception:
             return Response(
                {"error": "Erro interno ao criar pedido de amizade."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
