from django.db import models
from apps.users.models import User
from apps.albums.models import Album
from apps.tracks.models import Track
from django.db.models import JSONField
from apps.social.models import Group
from django.conf import settings
from django.utils import timezone

class AlbumRanking(models.Model):
    """
    Representa o ranking de álbuns de um usuário.
    Associa um Usuário a um Álbum e à Posição.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='album_rankings',
        verbose_name='Usuário'
    )
    album = models.ForeignKey(
        Album,
        on_delete=models.CASCADE,
        related_name='user_rankings',
        verbose_name='Álbum'
    )
    position = models.PositiveSmallIntegerField(
        verbose_name='Posição no Ranking'
    )

    class Meta:
        verbose_name = 'Ranking de Álbum'
        verbose_name_plural = 'Rankings de Álbuns'
        unique_together = (('user', 'album'), ('user', 'position')) 
        ordering = ['user', 'position']

    def __str__(self):
        return f"{self.user.username}'s Ranking: {self.album.title} ({self.position}°)"

class TrackRanking(models.Model):
    """
    Representa o ranking de músicas DENTRO de um álbum de um usuário.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='track_rankings',
        verbose_name='Usuário'
    )
    track = models.ForeignKey(
        Track,
        on_delete=models.CASCADE,
        related_name='user_rankings',
        verbose_name='Música'
    )
    position = models.PositiveSmallIntegerField(
        verbose_name='Posição no Ranking'
    )

    class Meta:
        verbose_name = 'Ranking de Música'
        verbose_name_plural = 'Rankings de Músicas'
        unique_together = (('user', 'track'),) 
        ordering = ['user', 'position']

    def __str__(self):
        return f"{self.user.username}'s Track Ranking: {self.track.title} ({self.position}°)"
    

class CountryGlobalRanking(models.Model):
    """
    Armazena o resultado do cálculo global do ranking de álbuns para um país.
    Este modelo é populado por uma tarefa agendada (Cron Job/Celery).
    """
    country_name = models.CharField(
        max_length=100, 
        unique=True, 
        verbose_name='Nome do País'
    )
    user_count = models.IntegerField(
        default=0, 
        verbose_name='Número de Usuários Ativos'
    ) 

    consensus_album = models.ForeignKey(
        Album, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='country_consensus',
        verbose_name='Álbum Favorito (Consenso)'
    )
    polarization_album = models.ForeignKey(
        Album, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='country_polarization',
        verbose_name='Álbum da Maior Polarização'
    )

    global_consensus_track = models.ForeignKey(
        Track, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='country_global_consensus',
        verbose_name='Música Global Favorita'
    )

    analysis_data = JSONField(
        default=dict, 
        verbose_name='Dados Completos da Análise (JSON)'
    )
    
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Ranking Global por País'
        verbose_name_plural = 'Rankings Globais por País'

    def __str__(self):
        return f"Ranking de Álbuns: {self.country_name}"
    
class GroupRanking(models.Model):
    """Representa um álbum que foi adicionado a um grupo para fins de matching."""
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='rankings_to_complete')
    album = models.ForeignKey(Album, on_delete=models.CASCADE)
    added_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    is_active = models.BooleanField(default=True) 
    
    class Meta:
        unique_together = ('group', 'album') 
        verbose_name = 'Ranking de Grupo'
        
    def __str__(self):
        return f"{self.album.title} em {self.group.name}"
    
class UserRanking(models.Model):
    """A submissão de ranking individual de um usuário para um GroupRanking específico."""
    group_ranking = models.ForeignKey(GroupRanking, on_delete=models.CASCADE, related_name='submissions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='group_submissions')
    is_complete = models.BooleanField(default=True) 
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('group_ranking', 'user') 
        verbose_name = 'Submissão de Ranking Individual'

    def __str__(self):
        return f"{self.user.username} submeteu {self.group_ranking.album.title}"

class RankedTrack(models.Model):
    """Representa uma track dentro da submissão do usuário."""
    user_ranking = models.ForeignKey(UserRanking, on_delete=models.CASCADE, related_name='ranked_tracks')
    track = models.ForeignKey(Track, on_delete=models.CASCADE)
    position = models.PositiveIntegerField()
    
    class Meta:
        ordering = ['position']
    
class Notification(models.Model):
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='notifications'
    )
    
    TYPE_CHOICES = [
        ('INVITE', 'Convite de Grupo'),
        ('MATCH_ALERT', 'Alerta de Rankeamento'),
        ('GENERIC', 'Geral'),
    ]
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='GENERIC')
    
    message = models.CharField(max_length=255)
    
    related_id = models.IntegerField(null=True, blank=True) 
    
    is_read = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Notificação"
        verbose_name_plural = "Notificações"

    def __str__(self):
        return f"[{self.type}] para {self.recipient.username}: {self.message[:40]}..."

