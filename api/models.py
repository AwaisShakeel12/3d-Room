import os
import uuid
from datetime import timedelta

from django.db import models
from django.utils import timezone


def texture_upload_path(instance, filename):
    ext = os.path.splitext(filename)[1].lower() or ".jpg"
    return f"textures/{instance.session_key}/{uuid.uuid4().hex}{ext}"


def asset_model_path(instance, filename):
    ext = os.path.splitext(filename)[1].lower() or ".glb"
    return f"models/{instance.category}/{uuid.uuid4().hex}{ext}"


def asset_thumb_path(instance, filename):
    ext = os.path.splitext(filename)[1].lower() or ".jpg"
    return f"thumbnails/{uuid.uuid4().hex}{ext}"


class Texture(models.Model):
    SURFACE_CHOICES = [
        ("floor", "Floor"),
        ("ceiling", "Ceiling"),
        ("wall_front", "Wall Front"),
        ("wall_back", "Wall Back"),
        ("wall_left", "Wall Left"),
        ("wall_right", "Wall Right"),
        ("partition_a", "Custom Wall Side A"),
        ("partition_b", "Custom Wall Side B"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session_key = models.CharField(max_length=64, db_index=True)
    surface = models.CharField(max_length=20, choices=SURFACE_CHOICES)
    image = models.ImageField(upload_to=texture_upload_path)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.expires_at or self.expires_at == timezone.now():
            self.expires_at = timezone.now() + timedelta(hours=5)
        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at

    def delete_file(self):
        try:
            if self.image and os.path.isfile(self.image.path):
                os.remove(self.image.path)
        except (ValueError, NotImplementedError):
            pass

    def __str__(self):
        return f"{self.surface} / {self.session_key[:8]}"


class Asset(models.Model):
    """Catalog item.
    model_file empty + shape set  -> procedural (code-built) model.
    model_file set (.glb)         -> real 3D model, lazy-loaded by frontend.
    """
    CATEGORY_CHOICES = [
        ("furniture", "Furniture"),
        ("ceiling", "Ceiling"),
        ("wall", "Wall"),
        ("windows", "Windows"),
        ("doors", "Doors"),
        ("floor", "Floor"),
        ("decor", "Decor"),
    ]
    SURFACE_CHOICES = [
        ("floor", "Floor"),
        ("ceiling", "Ceiling"),
        ("wall", "Wall"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=120)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    shape = models.CharField(
        max_length=40, blank=True, default="",
        help_text="Procedural builder key (sofa, fridge, niche_wall...). Leave empty if using a GLB file."
    )
    model_file = models.FileField(
        upload_to=asset_model_path, blank=True, null=True,
        help_text="Draco-compressed .glb file"
    )
    thumbnail = models.ImageField(upload_to=asset_thumb_path, blank=True, null=True)
    surface = models.CharField(max_length=10, choices=SURFACE_CHOICES, default="floor")
    default_width = models.FloatField(default=1.0)
    default_height = models.FloatField(default=1.0)
    default_depth = models.FloatField(default=1.0)
    color = models.CharField(max_length=9, blank=True, default="#4f7ec0")
    accent_color = models.CharField(max_length=9, blank=True, default="#e8e2d6")
    emit_light = models.BooleanField(default=False)
    cut_opening = models.BooleanField(default=False)
    is_partition = models.BooleanField(default=False)
    partition_style = models.CharField(max_length=20, blank=True, default="")
    default_v = models.FloatField(null=True, blank=True)
    default_sill = models.FloatField(null=True, blank=True)
    license = models.CharField(max_length=60, blank=True, default="CC0")
    source_url = models.URLField(blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["category", "name"]

    def __str__(self):
        return f"{self.category} / {self.name}"


def purge_expired_textures():
    """Deletes expired Texture rows AND their files from disk."""
    qs = Texture.objects.filter(expires_at__lte=timezone.now())
    count = 0
    for tex in qs:
        tex.delete_file()
        tex.delete()
        count += 1
    return count

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


from django.conf import settings as django_settings
from .models import purge_expired_textures # Ensure this is imported

@api_view(["GET", "POST"])
@permission_classes([AllowAny])
def trigger_cleanup(request):
    """Secure endpoint to manually trigger texture cleanup."""
    # Checks your existing admin key for security
    key = request.headers.get("X-Admin-Key") or request.query_params.get("admin_key") or request.data.get("admin_key")
    if key != django_settings.ADMIN_UPLOAD_KEY:
        return Response({"detail": "Invalid admin key."}, status=status.HTTP_403_FORBIDDEN)
    
    count = purge_expired_textures()
    return Response({"detail": f"Cleanup complete. Deleted {count} expired textures."})