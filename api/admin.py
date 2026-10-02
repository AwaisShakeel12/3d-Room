from django.contrib import admin

from .models import Asset, Texture


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "shape", "has_model", "is_active", "created_at")
    list_filter = ("category", "is_active", "emit_light", "cut_opening", "is_partition")
    search_fields = ("name", "shape")
    fieldsets = (
        ("Basic", {"fields": ("name", "category", "is_active")}),
        (
            "3D source",
            {
                "fields": ("model_file", "thumbnail", "shape"),
                "description": "Upload a Draco .glb OR leave model_file empty and set shape to use a code-built model.",
            },
        ),
        (
            "Placement & size (meters)",
            {
                "fields": (
                    "surface",
                    "default_width",
                    "default_height",
                    "default_depth",
                    "default_v",
                    "default_sill",
                )
            },
        ),
        (
            "Behaviour",
            {"fields": ("emit_light", "cut_opening", "is_partition", "partition_style", "color", "accent_color")},
        ),
        ("Credits", {"fields": ("license", "source_url", "metadata")}),
    )

    @admin.display(boolean=True, description="GLB uploaded")
    def has_model(self, obj):
        return bool(obj.model_file)


@admin.register(Texture)
class TextureAdmin(admin.ModelAdmin):
    list_display = ("surface", "session_key", "created_at", "expires_at")
    list_filter = ("surface",)