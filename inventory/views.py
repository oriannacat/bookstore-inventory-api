from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Book
from .serializers import BookSerializer
from .services import get_usd_exchange_rate


class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer

    @action(detail=False, methods=['get'], url_path='search')
    def search(self, request):
        category = request.query_params.get('category')
        if not category:
            return Response(
                {'detail': 'El parámetro "category" es requerido.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        books = self.get_queryset().filter(category__iexact=category)
        page = self.paginate_queryset(books)
        serializer = self.get_serializer(page if page is not None else books, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='low-stock')
    def low_stock(self, request):
        threshold_raw = request.query_params.get('threshold', 10)
        try:
            threshold = int(threshold_raw)
        except (TypeError, ValueError):
            return Response(
                {'detail': 'El parámetro "threshold" debe ser un número entero.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        books = self.get_queryset().filter(stock_quantity__lte=threshold)
        page = self.paginate_queryset(books)
        serializer = self.get_serializer(page if page is not None else books, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='calculate-price')
    def calculate_price(self, request, pk=None):
        book = self.get_object()

        exchange_rate, used_fallback = get_usd_exchange_rate(settings.LOCAL_CURRENCY)

        cost_usd = Decimal(str(book.cost_usd))
        rate = Decimal(str(exchange_rate))
        margin = Decimal(str(settings.PROFIT_MARGIN_PERCENTAGE)) / Decimal('100')

        cents = Decimal('0.01')
        cost_local = (cost_usd * rate).quantize(cents, rounding=ROUND_HALF_UP)
        selling_price_local = (cost_local * (Decimal('1') + margin)).quantize(
            cents, rounding=ROUND_HALF_UP
        )

        book.selling_price_local = selling_price_local
        book.save(update_fields=['selling_price_local', 'updated_at'])

        return Response(
            {
                'book_id': book.id,
                'cost_usd': float(cost_usd),
                'exchange_rate': float(rate),
                'cost_local': float(cost_local),
                'margin_percentage': float(settings.PROFIT_MARGIN_PERCENTAGE),
                'selling_price_local': float(selling_price_local),
                'currency': settings.LOCAL_CURRENCY,
                'used_fallback_rate': used_fallback,
                'calculation_timestamp': timezone.now().isoformat(),
            },
            status=status.HTTP_200_OK,
        )
