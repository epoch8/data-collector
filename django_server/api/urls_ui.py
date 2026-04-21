from django.contrib.auth.views import LoginView
from django.urls import path

from . import views_ui

urlpatterns = [
    path("", views_ui.ui_home, name="ui_home"),
    path(
        "login/",
        LoginView.as_view(
            template_name="ui/login.html",
            redirect_authenticated_user=True,
        ),
        name="ui_login",
    ),
    path("logout/", views_ui.ui_logout, name="ui_logout"),
    path("projects/", views_ui.project_list, name="ui_project_list"),
    path("projects/new/", views_ui.project_new, name="ui_project_new"),
    path("projects/<str:project_id>/", views_ui.project_detail, name="ui_project_detail"),
    path("projects/<str:project_id>/config/", views_ui.project_config, name="ui_project_config"),
    path(
        "projects/<str:project_id>/config/builder/",
        views_ui.project_config_builder,
        name="ui_project_config_builder",
    ),
    path(
        "projects/<str:project_id>/config/validate/",
        views_ui.project_config_validate_api,
        name="ui_project_config_validate_api",
    ),
    path("projects/<str:project_id>/media/", views_ui.project_media, name="ui_project_media"),
    path("projects/<str:project_id>/delete/", views_ui.project_delete, name="ui_project_delete"),
    path("packages/", views_ui.package_list, name="ui_package_list"),
    path(
        "projects/<str:project_id>/packages/<str:package_id>/",
        views_ui.package_detail,
        name="ui_package_detail",
    ),
    path(
        "projects/<str:project_id>/packages/<str:package_id>/blobs/<int:blob_pk>/",
        views_ui.package_blob_download,
        name="ui_package_blob_download",
    ),
]
