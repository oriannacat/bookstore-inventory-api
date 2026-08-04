import logging
from decimal import ROUND_HALF_UP, Decimal

import requests
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from .models import Book

logger = logging.getLogger(__name__)

CENTS = Decimal('0.01')


def get_usd_exchange_rate(currency: str | None = None) -> tuple[float, bool]:
    """Fetch the current USD -> currency exchange rate from the external API.

    Results are cached for settings.EXCHANGE_RATE_CACHE_TTL_SECONDS to avoid
    hitting the third-party API on every price calculation.

    Falls back to settings.DEFAULT_EXCHANGE_RATE if the API is unreachable,
    times out, or does not have the requested currency, per the business
    rule "si la API de cambio falla, usar tasa por defecto".

    Returns a tuple (rate: float, used_fallback: bool).
    """
    currency = currency or settings.LOCAL_CURRENCY

    cache_key = f'exchange_rate:USD:{currency}'
    cached_rate = cache.get(cache_key)
    if cached_rate is not None:
        logger.debug('Tasa de cambio USD->%s obtenida de cache: %s', currency, cached_rate)
        return cached_rate, False

    try:
        response = requests.get(settings.EXCHANGE_RATE_API_URL, timeout=5)
        response.raise_for_status()
        data = response.json()
        rate = float(data['rates'][currency])
        cache.set(cache_key, rate, timeout=settings.EXCHANGE_RATE_CACHE_TTL_SECONDS)
        return rate, False
    except (requests.RequestException, KeyError, ValueError, TypeError) as exc:
        logger.warning(
            'Falla al obtener la tasa de cambio USD->%s (%s). Usando tasa por defecto: %s',
            currency,
            exc,
            settings.DEFAULT_EXCHANGE_RATE,
        )
        return settings.DEFAULT_EXCHANGE_RATE, True


def calculate_price_for_book(book: Book) -> dict:
    """Apply the pricing business rule to a book and persist the result:

    1. Take cost_usd
    2. Fetch the current USD -> local currency exchange rate
    3. Apply the configured profit margin
    4. Update selling_price_local
    5. Return the detailed calculation
    """
    exchange_rate, used_fallback = get_usd_exchange_rate(settings.LOCAL_CURRENCY)

    cost_usd = Decimal(str(book.cost_usd))
    rate = Decimal(str(exchange_rate))
    margin = Decimal(str(settings.PROFIT_MARGIN_PERCENTAGE)) / Decimal('100')

    cost_local = (cost_usd * rate).quantize(CENTS, rounding=ROUND_HALF_UP)
    selling_price_local = (cost_local * (Decimal('1') + margin)).quantize(
        CENTS, rounding=ROUND_HALF_UP
    )

    book.selling_price_local = selling_price_local
    book.save(update_fields=['selling_price_local', 'updated_at'])

    logger.info(
        'Precio calculado para book_id=%s: cost_usd=%s rate=%s -> selling_price_local=%s %s '
        '(fallback=%s)',
        book.id,
        cost_usd,
        rate,
        selling_price_local,
        settings.LOCAL_CURRENCY,
        used_fallback,
    )

    return {
        'book_id': book.id,
        'cost_usd': cost_usd,
        'exchange_rate': rate,
        'cost_local': cost_local,
        'margin_percentage': Decimal(str(settings.PROFIT_MARGIN_PERCENTAGE)),
        'selling_price_local': selling_price_local,
        'currency': settings.LOCAL_CURRENCY,
        'used_fallback_rate': used_fallback,
        'calculation_timestamp': timezone.now(),
    }
