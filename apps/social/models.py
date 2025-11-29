from django.db import models
from apps.users.models import User
from django.utils import timezone
from django.conf import settings


class Friendship(models.Model):
    STATUS_CHOICES = (
        ("pending", "Pendente"),
        ("accepted", "Aceita"),
        ("rejected", "Rejeitada"),
    )

    from_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="friendship_requests_sent",
        verbose_name="De",
    )
    to_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="friendship_requests_received",
        verbose_name="Para",
    )
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default="pending", verbose_name="Status"
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Amizade"
        verbose_name_plural = "Amizades"
        unique_together = ("from_user", "to_user")

    def __str__(self):
        return f"Pedido de {self.from_user} para {self.to_user} ({self.status})"


class Group(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Nome do Grupo")
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="owned_groups",
        verbose_name="Criador",
    )
    members = models.ManyToManyField(
        User,
        through="GroupMembership",
        related_name="group_memberships",
        verbose_name="Membros",
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Grupo"
        verbose_name_plural = "Grupos"

    def __str__(self):
        return self.name


class GroupMembership(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    is_admin = models.BooleanField(default=False)
    joined_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ("user", "group")

    def __str__(self):
        return f"{self.user.username} em {self.group.name}"


class GroupInvite(models.Model):
    """
    Modelo para convites de grupo. Permite que um membro convide outro usuário.
    """

    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_group_invites",
    )

    group = models.ForeignKey(
        Group, related_name="invites", on_delete=models.CASCADE, verbose_name="Grupo"
    )

    receiver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="received_group_invites",
    )

    STATUS_CHOICES = [
        ("PENDING", "Pendente"),
        ("ACCEPTED", "Aceito"),
        ("REJECTED", "Rejeitado"),
        ("EXPIRED", "Expirado"),
    ]
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default="PENDING", verbose_name="Status"
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado Em")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado Em")

    class Meta:
        verbose_name = "Convite de Grupo"
        verbose_name_plural = "Convites de Grupo"
        unique_together = ("group", "receiver", "status")
        indexes = [
            models.Index(fields=["group", "receiver"]),
        ]

    def __str__(self):
        return f"Convite para {self.receiver.username} no grupo {self.group.name} - Status: {self.status}"
