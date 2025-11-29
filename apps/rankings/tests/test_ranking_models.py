import pytest
from apps.albums.models import Album
from django.db.utils import IntegrityError
from apps.rankings.models import (
    AlbumRanking, TrackRanking, CountryGlobalRanking, 
    GroupRanking, UserRanking, RankedTrack, Notification
)

@pytest.mark.django_db
def test_album_ranking_creation(user_fixture, album_fixture):
    """Testa a criação bem-sucedida de AlbumRanking."""
    ranking = AlbumRanking.objects.create(
        user=user_fixture,
        album=album_fixture,
        position=1
    )
    assert ranking.user == user_fixture
    assert ranking.position == 1
    assert str(ranking) == f"{user_fixture.username}'s Ranking: {album_fixture.title} (1°)"

@pytest.mark.django_db
def test_album_ranking_unique_album_constraint(user_fixture, album_fixture):
    """Garante que um usuário não pode rankear o mesmo álbum duas vezes."""
    AlbumRanking.objects.create(user=user_fixture, album=album_fixture, position=1)
    
    with pytest.raises(IntegrityError):
        AlbumRanking.objects.create(user=user_fixture, album=album_fixture, position=2)

@pytest.mark.django_db
def test_album_ranking_unique_position_constraint(user_fixture, album_fixture, track_fixture):
    """Garante que um usuário não pode ter dois álbuns na mesma posição."""
    album_b = Album.objects.create(title="Album B", release_date='2020-01-01', cover_image_url="http://b.jpg")
    AlbumRanking.objects.create(user=user_fixture, album=album_fixture, position=1)
    
    with pytest.raises(IntegrityError):
        AlbumRanking.objects.create(user=user_fixture, album=album_b, position=1)
        
@pytest.mark.django_db
def test_track_ranking_unique_track_constraint(user_fixture, track_fixture):
    """Garante que um usuário não pode rankear a mesma música duas vezes."""
    TrackRanking.objects.create(user=user_fixture, track=track_fixture, position=5)
    
    with pytest.raises(IntegrityError):
        TrackRanking.objects.create(user=user_fixture, track=track_fixture, position=6)

@pytest.mark.django_db
def test_track_ranking_str(user_fixture, track_fixture):
    """Testa o método __str__ para TrackRanking."""
    ranking = TrackRanking.objects.create(user=user_fixture, track=track_fixture, position=10)
    assert str(ranking) == f"{user_fixture.username}'s Track Ranking: {track_fixture.title} (10°)"


@pytest.mark.django_db
def test_country_global_ranking_unique_country(album_fixture, track_fixture):
    """Garante que só pode existir um ranking global por nome de país."""
    CountryGlobalRanking.objects.create(
        country_name='Brazil', 
        consensus_album=album_fixture, 
        global_consensus_track=track_fixture
    )
    
    with pytest.raises(IntegrityError):
        CountryGlobalRanking.objects.create(country_name='Brazil')

@pytest.mark.django_db
def test_country_global_ranking_str():
    """Testa o método __str__ para CountryGlobalRanking."""
    ranking = CountryGlobalRanking.objects.create(country_name='Germany')
    assert str(ranking) == "Ranking de Álbuns: Germany"


@pytest.mark.django_db
def test_group_ranking_unique_together(group_fixture, album_fixture, user_fixture):
    """Garante que um álbum só pode ser adicionado a um grupo uma vez."""
    GroupRanking.objects.create(group=group_fixture, album=album_fixture, added_by=user_fixture)
    
    with pytest.raises(IntegrityError):
        GroupRanking.objects.create(group=group_fixture, album=album_fixture, added_by=user_fixture)

@pytest.mark.django_db
def test_group_ranking_str(group_fixture, album_fixture, user_fixture):
    """Testa o método __str__ para GroupRanking."""
    group_ranking = GroupRanking.objects.create(group=group_fixture, album=album_fixture, added_by=user_fixture)
    assert str(group_ranking) == f"{album_fixture.title} em {group_fixture.name}"


@pytest.mark.django_db
def test_user_ranking_unique_together(user_fixture, group_fixture, album_fixture):
    """Garante que um usuário só pode submeter um ranking para um GroupRanking uma vez."""
    group_ranking = GroupRanking.objects.create(group=group_fixture, album=album_fixture, added_by=user_fixture)
    UserRanking.objects.create(group_ranking=group_ranking, user=user_fixture)
    
    with pytest.raises(IntegrityError):
        UserRanking.objects.create(group_ranking=group_ranking, user=user_fixture)

@pytest.mark.django_db
def test_user_ranking_str(user_fixture, group_fixture, album_fixture):
    """Testa o método __str__ para UserRanking."""
    group_ranking = GroupRanking.objects.create(group=group_fixture, album=album_fixture, added_by=user_fixture)
    user_ranking = UserRanking.objects.create(group_ranking=group_ranking, user=user_fixture)
    assert str(user_ranking) == f"{user_fixture.username} submeteu {group_ranking.album.title}"


@pytest.mark.django_db
def test_ranked_track_creation(user_fixture, group_fixture, album_fixture, track_fixture):
    """Testa a criação bem-sucedida de RankedTrack."""
    group_ranking = GroupRanking.objects.create(group=group_fixture, album=album_fixture, added_by=user_fixture)
    user_ranking = UserRanking.objects.create(group_ranking=group_ranking, user=user_fixture)
    
    ranked_track = RankedTrack.objects.create(
        user_ranking=user_ranking,
        track=track_fixture,
        position=1
    )
    assert ranked_track.position == 1


@pytest.mark.django_db
def test_notification_creation(user_fixture):
    """Testa a criação bem-sucedida de Notificação."""
    notification = Notification.objects.create(
        recipient=user_fixture,
        type='INVITE',
        message='Você foi convidado para um grupo!',
        related_id=123
    )
    
    assert notification.recipient == user_fixture
    assert notification.is_read is False
    assert notification.type == 'INVITE'
    assert 'para' in str(notification)