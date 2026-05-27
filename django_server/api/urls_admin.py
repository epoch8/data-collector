from django.urls import path

from . import views_admin

urlpatterns = [
    path("v1/projects", views_admin.AdminProjectsListView.as_view()),
    path(
        "v1/projects/<str:project_id>/packages",
        views_admin.AdminPackageListView.as_view(),
    ),
    path(
        "v1/projects/<str:project_id>/packages/<str:package_id>/workspace",
        views_admin.AdminPackageWorkspaceView.as_view(),
    ),
    path(
        "v1/projects/<str:project_id>/packages/<str:package_id>/manifest",
        views_admin.AdminPackageManifestPatchView.as_view(),
    ),
    path(
        "v1/projects/<str:project_id>/packages/<str:package_id>/blobs/<int:blob_pk>/preview",
        views_admin.AdminBlobPreviewView.as_view(),
    ),
]
