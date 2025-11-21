from django.db import models
from apps.users.models import User
from django.utils import timezone
from django.conf import settings

# --- Modelo 1: Pedido de Amizade ---
class Friendship(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pendente'),
        ('accepted', 'Aceita'),
        ('rejected', 'Rejeitada'),
    )

    from_user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='friendship_requests_sent',
        verbose_name='De'
    )
    to_user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='friendship_requests_received',
        verbose_name='Para'
    )
    status = models.CharField(
        max_length=10, 
        choices=STATUS_CHOICES, 
        default='pending',
        verbose_name='Status'
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = 'Amizade'
        verbose_name_plural = 'Amizades'
        # Garante que não haja dois pedidos entre os mesmos dois usuários (em ambas direções)
        unique_together = ('from_user', 'to_user') 

    def __str__(self):
        return f"Pedido de {self.from_user} para {self.to_user} ({self.status})"

