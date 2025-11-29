from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    AlbumRankingView,
    TrackRankingView,
    CompatibilityView,
    GroupCompatibilityView,
    GroupTrackCompatibilityView,
    GlobalRankingListView,
    TrackCompatibilityView,
    GroupRankingViewSet,
    UserRankedTitlesView,
    OtherUserRankedTitlesView,
)

router = DefaultRouter()
router.register(r"group_rankings", GroupRankingViewSet, basename="group-ranking")


urlpatterns = [
    path("albums/", AlbumRankingView.as_view(), name="album-ranking"),
    path(
        "tracks/<int:album_id>/",
        TrackRankingView.as_view(),
        name="track-ranking-by-album",
    ),
    path(
        "compare/albums/<int:target_user_id>/",
        CompatibilityView.as_view(),
        name="album-compatibility",
    ),
    path(
        "compare/groups/<int:group_id>/",
        GroupCompatibilityView.as_view(),
        name="group-compatibility",
    ),
    path(
        "compare/tracks/<int:target_user_id>/album/<int:album_id>/",
        TrackCompatibilityView.as_view(),
        name="track-compatibility-duo",
    ),
    path(
        "compare/groups/<int:group_id>/tracks/<int:album_id>/",
        GroupTrackCompatibilityView.as_view(),
        name="group-track-compatibility",
    ),
    path("global/", GlobalRankingListView.as_view(), name="global-ranking-list"),
    path(
        "user/ranked-titles/", UserRankedTitlesView.as_view(), name="user-ranked-titles"
    ),
    path(
        "user/<int:pk>/ranked-titles/",
        OtherUserRankedTitlesView.as_view(),
        name="other-user-ranked-titles",
    ),
    path("", include(router.urls)),
]
