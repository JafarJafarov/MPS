from django.urls import path
from . import views


app_name = "capacity"


urlpatterns = [
    path(
        "import/",
        views.capacity_import,
        name="capacity_import"
    ),

    path(
        "template/",
        views.download_capacity_template,
        name="capacity_template"
    ),
]