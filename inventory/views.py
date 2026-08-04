import logging

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from .filters import BookFilter
from .models import Book
from .permissions import HasAPIKeyForWrite
from .serializers import BookSerializer
from .services import calculate_price_for_book

logger = logging.getLogger(__name__)


class BookViewSet(viewsets.ModelViewSet):
    """CRUD for Book, plus category search, low-stock lookup and price calculation.

    Read access (list/retrieve/search/low-stock) is always open. Write access
    (create/update/partial_update/destroy/calculate_price) is gated by
    HasAPIKeyForWrite, which only enforces a key when settings.API_KEY is set.
    """

    queryset = Book.objects.all()
    serializer_class = BookSerializer
    permission_classes = [HasAPIKeyForWrite]

    def _paginated_response(self, request: Request, queryset) -> Response:
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page if page is not None else queryset, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='search')
    def search(self, request: Request) -> Response:
        category = request.query_params.get('category')
        if not category:
            return Response(
                {'detail': 'El parámetro "category" es requerido.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        books = BookFilter({'category': category}, queryset=self.get_queryset()).qs
        return self._paginated_response(request, books)

    @action(detail=False, methods=['get'], url_path='low-stock')
    def low_stock(self, request: Request) -> Response:
        threshold_raw = request.query_params.get('threshold', 10)
        try:
            threshold = int(threshold_raw)
        except (TypeError, ValueError):
            return Response(
                {'detail': 'El parámetro "threshold" debe ser un número entero.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        books = BookFilter({'threshold': threshold}, queryset=self.get_queryset()).qs
        return self._paginated_response(request, books)

    @action(detail=True, methods=['post'], url_path='calculate-price')
    def calculate_price(self, request: Request, pk: str | None = None) -> Response:
        book = self.get_object()
        result = calculate_price_for_book(book)
        return Response(result, status=status.HTTP_200_OK)
