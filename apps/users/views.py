from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from .serializers import UserRegistrationSerializer
from django.http import JsonResponse
from drf_spectacular.utils import extend_schema   
from rest_framework.permissions import IsAuthenticated
from rest_framework import generics
from .serializers import UserRegistrationSerializer

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