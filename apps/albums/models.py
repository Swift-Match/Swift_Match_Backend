from django.db import models

class Album(models.Model):
    """Modelo para representar um álbum da Taylor Swift."""
    
    title = models.CharField(
        max_length=150, 
        unique=True, 
        verbose_name="Título do Álbum"
    )
    
    release_date = models.DateField(
        verbose_name="Data de Lançamento"
    )
    
    cover_image_url = models.URLField(
        max_length=500, 
        blank=True, 
        null=True,
        verbose_name="URL da Capa"
    )

    class Meta:
        verbose_name = "Álbum"
        verbose_name_plural = "Álbuns"
        ordering = ['release_date'] 
        
    def __str__(self):
        return f"{self.title}"