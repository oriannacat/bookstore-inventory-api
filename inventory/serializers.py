from decimal import Decimal

from rest_framework import serializers

from .models import Book, validate_isbn_format


class BookSerializer(serializers.ModelSerializer):
    # Rendered as a JSON number (not a string) to match the API spec, e.g.
    # {"cost_usd": 15.99} instead of DRF's DecimalField default {"cost_usd": "15.99"}.
    cost_usd = serializers.DecimalField(max_digits=10, decimal_places=2, coerce_to_string=False)
    selling_price_local = serializers.DecimalField(
        max_digits=10, decimal_places=2, coerce_to_string=False, read_only=True
    )
    # Declared explicitly so DRF doesn't auto-attach its own UniqueValidator
    # (from the model's unique=True) with its English, harder-to-customize
    # message. Duplicate detection is handled entirely by validate_isbn() below.
    isbn = serializers.CharField(max_length=20)

    class Meta:
        model = Book
        fields = [
            'id',
            'title',
            'author',
            'isbn',
            'cost_usd',
            'selling_price_local',
            'stock_quantity',
            'category',
            'supplier_country',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'selling_price_local', 'created_at', 'updated_at']

    def validate_isbn(self, value: str) -> str:
        validate_isbn_format(value)
        qs = Book.objects.filter(isbn=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('Ya existe un libro con este ISBN.')
        return value

    def validate_cost_usd(self, value: Decimal) -> Decimal:
        if value <= 0:
            raise serializers.ValidationError('cost_usd debe ser mayor a 0.')
        return value

    def validate_stock_quantity(self, value: int) -> int:
        if value < 0:
            raise serializers.ValidationError('stock_quantity no puede ser negativo.')
        return value
