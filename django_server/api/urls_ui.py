from django.urls import path

from . import views_ui
from .views_auth import UiLoginView, ui_firebase_login, ui_staff_login_api

urlpatterns = [
    path("", views_ui.ui_home, name="ui_home"),
    path("set-language/", views_ui.ui_set_language, name="ui_set_language"),
    path("login/", UiLoginView.as_view(), name="ui_login"),
    path("login/firebase/", ui_firebase_login, name="ui_login_firebase"),
    path("login/submit/", ui_staff_login_api, name="ui_login_submit"),
    path("logout/", views_ui.ui_logout, name="ui_logout"),
    path("users/", views_ui.collector_user_list, name="ui_collector_user_list"),
    path("users/sync-firebase/", views_ui.collector_user_sync_firebase, name="ui_collector_user_sync_firebase"),
    path("users/<int:pk>/", views_ui.collector_user_detail, name="ui_collector_user_detail"),
    path("projects/", views_ui.project_list, name="ui_project_list"),
    path("projects/new/", views_ui.project_new, name="ui_project_new"),
    path("projects/<str:project_id>/", views_ui.project_detail, name="ui_project_detail"),
    path(
        "projects/<str:project_id>/git-sync/",
        views_ui.project_git_sync,
        name="ui_project_git_sync",
    ),
    path(
        "projects/<str:project_id>/ssh-key/",
        views_ui.project_update_ssh_key,
        name="ui_project_update_ssh_key",
    ),
    path(
        "projects/<str:project_id>/git-settings/",
        views_ui.project_git_settings,
        name="ui_project_git_settings",
    ),
    path(
        "projects/<str:project_id>/storage-settings/",
        views_ui.project_storage_settings,
        name="ui_project_storage_settings",
    ),
    path(
        "projects/<str:project_id>/storage-check/",
        views_ui.project_storage_check,
        name="ui_project_storage_check",
    ),
    path(
        "projects/<str:project_id>/config/builder/<str:form_id>/",
        views_ui.project_config_builder,
        name="ui_project_config_builder",
    ),
    path(
        "projects/<str:project_id>/config/builder/",
        views_ui.project_config_builder,
        kwargs={"form_id": "default"},
        name="ui_project_config_builder_default",
    ),
    path(
        "projects/<str:project_id>/config/validate/",
        views_ui.project_config_validate_api,
        name="ui_project_config_validate_api",
    ),
    path(
        "projects/<str:project_id>/forms/new/",
        views_ui.project_form_create,
        name="ui_project_form_create",
    ),
    path(
        "projects/<str:project_id>/config/<str:form_id>/",
        views_ui.project_config,
        name="ui_project_config",
    ),
    path(
        "projects/<str:project_id>/config/",
        views_ui.project_config,
        kwargs={"form_id": "default"},
        name="ui_project_config_default",
    ),
    path("projects/<str:project_id>/media/", views_ui.project_media, name="ui_project_media"),
    path("projects/<str:project_id>/delete/", views_ui.project_delete, name="ui_project_delete"),
    path("packages/", views_ui.package_list, name="ui_package_list"),
    path(
        "projects/<str:project_id>/packages/<str:package_id>/depth/<path:logical_path>",
        views_ui.package_depth_blob,
        name="ui_package_depth_blob",
    ),
    path(
        "projects/<str:project_id>/packages/<str:package_id>/save/",
        views_ui.package_manifest_save,
        name="ui_package_manifest_save",
    ),
    path(
        "projects/<str:project_id>/packages/<str:package_id>/delete/",
        views_ui.package_delete,
        name="ui_package_delete",
    ),
    path(
        "projects/<str:project_id>/packages/<str:package_id>/viz-data/",
        views_ui.package_viz_data,
        name="ui_package_viz_data",
    ),
    path(
        "projects/<str:project_id>/packages/<str:package_id>/blobs/<path:logical_path>/",
        views_ui.package_blob_download,
        name="ui_package_blob_download",
    ),
    path(
        "projects/<str:project_id>/packages/<str:package_id>/",
        views_ui.package_workspace,
        name="ui_package_workspace",
    ),
]
