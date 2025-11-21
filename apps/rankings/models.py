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
    
