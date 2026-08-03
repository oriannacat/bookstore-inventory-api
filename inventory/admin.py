from django.contrib import admin

from .models import Book


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'author', 'isbn', 'cost_usd', 'selling_price_local', 'stock_quantity', 'category')
    search_fields = ('title', 'author', 'isbn')
    list_filter = ('category', 'supplier_country')
