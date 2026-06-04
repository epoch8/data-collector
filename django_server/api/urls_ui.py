from django.urls import path, re_path

from . import views_ui
from .views_auth import UiLoginView, ui_login_page

urlpatterns = [
    path("", views_ui.ui_home, name="ui_home"),
    path("login/", ui_login_page, name="ui_login"),
    path("login/submit/", UiLoginView.as_view(), name="ui_login_submit"),
    path("logout/", views_ui.ui_logout, name="ui_logout"),
    path("users/", views_ui.collector_user_list, name="ui_collector_user_list"),
    path("users/sync-firebase/", views_ui.collector_user_sync_firebase, name="ui_collector_user_sync_firebase"),
    path("users/<int:pk>/", views_ui.collector_user_detail, name="ui_collector_user_detail"),
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
    path("packages/", views_ui.packages_spa, name="ui_packages_spa"),
    re_path(
        r"^packages/(?P<subpath>.*)$",
        views_ui.packages_spa,
        name="ui_packages_spa_catchall",
    ),
]
