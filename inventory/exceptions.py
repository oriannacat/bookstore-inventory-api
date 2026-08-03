from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler


class ExchangeRateServiceError(Exception):
    """Raised when the external exchange-rate API cannot be reached and no
    fallback could be applied."""


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        return response

    if isinstance(exc, ExchangeRateServiceError):
        return Response(
            {'detail': str(exc) or 'Servicio de tasas de cambio no disponible.'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    return Response(
        {'detail': 'Error interno del servidor.'},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
