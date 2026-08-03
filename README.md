# Bookstore Inventory API

API REST para la gestión de inventario de una cadena de librerías, con
validación de precios en tiempo real contra tasas de cambio (USD → moneda
local) y cálculo automático del precio de venta sugerido.

Construida con **Django 6** + **Django REST Framework**.

## Requisitos previos

- Python 3.12+ (o Docker, ver más abajo)
- pip
- (Opcional) Docker y Docker Compose para levantar el proyecto con Postgres

## Instalación y ejecución local (sin Docker)

```bash
git clone <URL_DEL_REPOSITORIO>
cd bookstore-inventory-api

python -m venv venv
source venv/bin/activate        # En Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env            # Ajusta valores si lo necesitas

python manage.py migrate
python manage.py runserver
```

Por defecto, sin `DATABASE_URL` configurada, el proyecto usa **SQLite**
(`db.sqlite3`) para desarrollo local. La API queda disponible en
`http://127.0.0.1:8000/`.

Para crear un superusuario y acceder al panel de administración
(`/admin/`):

```bash
python manage.py createsuperuser
```

## Ejecución con Docker

Este modo levanta la API junto con una base de datos **PostgreSQL** en un
contenedor, replicando el entorno de producción.

```bash
cp .env.example .env
docker compose up --build
```

La API queda disponible en `http://localhost:8000/`. Las migraciones se
aplican automáticamente al iniciar el contenedor `web`.

## Variables de entorno

| Variable                    | Descripción                                                              | Default                                          |
|------------------------------|---------------------------------------------------------------------------|---------------------------------------------------|
| `SECRET_KEY`                | Clave secreta de Django                                                  | valor de desarrollo (cambiar en producción)       |
| `DEBUG`                     | Modo debug                                                               | `True`                                            |
| `ALLOWED_HOSTS`              | Hosts permitidos, separados por coma                                    | `*`                                               |
| `DATABASE_URL`               | Cadena de conexión a Postgres. Vacía = usa SQLite                       | (vacío)                                           |
| `EXCHANGE_RATE_API_URL`      | Endpoint de la API de tasas de cambio                                   | `https://api.exchangerate-api.com/v4/latest/USD`  |
| `LOCAL_CURRENCY`             | Moneda local objetivo para el cálculo de precios                        | `EUR`                                             |
| `DEFAULT_EXCHANGE_RATE`      | Tasa de cambio de respaldo si la API externa falla                      | `0.85`                                            |
| `PROFIT_MARGIN_PERCENTAGE`   | Margen de ganancia aplicado sobre el costo en moneda local               | `40`                                              |

## Modelo de datos: `Book`

```json
{
  "id": 1,
  "title": "El Quijote",
  "author": "Miguel de Cervantes",
  "isbn": "978-84-376-0494-7",
  "cost_usd": 15.99,
  "selling_price_local": null,
  "stock_quantity": 25,
  "category": "Literatura Clásica",
  "supplier_country": "ES",
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T10:30:00Z"
}
```

### Reglas de negocio

- `cost_usd` debe ser mayor a 0.
- `stock_quantity` no puede ser negativo.
- `isbn` debe tener 10 o 13 dígitos (se aceptan guiones como separadores).
- No se permiten libros duplicados con el mismo ISBN.
- Si la API externa de tasas de cambio falla, se usa `DEFAULT_EXCHANGE_RATE`
  como respaldo (esto se indica en la respuesta con `used_fallback_rate: true`).
- Errores manejados: `400` (validación), `404` (no encontrado), `500`
  (error interno), `503` (servicio externo no disponible sin respaldo
  configurado).

## Endpoints

Todas las rutas viven bajo la raíz del proyecto. El router de DRF exige
slash final (`/`) en cada ruta.

### CRUD de libros

| Método | Ruta               | Descripción                          |
|--------|---------------------|---------------------------------------|
| POST   | `/books/`            | Crear libro                           |
| GET    | `/books/`            | Listar libros (paginado, 10 por pág.) |
| GET    | `/books/{id}/`       | Obtener libro por ID                  |
| PUT    | `/books/{id}/`       | Actualizar libro                      |
| DELETE | `/books/{id}/`       | Eliminar libro                        |

**Ejemplo — crear libro:**

```bash
curl -X POST http://127.0.0.1:8000/books/ \
  -H "Content-Type: application/json" \
  -d '{
    "title": "El Quijote",
    "author": "Miguel de Cervantes",
    "isbn": "978-84-376-0494-7",
    "cost_usd": 15.99,
    "stock_quantity": 25,
    "category": "Literatura Clásica",
    "supplier_country": "ES"
  }'
```

### Búsqueda y filtros

| Método | Ruta                                       | Descripción                    |
|--------|----------------------------------------------|----------------------------------|
| GET    | `/books/search/?category={category}`        | Buscar libros por categoría      |
| GET    | `/books/low-stock/?threshold=10`             | Libros con stock igual o menor al umbral |

```bash
curl "http://127.0.0.1:8000/books/search/?category=Literatura%20Cl%C3%A1sica"
curl "http://127.0.0.1:8000/books/low-stock/?threshold=10"
```

### Cálculo de precio (integración externa)

| Método | Ruta                              | Descripción                        |
|--------|-------------------------------------|--------------------------------------|
| POST   | `/books/{id}/calculate-price/`      | Calcula y guarda el precio de venta  |

```bash
curl -X POST http://127.0.0.1:8000/books/1/calculate-price/
```

Respuesta:

```json
{
  "book_id": 1,
  "cost_usd": 15.99,
  "exchange_rate": 0.867,
  "cost_local": 13.86,
  "margin_percentage": 40.0,
  "selling_price_local": 19.4,
  "currency": "EUR",
  "used_fallback_rate": false,
  "calculation_timestamp": "2026-08-03T23:41:57.998913+00:00"
}
```

## Colección de Postman

En `postman/bookstore-inventory-api.postman_collection.json` se incluye la
colección con todos los endpoints, y en
`postman/environment.postman_environment.json` un entorno con la variable
`base_url` (por defecto apuntando a la API desplegada en producción).

## Despliegue

La API se encuentra desplegada en: `<URL_DE_PRODUCCION>`

Base de datos: PostgreSQL gestionado (no SQLite) en el mismo proveedor de
despliegue.

## Estructura del proyecto

```
bookstore-inventory-api/
├── config/            # Configuración del proyecto Django (settings, urls, wsgi)
├── inventory/         # App principal: modelo Book, serializers, views, servicios
├── postman/           # Colección y entorno de Postman
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```
