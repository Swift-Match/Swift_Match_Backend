import pytest
from datetime import date
from apps.albums.models import Album
from django.db.utils import IntegrityError

@pytest.mark.django_db
class TestAlbumModel:
    
    @pytest.fixture
    def setup_album(self):
        """Fixture para criar um álbum padrão."""
        return Album.objects.create(
            title="Fearless (Taylor's Version)",
            release_date=date(2021, 4, 9),
            cover_image_url="http://example.com/fearless.jpg"
        )
        
    def test_album_creation_success(self, setup_album):
        """Teste Unitário: Verifica a criação bem-sucedida de um Álbum."""
        album = setup_album
        
        # 1. Verifica os valores dos campos
        assert album.title == "Fearless (Taylor's Version)"
        assert album.release_date == date(2021, 4, 9)
        assert album.cover_image_url == "http://example.com/fearless.jpg"
        
        # 2. Verifica se o objeto existe no banco
        assert Album.objects.count() == 1

    def test_album_str_representation(self, setup_album):
        """Teste Unitário: Verifica a representação em string (__str__)."""
        album = setup_album
        assert str(album) == "Fearless (Taylor's Version)"

    def test_album_unique_title_constraint(self, setup_album):
        """Teste Unitário: Garante que títulos duplicados não são permitidos."""
        
        # Tenta criar um segundo álbum com o mesmo título
        with pytest.raises(IntegrityError):
            Album.objects.create(
                title="Fearless (Taylor's Version)", # Título duplicado
                release_date=date(2022, 1, 1)
            )

    def test_album_ordering_meta(self):
        """Teste Unitário: Verifica se a ordenação Meta está funcionando (pela data)."""
        
        # Cria álbuns fora de ordem cronológica
        Album.objects.create(
            title="1989 (Taylor's Version)",
            release_date=date(2023, 10, 27)
        )
        Album.objects.create(
            title="Red (Taylor's Version)",
            release_date=date(2021, 11, 12)
        )
        
        # A Meta ordering deve garantir que 'Red' (2021) venha antes de '1989' (2023)
        ordered_albums = Album.objects.all()
        
        assert ordered_albums[0].title == "Red (Taylor's Version)"
        assert ordered_albums[1].title == "1989 (Taylor's Version)"

    def test_cover_image_url_can_be_null(self):
        """Teste Unitário: Garante que o campo URL pode ser nulo/vazio."""
        
        album = Album.objects.create(
            title="Debut",
            release_date=date(2006, 10, 24),
            cover_image_url=None # Deve permitir None no banco
        )
        
        assert album.cover_image_url is None