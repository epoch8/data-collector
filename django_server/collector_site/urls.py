from django.urls import include, path

urlpatterns = [
    path("ui/", include("api.urls_ui")),
    path("", include("api.urls")),
]
