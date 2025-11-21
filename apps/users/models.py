from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):

    country = models.CharField(
        max_length=100, 
        blank=True, 
        null=True, # Permite nulo no banco
        default="", # Padrão
        verbose_name="País de Origem"
    )
    
    TEMA_CHOICES = (
        ("TS", "Taylor Swift (Debut)"),
        ("FEARLESS", "Fearless"),
        ("SPEAK_NOW", "Speak Now"),
        ("RED", "Red"),
        ("1989", "1989"),
        ("REPUTATION", "Reputation"),
        ("LOVER", "Lover"),
        ("FOLKLORE", "Folklore"),
        ("EVERMORE", "Evermore"),
        ("MIDNIGHTS", "Midnights"),
        ("TTPD", "The Tortured Poets Department"),
        ("SHOWGIRL", "The Life of a Showgirl")
    )
    
    tema = models.CharField(
        max_length=20,
        choices=TEMA_CHOICES,
        default="MIDNIGHTS",
        verbose_name="Tema do Álbum"
    )

    class Meta:
        verbose_name = "Usuário"
        verbose_name_plural = "Usuários"
        
