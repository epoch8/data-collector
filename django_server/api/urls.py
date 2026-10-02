from django.conf import settings
from django.urls import path, re_path

from . import views
from .proxy import proxy_view

urlpatterns = [
    path("health", views.health),
    path("v1/projects", views.ProjectsCatalogView.as_view()),
    path(
        "v1/projects/<str:project_id>/config",
        views.ProjectConfigView.as_view(),
    ),
    path(
        "v1/projects/<str:project_id>/forms",
        views.ProjectFormsView.as_view(),
    ),
    path(
        "v1/projects/<str:project_id>/forms/<str:form_id>/config",
        views.ProjectFormConfigView.as_view(),
    ),
    re_path(
        r"^v1/projects/(?P<project_id>[^/]+)/assets/(?P<asset_path>.*)$",
        views.ProjectAssetGetView.as_view(),
    ),
    path(
        "v1/projects/<str:project_id>/packages",
        views.PackageSessionCreateView.as_view(),
    ),
    re_path(
        r"^v1/projects/(?P<project_id>[^/]+)/packages/(?P<package_id>[^/]+)/blobs/(?P<blob_path>.*)$",
        views.PackageBlobPutView.as_view(),
    ),
    path(
        "v1/projects/<str:project_id>/packages/<str:package_id>/manifest",
        views.PackageManifestPutView.as_view(),
    ),
    path(
        "v1/projects/<str:project_id>/packages/<str:package_id>/commit",
        views.PackageCommitView.as_view(),
    ),
    path(
        "v1/projects/<str:project_id>/packages/<str:package_id>",
        views.PackageDetailView.as_view(),
    ),
]

# Маршруты, которые всегда обрабатываются локально, даже при включённом прокси.
LOCAL_ONLY_ROUTES = frozenset({"v1/projects"})

if settings.DATAPIPE_PROXY_URL:
    # Те же маршруты, но обрабатываются удалённым сервером.
    urlpatterns = [
        p if str(p.pattern) in LOCAL_ONLY_ROUTES else re_path(p.pattern.regex.pattern, proxy_view)
        for p in urlpatterns
    ]
