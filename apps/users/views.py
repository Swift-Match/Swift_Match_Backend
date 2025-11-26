from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from .serializers import UserRegistrationSerializer
from django.http import JsonResponse
from drf_spectacular.utils import extend_schema   
from rest_framework.permissions import IsAuthenticated
from rest_framework import generics, views, status
from .serializers import UserRegistrationSerializer, UserThemeSerializer, UserFirstLoginSerializer
from .models import User

class RegisterUserView(APIView):
    """View para o cadastro de novos usuários."""
    permission_classes = []

    @extend_schema(
        request=UserRegistrationSerializer,
        responses={201: None, 400: dict}
    )
    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({"message": "Usuário criado com sucesso!"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class UserProfileView(generics.RetrieveAPIView):
    """
    Retorna os detalhes do perfil do usuário logado, incluindo contagens sociais.
    """
    serializer_class = UserRegistrationSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

def healthcheck(request):
    return JsonResponse({"status": "ok"})

class UserThemeUpdateView(generics.UpdateAPIView):
    """
    Atualiza o tema do usuário logado.
    """
    serializer_class = UserThemeSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class UserThemeListView(views.APIView):
    """
    Retorna a lista de todos os temas disponíveis.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        temas = [{"key": key, "label": label} for key, label in User.TEMA_CHOICES]
        return Response(temas, status=status.HTTP_200_OK)
    

class UserFirstLoginView(generics.RetrieveAPIView):
    serializer_class = UserFirstLoginSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user
    
class UserThemeRetrieveView(generics.RetrieveAPIView):
    """
    Retorna apenas o tema (tema) do usuário logado.
    """
    serializer_class = UserThemeSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        """Retorna o objeto User autenticado."""
        return self.request.user
    
class OtherUserProfileView(generics.RetrieveAPIView):
    """
    Retorna os detalhes do perfil de outro usuário, usando o ID (pk) na URL.
    Exemplo de URL: /api/users/123/
    """
    serializer_class = UserRegistrationSerializer
    permission_classes = [IsAuthenticated] # Mantenha a restrição de autenticação
    
    # Define o queryset para que o DRF possa buscar o objeto usando o 'pk' da URL
    queryset = User.objects.all()

    # O método get_object() padrão do RetrieveAPIView já usa a primary key (pk)
    # se o queryset estiver definido e a URL contiver o '<pk>'.
    # Não precisamos reescrevê-lo.

def healthcheck(request):
    return JsonResponse({"status": "ok"})