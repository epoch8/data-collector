from django.urls import path, re_path

from . import views

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
