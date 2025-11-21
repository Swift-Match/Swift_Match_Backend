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
    
    