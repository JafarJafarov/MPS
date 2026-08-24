from django.urls import path

from . import views


app_name = "scheduling"


urlpatterns = [

    path(
        "<int:plan_id>/",
        views.scheduling_dashboard,
        name="dashboard",
    ),

    path(
        "<int:plan_id>/export/excel/",
        views.export_weekly_plan_excel,
        name="export_excel",
    ),

    path(
        "<int:plan_id>/export/pdf/",
        views.export_weekly_plan_pdf,
        name="export_pdf",
    ),

]
