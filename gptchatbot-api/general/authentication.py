from ninja.security import APIKeyHeader
from django.conf import settings


class APIKeyAuth(APIKeyHeader):
    param_name = "X-API-Key"

    def authenticate(self, request, key):
        if not settings.X_API_KEY:
            return None

        if key != settings.X_API_KEY:
            return None

        return key


api_key_auth = APIKeyAuth()