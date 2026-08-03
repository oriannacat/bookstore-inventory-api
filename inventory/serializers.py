from rest_framework import serializers

from .models import Book, validate_isbn_format


class BookSerializer(serializers.ModelSerializer):
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

    def validate_isbn(self, value):
        validate_isbn_format(value)
        qs = Book.objects.filter(isbn=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('Ya existe un libro con este ISBN.')
        return value

    def validate_cost_usd(self, value):
        if value <= 0:
            raise serializers.ValidationError('cost_usd debe ser mayor a 0.')
        return value

    def validate_stock_quantity(self, value):
        if value < 0:
            raise serializers.ValidationError('stock_quantity no puede ser negativo.')
        return value
