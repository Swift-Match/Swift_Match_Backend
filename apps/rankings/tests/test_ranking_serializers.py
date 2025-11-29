import pytest
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIRequestFactory
from apps.rankings.models import (
    AlbumRanking,
    TrackRanking,
    UserRanking,
    GroupRanking,
    RankedTrack,
)
from apps.rankings.serializers import (
    AlbumRankingSerializer,
    TrackRankingSerializer,
    UserRankingCreateSerializer,
    GroupRankingCreateSerializer,
)
from apps.albums.models import Album
from apps.tracks.models import Track
from apps.social.models import GroupMembership


@pytest.fixture
def api_request(user_fixture):
    factory = APIRequestFactory()
    request = factory.get("/")
    request.user = user_fixture
    return request


@pytest.mark.django_db
class TestAlbumRankingSerializer:

    def test_album_ranking_successful_creation(
        self, user_fixture, album_fixture, api_request
    ):
        """Testa a criação bem-sucedida de um AlbumRanking."""
        album2 = Album.objects.create(
            title="Fearless (Taylor's Version)", release_date="2021-04-09"
        )

        data = {
            "rankings": [
                {"album_id": album_fixture.id, "position": 1},
                {"album_id": album2.id, "position": 2},
            ]
        }

        serializer = AlbumRankingSerializer(data=data, context={"request": api_request})

        assert serializer.is_valid(), serializer.errors

        ranking_objects = serializer.create(
            serializer.validated_data, user=user_fixture
        )

        assert len(ranking_objects) == 2
        assert AlbumRanking.objects.filter(user=user_fixture).count() == 2
        assert (
            AlbumRanking.objects.get(user=user_fixture, album=album_fixture).position
            == 1
        )

    def test_album_ranking_unique_position_validation_fails(
        self, user_fixture, album_fixture, api_request
    ):
        """Testa se posições duplicadas causam erro de validação."""
        album2 = Album.objects.create(
            title="Red (Taylor's Version)", release_date="2021-11-12"
        )

        data = {
            "rankings": [
                {"album_id": album_fixture.id, "position": 1},
                {"album_id": album2.id, "position": 1},
            ]
        }

        serializer = AlbumRankingSerializer(data=data, context={"request": api_request})

        assert serializer.is_valid()

        with pytest.raises(ValidationError) as excinfo:
            serializer.create(serializer.validated_data, user=user_fixture)

        assert "As posições no ranking devem ser únicas." in excinfo.value.detail[0]

    def test_album_ranking_clears_previous_rankings(
        self, user_fixture, album_fixture, api_request
    ):
        """Testa se rankings anteriores do usuário são excluídos."""
        AlbumRanking.objects.create(user=user_fixture, album=album_fixture, position=1)
        assert AlbumRanking.objects.filter(user=user_fixture).count() == 1

        album2 = Album.objects.create(
            title="1989 (Taylor's Version)", release_date="2023-10-27"
        )

        data = {
            "rankings": [
                {"album_id": album2.id, "position": 1},
            ]
        }

        serializer = AlbumRankingSerializer(data=data, context={"request": api_request})
        serializer.is_valid()
        serializer.create(serializer.validated_data, user=user_fixture)

        assert AlbumRanking.objects.filter(user=user_fixture).count() == 1
        assert AlbumRanking.objects.get(user=user_fixture).album == album2


@pytest.mark.django_db
class TestTrackRankingSerializer:

    def test_track_ranking_successful_creation(
        self, user_fixture, album_fixture, track_fixture, api_request
    ):
        """Testa a criação bem-sucedida de um TrackRanking (com todas as músicas do álbum)."""
        track2 = Track.objects.create(album=album_fixture, title="Mine", track_number=1)

        data = {
            "album_id": album_fixture.id,
            "rankings": [
                {"track_id": track_fixture.id, "position": 2},
                {"track_id": track2.id, "position": 1},
            ],
        }

        serializer = TrackRankingSerializer(data=data, context={"request": api_request})
        assert serializer.is_valid(), serializer.errors

        ranking_objects = serializer.create(
            serializer.validated_data, user=user_fixture
        )

        assert len(ranking_objects) == 2
        assert TrackRanking.objects.filter(user=user_fixture).count() == 2
        assert TrackRanking.objects.get(user=user_fixture, track=track2).position == 1

    def test_track_ranking_invalid_track_album_mismatch(
        self, user_fixture, album_fixture, track_fixture, api_request
    ):
        """Testa se a validação falha se uma track não pertencer ao álbum."""
        album_diferente = Album.objects.create(
            title="Midnights", release_date="2022-10-21"
        )
        track_externa = Track.objects.create(
            album=album_diferente, title="Anti-Hero", track_number=3
        )

        data = {
            "album_id": album_fixture.id,
            "rankings": [
                {"track_id": track_fixture.id, "position": 1},
                {"track_id": track_externa.id, "position": 2},
            ],
        }

        serializer = TrackRankingSerializer(data=data, context={"request": api_request})
        assert serializer.is_valid()

        with pytest.raises(ValidationError) as excinfo:
            serializer.create(serializer.validated_data, user=user_fixture)

        assert "tracks" in excinfo.value.detail
        assert any("não" in str(error) for error in excinfo.value.detail["tracks"])

    def test_track_ranking_clears_previous_rankings_for_album(
        self, user_fixture, album_fixture, track_fixture, api_request
    ):
        """Testa se apenas os rankings de tracks pertencentes ao álbum atual são limpos."""
        track2 = Track.objects.create(
            album=album_fixture, title="Haunted", track_number=3
        )

        TrackRanking.objects.create(user=user_fixture, track=track_fixture, position=10)

        album_outro = Album.objects.create(title="Lover", release_date="2019-08-23")
        track_outro = Track.objects.create(
            album=album_outro, title="Cruel Summer", track_number=2
        )
        TrackRanking.objects.create(user=user_fixture, track=track_outro, position=1)

        assert TrackRanking.objects.filter(user=user_fixture).count() == 2

        data = {
            "album_id": album_fixture.id,
            "rankings": [
                {"track_id": track2.id, "position": 1},
            ],
        }

        serializer = TrackRankingSerializer(data=data, context={"request": api_request})
        serializer.is_valid()
        serializer.create(serializer.validated_data, user=user_fixture)

        assert TrackRanking.objects.filter(user=user_fixture).count() == 2
        assert not TrackRanking.objects.filter(track=track_fixture).exists()
        assert TrackRanking.objects.filter(track=track_outro).exists()


@pytest.mark.django_db
class TestUserRankingCreateSerializer:

    def test_user_ranking_creation_successful(
        self, user_fixture, album_fixture, track_fixture, api_request, group_fixture
    ):
        """Testa a criação do ranking do usuário com tracks aninhadas."""

        group_ranking_instance = GroupRanking.objects.create(
            group=group_fixture, album=album_fixture, added_by=user_fixture
        )

        track2 = Track.objects.create(
            album=album_fixture, title="Sparks Fly", track_number=2
        )

        data = {
            "group_ranking": group_ranking_instance.id,
            "ranked_tracks": [
                {"track_id": track2.id, "position": 1},
                {"track_id": track_fixture.id, "position": 2},
            ],
        }

        serializer = UserRankingCreateSerializer(
            data=data, context={"request": api_request}
        )

        assert serializer.is_valid(), serializer.errors

        user_ranking_obj = serializer.save(user=user_fixture)

        assert UserRanking.objects.filter(user=user_fixture).count() == 1
        assert RankedTrack.objects.filter(user_ranking=user_ranking_obj).count() == 2

        rank_1 = RankedTrack.objects.get(user_ranking=user_ranking_obj, track=track2)
        assert rank_1.position == 1

        assert user_ranking_obj.user == user_fixture

    def test_user_ranking_missing_user_context(
        self, album_fixture, user_fixture, group_fixture
    ):
        """Testa a falha se o contexto do usuário não for fornecido (simulando falta de autenticação)."""

        from django.contrib.auth.models import AnonymousUser
        from rest_framework.test import APIRequestFactory

        group_ranking_instance = GroupRanking.objects.create(
            group=group_fixture, album=album_fixture, added_by=user_fixture
        )
        track2 = Track.objects.create(
            album=album_fixture, title="Sparks Fly", track_number=2
        )

        data = {
            "group_ranking": group_ranking_instance.id,
            "ranked_tracks": [
                {"track_id": track2.id, "position": 1},
            ],
        }

        api_request = APIRequestFactory().get("/")
        api_request.user = AnonymousUser()

        serializer = UserRankingCreateSerializer(
            data=data, context={"request": api_request}
        )

        assert not serializer.is_valid()

        assert "user" in serializer.errors


@pytest.mark.django_db
class TestGroupRankingCreateSerializer:

    def test_group_ranking_creation_by_member_successful(
        self, user_fixture, album_fixture, group_fixture, api_request
    ):
        """Testa a criação bem-sucedida por um membro do grupo (validação de permissão)."""
        GroupMembership.objects.create(
            user=user_fixture, group=group_fixture, is_admin=False
        )

        data = {"group": group_fixture.id, "album": album_fixture.id}

        serializer = GroupRankingCreateSerializer(
            data=data, context={"request": api_request}
        )

        assert serializer.is_valid(), serializer.errors

        group_ranking_obj = serializer.save()

        assert GroupRanking.objects.count() == 1
        assert group_ranking_obj.group == group_fixture
        assert group_ranking_obj.added_by == user_fixture

    def test_group_ranking_creation_by_non_member_fails(
        self, user_fixture, album_fixture, group_fixture, api_request
    ):
        """Testa se a criação falha para um usuário que não é membro do grupo."""

        data = {"group": group_fixture.id, "album": album_fixture.id}

        serializer = GroupRankingCreateSerializer(
            data=data, context={"request": api_request}
        )

        with pytest.raises(ValidationError) as excinfo:
            serializer.is_valid(raise_exception=True)

        assert "Você precisa ser membro deste grupo para adicionar um ranking." in str(
            excinfo.value.detail
        )


def test_group_ranking_unique_constraint(
    user_fixture, album_fixture, group_fixture, api_request
):
    """Testa a restrição de unicidade (group e album)."""
    GroupMembership.objects.create(
        user=user_fixture, group=group_fixture, is_admin=False
    )

    GroupRanking.objects.create(
        group=group_fixture, album=album_fixture, added_by=user_fixture
    )

    data = {"group": group_fixture.id, "album": album_fixture.id}

    serializer = GroupRankingCreateSerializer(
        data=data, context={"request": api_request}
    )

    assert not serializer.is_valid()

    assert "non_field_errors" in serializer.errors
    assert any(
        "já existe" in str(error) for error in serializer.errors["non_field_errors"]
    )
