from django.urls import path

from . import views

urlpatterns = [
    path("textures/upload/", views.upload_texture, name="texture-upload"),
    path("textures/session/<str:session_key>/", views.list_session_textures, name="texture-list"),
    path("textures/session/<str:session_key>/delete/", views.delete_session_textures, name="texture-delete"),
    path("assets/", views.list_assets, name="asset-list"),
    path("assets/create/", views.create_asset, name="asset-create"),
    path("system/cleanup/", views.trigger_cleanup, name="trigger-cleanup"),
]