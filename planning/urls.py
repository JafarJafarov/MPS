from django.urls import path

from . import views


app_name = "planning"


urlpatterns = [

    path(
        "sap-import/",
        views.sap_import,
        name="sap_import"
    ),

    path(
        "sap-template/",
        views.download_sap_template,
        name="sap_template"
    ),

    path(
        "weeks/",
        views.weekly_plan_list,
        name="weekly_plan_list"
    ),

    path(
        "weeks/new/",
        views.weekly_plan_create,
        name="weekly_plan_create"
    ),

    path(
        "itk-import/",
        views.itk_import,
        name="itk_import"
    ),

    path(
        "itk-template/",
        views.download_itk_template,
        name="itk_template"
    ),

    path(
        "weeks/<int:plan_id>/itk-operations/",
        views.itk_operations,
        name="itk_operations"
    ),

]