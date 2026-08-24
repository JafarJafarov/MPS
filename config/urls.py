from django.contrib import admin
from django.urls import include, path


urlpatterns = [

    # =====================================================
    # DJANGO ADMIN
    # =====================================================

    path(
        "admin/",
        admin.site.urls
    ),

    # =====================================================
    # PLANNING
    # =====================================================

    path(
        "planning/",
        include("planning.urls")
    ),

    # =====================================================
    # CAPACITY
    # =====================================================

    path(
        "capacity/",
        include("capacity.urls")
    ),

    # =====================================================
    # SCHEDULING
    # =====================================================

    path(
        "scheduling/",
        include("scheduling.urls")
    ),

]