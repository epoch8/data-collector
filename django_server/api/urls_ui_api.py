from django.urls import path

from . import views_ui_api
from .views_auth import ui_staff_login_api

urlpatterns = [
    path("v1/staff-login", ui_staff_login_api, name="ui_api_staff_login"),
    path("v1/me", views_ui_api.UiMeView.as_view(), name="ui_api_me"),
    path("v1/projects", views_ui_api.UiProjectsListView.as_view(), name="ui_api_projects"),
    path(
        "v1/projects/<str:project_id>/config",
        views_ui_api.UiProjectConfigView.as_view(),
        name="ui_api_project_config",
    ),
    path(
        "v1/projects/<str:project_id>/packages",
        views_ui_api.UiPackageListView.as_view(),
        name="ui_api_packages",
    ),
    path(
        "v1/projects/<str:project_id>/packages/<str:package_id>/workspace",
        views_ui_api.UiPackageWorkspaceView.as_view(),
        name="ui_api_package_workspace",
    ),
    path(
        "v1/projects/<str:project_id>/packages/<str:package_id>/manifest",
        views_ui_api.UiPackageManifestPatchView.as_view(),
        name="ui_api_package_manifest",
    ),
    path(
        "v1/projects/<str:project_id>/packages/<str:package_id>/blobs/<int:blob_pk>/preview",
        views_ui_api.UiBlobPreviewView.as_view(),
        name="ui_api_blob_preview",
    ),
    path(
        "v1/field-changelog",
        views_ui_api.UiFieldChangelogView.as_view(),
        name="ui_api_field_changelog",
    ),
]
