# apps/common/schema.py
"""
Shared OpenAPI response shapes for drf-spectacular.

These mirror the ad-hoc {"error": "..."} / {"detail": "..."} dicts returned
by various APIView methods across the project (see docs/api.md — "Error
Responses" / "Success messages" conventions).
"""

from drf_spectacular.utils import inline_serializer
from rest_framework import serializers

ErrorResponseSerializer = inline_serializer(
    name="ErrorResponse",
    fields={"error": serializers.CharField()},
)

DetailResponseSerializer = inline_serializer(
    name="DetailResponse",
    fields={"detail": serializers.CharField()},
)
