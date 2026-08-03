import requests
from django.conf import settings


def get_usd_exchange_rate(currency=None):
    """Fetch the current USD -> currency exchange rate from the external API.

    Falls back to settings.DEFAULT_EXCHANGE_RATE if the API is unreachable,
    times out, or does not have the requested currency, per the business
    rule "si la API de cambio falla, usar tasa por defecto".

    Returns a tuple (rate: float, used_fallback: bool).
    """
    currency = currency or settings.LOCAL_CURRENCY

    try:
        response = requests.get(settings.EXCHANGE_RATE_API_URL, timeout=5)
        response.raise_for_status()
        data = response.json()
        rate = data['rates'][currency]
        return float(rate), False
    except (requests.RequestException, KeyError, ValueError, TypeError):
        return settings.DEFAULT_EXCHANGE_RATE, True
