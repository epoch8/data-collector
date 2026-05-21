from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("ui/", include("api.urls_ui")),
    path("", include("api.urls")),
]
