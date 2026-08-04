import django_filters

from .models import Book


class BookFilter(django_filters.FilterSet):
    category = django_filters.CharFilter(field_name='category', lookup_expr='iexact')
    threshold = django_filters.NumberFilter(field_name='stock_quantity', lookup_expr='lte')

    class Meta:
        model = Book
        fields: list[str] = []
