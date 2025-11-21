import pytest
from datetime import date
from django.db.utils import IntegrityError
from apps.albums.models import Album
from apps.tracks.models import Track

@pytest.fixture
def album_fearless(db):
    """Fixture para criar um Álbum base (Fearless)."""
    return Album.objects.create(
        title="Fearless (Taylor's Version)",
        release_date=date(2021, 4, 9)
    )

@pytest.fixture
def album_red(db):
    """Fixture para criar um segundo Álbum (Red) para testes de ordenação."""
    return Album.objects.create(
        title="Red (Taylor's Version)",
        release_date=date(2021, 11, 12)
    )

@pytest.mark.django_db
class TestTrackModel:
    
    def test_track_creation_success(self, album_fearless):
        """Teste Unitário: Verifica a criação bem-sucedida de uma Música."""
        track = Track.objects.create(
            album=album_fearless,
            title="Love Story (Taylor's Version)",
            track_number=2
        )
        
        # Verifica os valores dos campos
        assert track.title == "Love Story (Taylor's Version)"
        assert track.track_number == 2
        assert track.album.title == "Fearless (Taylor's Version)"
        assert Track.objects.count() == 1

    def test_track_str_representation(self, album_fearless):
        """Teste Unitário: Verifica a representação em string (__str__)."""
        track = Track.objects.create(
            album=album_fearless,
            title="Fifteen (Taylor's Version)",
            track_number=4
        )
        # Formato esperado: "4. Fifteen (Taylor's Version) (Fearless (Taylor's Version))"
        expected_str = "4. Fifteen (Taylor's Version) (Fearless (Taylor's Version))"
        assert str(track) == expected_str

    def test_unique_together_constraint(self, album_fearless):
        """Teste Unitário: Garante que (album, track_number) é único."""
        
        # 1. Cria a primeira música (faixa 5)
        Track.objects.create(
            album=album_fearless,
            title="You Belong with Me",
            track_number=5
        )
        
        # 2. Tenta criar uma segunda música na mesma faixa e álbum (DEVE FALHAR)
        with pytest.raises(IntegrityError):
            Track.objects.create(
                album=album_fearless,
                title="Another Song",
                track_number=5 # Número de faixa duplicado
            )
            
    def test_unique_together_allows_same_number_different_album(self, album_fearless, album_red):
        """Teste Unitário: Garante que o mesmo track_number pode ser usado em álbuns diferentes."""
        
        # Faixa 1 no Fearless (OK)
        Track.objects.create(
            album=album_fearless,
            title="Faixa 1 - Fearless",
            track_number=1
        )
        
        # Faixa 1 no Red (DEVE SER OK)
        Track.objects.create(
            album=album_red,
            title="Faixa 1 - Red",
            track_number=1
        )
        
        assert Track.objects.count() == 2

    def test_track_ordering_meta(self, album_fearless, album_red):
        """Teste Unitário: Verifica a ordenação por release_date do álbum e track_number."""
        
        # Fearless (2021/04/09): Faixa 3
        Track.objects.create(album=album_fearless, title="Faixa 3 Fearless", track_number=3)
        # Red (2021/11/12): Faixa 1
        Track.objects.create(album=album_red, title="Faixa 1 Red", track_number=1)
        # Fearless (2021/04/09): Faixa 1
        Track.objects.create(album=album_fearless, title="Faixa 1 Fearless", track_number=1)
        
        # A ordenação esperada (ordering = ['album__release_date', 'track_number']):
        # 1. Faixa 1 Fearless (Álbum mais antigo)
        # 2. Faixa 3 Fearless (Mesmo álbum, track_number maior)
        # 3. Faixa 1 Red (Álbum mais recente)
        
        ordered_tracks = Track.objects.all()
        
        assert ordered_tracks[0].title == "Faixa 1 Fearless"
        assert ordered_tracks[1].title == "Faixa 3 Fearless"
        assert ordered_tracks[2].title == "Faixa 1 Red"