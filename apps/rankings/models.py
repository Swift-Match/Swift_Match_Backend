from django.db import models
from apps.users.models import User
from apps.albums.models import Album
from apps.tracks.models import Track
from django.db.models import JSONField
from apps.social.models import Group
from django.conf import settings
from django.utils import timezone

# --- Modelo 1: Ranking de Álbuns ---
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
    # A posição que o usuário atribuiu ao álbum (1, 2, 3, etc.)
    position = models.PositiveSmallIntegerField(
        verbose_name='Posição no Ranking'
    )

    class Meta:
        verbose_name = 'Ranking de Álbum'
        verbose_name_plural = 'Rankings de Álbuns'
        # Garante que um usuário não rankeie o mesmo álbum duas vezes
        # e que não existam duas posições iguais para o mesmo usuário (evita empates)
        unique_together = (('user', 'album'), ('user', 'position')) 
        ordering = ['user', 'position']

    def __str__(self):
        return f"{self.user.username}'s Ranking: {self.album.title} ({self.position}°)"

# --- Modelo 2: Ranking de Músicas (por Álbum) ---
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
    # A posição que o usuário atribuiu à música (1, 2, 3, etc.)
    position = models.PositiveSmallIntegerField(
        verbose_name='Posição no Ranking'
    )

    class Meta:
        verbose_name = 'Ranking de Música'
        verbose_name_plural = 'Rankings de Músicas'
        # A restrição de unicidade é mais complexa aqui, 
        # pois o usuário pode ter uma música de álbuns diferentes na mesma posição global.
        # No entanto, vamos garantir que ele só rankeie a música UMA vez
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
    ) # 🌟 Necessário para definir o tamanho da bubble no frontend

    # Análise de Consenso/Extremos (Os IDs dos álbuns mais relevantes)
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

    # Armazena o ranking completo (Álbum: Posição Média, Desvio Padrão)
    # e outras métricas que não precisam de um campo FK dedicado.
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
    is_active = models.BooleanField(default=True) # Pode ser desativado
    
    class Meta:
        unique_together = ('group', 'album') # Um álbum só pode ser adicionado ao grupo uma vez
        verbose_name = 'Ranking de Grupo'
        
    def __str__(self):
        return f"{self.album.title} em {self.group.name}"
    
class UserRanking(models.Model):
    """A submissão de ranking individual de um usuário para um GroupRanking específico."""
    # Agora se relaciona com GroupRanking, não apenas Album
    group_ranking = models.ForeignKey(GroupRanking, on_delete=models.CASCADE, related_name='submissions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='group_submissions')
    is_complete = models.BooleanField(default=True) # Marca que o ranking foi enviado
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        # Um usuário só pode submeter um ranking para um GroupRanking específico uma vez
        unique_together = ('group_ranking', 'user') 
        verbose_name = 'Submissão de Ranking Individual'

    def __str__(self):
        return f"{self.user.username} submeteu {self.group_ranking.album.title}"

# O modelo RankedTrack permanece o mesmo, mas agora aponta para o novo UserRanking
class RankedTrack(models.Model):
    """Representa uma track dentro da submissão do usuário."""
    user_ranking = models.ForeignKey(UserRanking, on_delete=models.CASCADE, related_name='ranked_tracks')
    track = models.ForeignKey(Track, on_delete=models.CASCADE)
    position = models.PositiveIntegerField()
    
    class Meta:
        ordering = ['position']
    
