from django.conf import settings
from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView


class HasAPIKeyForWrite(BasePermission):
    """Read access (GET/HEAD/OPTIONS) is always allowed.

    Write access (POST/PUT/PATCH/DELETE) requires the "X-API-Key" header to
    match settings.API_KEY — unless API_KEY is left unset, in which case
    write access stays open too (useful while the API is being evaluated).
    """

    message = 'API key inválida o ausente. Incluye el header "X-API-Key".'

    def has_permission(self, request: Request, view: APIView) -> bool:
        if request.method in SAFE_METHODS:
            return True
        if not settings.API_KEY:
            return True
        return request.headers.get('X-API-Key') == settings.API_KEY
