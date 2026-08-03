import re
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models


def validate_isbn_format(value):
    """ISBN must contain 10 or 13 digits (hyphens/spaces allowed as separators,
    trailing 'X' allowed as the ISBN-10 check digit)."""
    stripped = re.sub(r'[\s-]', '', value)
    if not re.fullmatch(r'\d{9}[\dXx]|\d{13}', stripped):
        raise ValidationError(
            '%(value)s no es un ISBN válido: debe tener 10 o 13 dígitos.',
            params={'value': value},
        )


class Book(models.Model):
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    isbn = models.CharField(max_length=20, unique=True, validators=[validate_isbn_format])
    cost_usd = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))]
    )
    selling_price_local = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    stock_quantity = models.IntegerField(validators=[MinValueValidator(0)])
    category = models.CharField(max_length=100, blank=True, default='')
    supplier_country = models.CharField(max_length=2, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f'{self.title} ({self.isbn})'
