import uuid
from datetime import timedelta

from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import Asset, Texture, purge_expired_textures
from .serializers import AssetSerializer, TextureSerializer

from .models import Asset, Texture, purge_expired_textures
from .serializers import AssetSerializer, TextureSerializer

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB


# ---------------- Textures (Phase 2, unchanged) ----------------
@api_view(["POST"])
@permission_classes([AllowAny])
@parser_classes([MultiPartParser, FormParser])
def upload_texture(request):
    """Upload one temporary texture image. Fields: image (file), surface, session_key (optional)."""
    purge_expired_textures()

    image = request.data.get("image")
    if image is None:
        return Response(
            {"detail": "No image file provided (form field name must be 'image')."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if getattr(image, "content_type", None) not in ALLOWED_IMAGE_TYPES:
        return Response(
            {"detail": "Unsupported file type. Use JPG, PNG or WEBP."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if image.size > MAX_IMAGE_BYTES:
        return Response(
            {"detail": "Image too large. Maximum size is 5 MB."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    surface = request.data.get("surface") or "wall_front"
    valid = [c[0] for c in Texture.SURFACE_CHOICES]
    if surface not in valid:
        return Response(
            {"detail": f"Invalid surface. Use one of: {valid}"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    session_key = request.data.get("session_key") or uuid.uuid4().hex

    for old in Texture.objects.filter(session_key=session_key, surface=surface):
        old.delete_file()
        old.delete()

    tex = Texture.objects.create(
        session_key=session_key,
        surface=surface,
        image=image,
        expires_at=timezone.now() + timedelta(hours=5),
    )
    data = TextureSerializer(tex, context={"request": request}).data
    return Response(data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([AllowAny])
def list_session_textures(request, session_key):
    qs = Texture.objects.filter(
        session_key=session_key,
        expires_at__gt=timezone.now(),
    )
    data = TextureSerializer(qs, many=True, context={"request": request}).data
    return Response(data)


@api_view(["DELETE"])
@permission_classes([AllowAny])
def delete_session_textures(request, session_key):
    qs = Texture.objects.filter(session_key=session_key)
    count = qs.count()
    for tex in qs:
        tex.delete_file()
        tex.delete()
    return Response({"deleted": count}, status=status.HTTP_200_OK)


# ---------------- Assets catalog (Phase 3) ----------------
@api_view(["GET"])
@permission_classes([AllowAny])
def list_assets(request):
    """Public read-only catalog. Optional ?category=furniture filter."""
    qs = Asset.objects.filter(is_active=True)
    category = request.query_params.get("category")
    if category:
        qs = qs.filter(category=category)
    serializer = AssetSerializer(qs, many=True, context={"request": request})
    return Response(serializer.data)



from django.conf import settings as django_settings

VALID_CATEGORIES = {"furniture", "ceiling", "wall", "windows", "doors", "floor", "decor"}
VALID_SURFACES = {"floor", "ceiling", "wall"}


@api_view(["POST"])
@permission_classes([AllowAny])
@parser_classes([MultiPartParser, FormParser])
def create_asset(request):
    """Key-protected catalog upload used by /admin-upload page."""
    key = request.headers.get("X-Admin-Key") or request.data.get("admin_key")
    if key != django_settings.ADMIN_UPLOAD_KEY:
        return Response({"detail": "Invalid admin key."}, status=status.HTTP_403_FORBIDDEN)

    name = (request.data.get("name") or "").strip()
    category = request.data.get("category") or "furniture"
    if not name:
        return Response({"detail": "Name is required."}, status=status.HTTP_400_BAD_REQUEST)
    if category not in VALID_CATEGORIES:
        return Response({"detail": "Invalid category."}, status=status.HTTP_400_BAD_REQUEST)

    model_file = request.FILES.get("model_file")
    if model_file is not None and not model_file.name.lower().endswith((".glb", ".gltf")):
        return Response({"detail": "Model file must be .glb or .gltf."}, status=status.HTTP_400_BAD_REQUEST)

    surface = request.data.get("surface") or "floor"
    if surface not in VALID_SURFACES:
        surface = "floor"

    def fnum(value, default):
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def optnum(value):
        if value is None or value == "":
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def flag(value):
        return value in ("true", "1", "on", True)

    asset = Asset.objects.create(
        name=name,
        category=category,
        shape=(request.data.get("shape") or "").strip(),
        model_file=model_file,
        thumbnail=request.FILES.get("thumbnail"),
        surface=surface,
        default_width=fnum(request.data.get("default_width"), 1.0),
        default_height=fnum(request.data.get("default_height"), 1.0),
        default_depth=fnum(request.data.get("default_depth"), 1.0),
        color=request.data.get("color") or "#4f7ec0",
        accent_color=request.data.get("accent_color") or "#e8e2d6",
        emit_light=flag(request.data.get("emit_light")),
        cut_opening=flag(request.data.get("cut_opening")),
        is_partition=flag(request.data.get("is_partition")),
        partition_style=request.data.get("partition_style") or "",
        default_v=optnum(request.data.get("default_v")),
        default_sill=optnum(request.data.get("default_sill")),
        license=request.data.get("license") or "CC0",
        source_url=request.data.get("source_url") or "",
    )
    data = AssetSerializer(asset, context={"request": request}).data
    return Response(data, status=status.HTTP_201_CREATED)



@api_view(["GET", "POST"])
@permission_classes([AllowAny])
def trigger_cleanup(request):
    """Secure endpoint to manually trigger texture cleanup."""
    # Checks your existing admin key for security
    key = request.headers.get("X-Admin-Key") or request.query_params.get("admin_key") or request.data.get("admin_key")
    
    if key != django_settings.ADMIN_UPLOAD_KEY:
        return Response({"detail": "Invalid admin key."}, status=status.HTTP_403_FORBIDDEN)
    
    count = purge_expired_textures()
    return Response({"detail": f"Cleanup complete. Deleted {count} expired textures."}, status=status.HTTP_200_OK)