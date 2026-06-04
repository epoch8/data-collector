from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("admin-api/", include("api.urls_admin")),
    path("ui/api/", include("api.urls_ui_api")),
    path("ui/", include("api.urls_ui")),
    path("", include("api.urls")),
]
