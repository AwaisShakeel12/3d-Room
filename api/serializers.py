from rest_framework import serializers

from .models import Asset, Texture


class TextureSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    is_expired = serializers.BooleanField(read_only=True)

    class Meta:
        model = Texture
        fields = [
            "id",
            "session_key",
            "surface",
            "url",
            "created_at",
            "expires_at",
            "is_expired",
        ]
        read_only_fields = fields

    def get_url(self, obj):
        request = self.context.get("request")
        if request is not None:
            return request.build_absolute_uri(obj.image.url)
        return obj.image.url


class AssetSerializer(serializers.ModelSerializer):
    model_url = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()
    accentColor = serializers.CharField(source="accent_color", read_only=True)
    emitLight = serializers.BooleanField(source="emit_light", read_only=True)
    cutOpening = serializers.BooleanField(source="cut_opening", read_only=True)
    isPartition = serializers.BooleanField(source="is_partition", read_only=True)
    partitionStyle = serializers.CharField(source="partition_style", read_only=True)
    defaultV = serializers.FloatField(source="default_v", read_only=True)
    defaultSill = serializers.FloatField(source="default_sill", read_only=True)

    class Meta:
        model = Asset
        fields = [
            "id",
            "name",
            "category",
            "shape",
            "model_url",
            "thumbnail_url",
            "surface",
            "default_width",
            "default_height",
            "default_depth",
            "color",
            "accentColor",
            "emitLight",
            "cutOpening",
            "isPartition",
            "partitionStyle",
            "defaultV",
            "defaultSill",
            "license",
            "source_url",
            "metadata",
        ]

    def get_model_url(self, obj):
        if not obj.model_file:
            return None
        request = self.context.get("request")
        url = obj.model_file.url
        return request.build_absolute_uri(url) if request else url

    def get_thumbnail_url(self, obj):
        if not obj.thumbnail:
            return None
        request = self.context.get("request")
        url = obj.thumbnail.url
        return request.build_absolute_uri(url) if request else url