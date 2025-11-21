from django.db import models
from apps.albums.models import Album # Importa o modelo Album

class Track(models.Model):
    """Modelo para representar uma música (track) de um álbum."""

    album = models.ForeignKey(
        Album, 
        on_delete=models.CASCADE, 
        related_name='tracks',    
        verbose_name="Álbum"
    )
    
    title = models.CharField(
        max_length=255, 
        verbose_name="Título da Música"
    )
    
    track_number = models.PositiveSmallIntegerField(
        verbose_name="Número da Faixa"
    )

    class Meta:
        verbose_name = "Música"
        verbose_name_plural = "Músicas"
        unique_together = ('album', 'track_number') 
        ordering = ['album__release_date', 'track_number'] 
        
    def __str__(self):
        return f"{self.track_number}. {self.title} ({self.album.title})"