from decimal import Decimal
from unittest.mock import patch

import requests
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Book, validate_isbn_format

VALID_PAYLOAD = {
    'title': 'El Quijote',
    'author': 'Miguel de Cervantes',
    'isbn': '978-84-376-0494-7',
    'cost_usd': 15.99,
    'stock_quantity': 25,
    'category': 'Literatura Clasica',
    'supplier_country': 'ES',
}


class IsbnValidatorTests(TestCase):
    def test_accepts_13_digit_isbn_with_hyphens(self):
        validate_isbn_format('978-84-376-0494-7')

    def test_accepts_10_digit_isbn(self):
        validate_isbn_format('0306406152')

    def test_accepts_10_digit_isbn_with_x_check_digit(self):
        validate_isbn_format('080442957X')

    def test_rejects_wrong_length(self):
        with self.assertRaises(ValidationError):
            validate_isbn_format('12345')

    def test_rejects_non_numeric(self):
        with self.assertRaises(ValidationError):
            validate_isbn_format('abcdefghij')


class BookModelTests(TestCase):
    def test_cost_usd_must_be_positive(self):
        book = Book(
            title='X', author='Y', isbn='978-84-376-0494-7', cost_usd=Decimal('0'),
            stock_quantity=1,
        )
        with self.assertRaises(ValidationError):
            book.full_clean()

    def test_stock_quantity_cannot_be_negative(self):
        book = Book(
            title='X', author='Y', isbn='978-84-376-0494-7', cost_usd=Decimal('5'),
            stock_quantity=-1,
        )
        with self.assertRaises(ValidationError):
            book.full_clean()

    def test_duplicate_isbn_rejected_at_db_level(self):
        Book.objects.create(
            title='X', author='Y', isbn='978-84-376-0494-7', cost_usd=Decimal('5'),
            stock_quantity=1,
        )
        with self.assertRaises(Exception):
            Book.objects.create(
                title='Z', author='W', isbn='978-84-376-0494-7', cost_usd=Decimal('7'),
                stock_quantity=2,
            )


class BookCrudApiTests(APITestCase):
    def setUp(self):
        self.book = Book.objects.create(
            title='El Quijote', author='Miguel de Cervantes', isbn='978-84-376-0494-7',
            cost_usd=Decimal('15.99'), stock_quantity=25, category='Literatura Clasica',
            supplier_country='ES',
        )

    def test_create_book_returns_numeric_cost(self):
        # Checked against the rendered JSON (not response.data, which still holds
        # DRF's internal Decimal representation pre-render) to prove the wire
        # format matches the spec: {"cost_usd": 15.99}, not {"cost_usd": "15.99"}.
        payload = dict(VALID_PAYLOAD, isbn='84-376-0495-5')
        response = self.client.post('/books/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        body = response.json()
        self.assertIsInstance(body['cost_usd'], float)
        self.assertEqual(body['cost_usd'], 15.99)
        self.assertIsNone(body['selling_price_local'])

    def test_create_book_duplicate_isbn_rejected(self):
        response = self.client.post('/books/', VALID_PAYLOAD, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('isbn', response.data)

    def test_create_book_invalid_cost_rejected(self):
        payload = dict(VALID_PAYLOAD, isbn='84-376-0495-5', cost_usd=-5)
        response = self.client.post('/books/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_book_invalid_isbn_rejected(self):
        payload = dict(VALID_PAYLOAD, isbn='12345')
        response = self.client.post('/books/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_books_is_paginated(self):
        response = self.client.get('/books/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('count', response.data)
        self.assertIn('results', response.data)

    def test_retrieve_book(self):
        response = self.client.get(f'/books/{self.book.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['isbn'], self.book.isbn)

    def test_retrieve_missing_book_404(self):
        response = self.client.get('/books/999999/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_put_replaces_book(self):
        payload = dict(VALID_PAYLOAD, isbn=self.book.isbn, stock_quantity=30, cost_usd=17.5)
        response = self.client.put(f'/books/{self.book.id}/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['stock_quantity'], 30)

    def test_patch_partial_update(self):
        response = self.client.patch(
            f'/books/{self.book.id}/', {'stock_quantity': 5}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['stock_quantity'], 5)
        self.assertEqual(response.data['title'], self.book.title)

    def test_delete_book(self):
        response = self.client.delete(f'/books/{self.book.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Book.objects.filter(id=self.book.id).exists())

    def test_delete_missing_book_404(self):
        response = self.client.delete('/books/999999/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class SearchAndLowStockApiTests(APITestCase):
    def setUp(self):
        Book.objects.create(
            title='A', author='A', isbn='978-84-376-0494-7', cost_usd=Decimal('5'),
            stock_quantity=2, category='Literatura Clasica',
        )
        Book.objects.create(
            title='B', author='B', isbn='0306406152', cost_usd=Decimal('5'),
            stock_quantity=50, category='Ciencia Ficcion',
        )

    def test_search_by_category(self):
        response = self.client.get('/books/search/', {'category': 'literatura clasica'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)

    def test_search_requires_category_param(self):
        response = self.client.get('/books/search/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_low_stock_default_threshold(self):
        response = self.client.get('/books/low-stock/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)

    def test_low_stock_invalid_threshold(self):
        response = self.client.get('/books/low-stock/', {'threshold': 'abc'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class CalculatePriceApiTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.book = Book.objects.create(
            title='El Quijote', author='Miguel de Cervantes', isbn='978-84-376-0494-7',
            cost_usd=Decimal('15.99'), stock_quantity=25,
        )

    def tearDown(self):
        cache.clear()

    @patch('inventory.services.requests.get')
    def test_calculate_price_success(self, mock_get):
        mock_get.return_value.json.return_value = {'rates': {'EUR': 0.85}}
        mock_get.return_value.raise_for_status.return_value = None

        response = self.client.post(f'/books/{self.book.id}/calculate-price/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        body = response.json()
        self.assertEqual(body['exchange_rate'], 0.85)
        self.assertEqual(body['margin_percentage'], 40.0)
        self.assertFalse(body['used_fallback_rate'])
        # cost_local = 15.99 * 0.85 = 13.59 ; selling = 13.59 * 1.4 = 19.03
        self.assertEqual(body['cost_local'], 13.59)
        self.assertEqual(body['selling_price_local'], 19.03)

        self.book.refresh_from_db()
        self.assertEqual(self.book.selling_price_local, Decimal('19.03'))

    @patch('inventory.services.requests.get', side_effect=requests.RequestException('down'))
    def test_calculate_price_falls_back_when_api_fails(self, mock_get):
        response = self.client.post(f'/books/{self.book.id}/calculate-price/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        body = response.json()
        self.assertTrue(body['used_fallback_rate'])
        from django.conf import settings
        self.assertEqual(body['exchange_rate'], settings.DEFAULT_EXCHANGE_RATE)

    def test_calculate_price_missing_book_404(self):
        response = self.client.post('/books/999999/calculate-price/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch('inventory.services.requests.get')
    def test_exchange_rate_is_cached(self, mock_get):
        mock_get.return_value.json.return_value = {'rates': {'EUR': 0.9}}
        mock_get.return_value.raise_for_status.return_value = None

        self.client.post(f'/books/{self.book.id}/calculate-price/')
        self.client.post(f'/books/{self.book.id}/calculate-price/')

        self.assertEqual(mock_get.call_count, 1)


@override_settings(API_KEY='secret-test-key')
class ApiKeyPermissionTests(APITestCase):
    def setUp(self):
        self.book = Book.objects.create(
            title='El Quijote', author='Miguel de Cervantes', isbn='978-84-376-0494-7',
            cost_usd=Decimal('15.99'), stock_quantity=25,
        )

    def test_write_blocked_without_key(self):
        response = self.client.patch(
            f'/books/{self.book.id}/', {'stock_quantity': 1}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_write_allowed_with_correct_key(self):
        response = self.client.patch(
            f'/books/{self.book.id}/', {'stock_quantity': 1}, format='json',
            headers={'X-API-Key': 'secret-test-key'},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_read_allowed_without_key(self):
        response = self.client.get('/books/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
