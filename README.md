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

Sin Docker, el proyecto corre con `config.settings.development` (definido por
defecto en `manage.py`): usa **SQLite** (`db.sqlite3`) si no defines
`DATABASE_URL`, `DEBUG=True`, CORS abierto y logging detallado. La API queda
disponible en `http://127.0.0.1:8000/`.

Para crear un superusuario y acceder al panel de administración (`/admin/`):

```bash
python manage.py createsuperuser
```

### Correr los tests

```bash
python manage.py test inventory
```

Incluye 30 tests: validaciones del modelo (ISBN, costo, stock, duplicados),
CRUD completo, búsqueda/low-stock, cálculo de precio (con mock de la API
externa y su fallback), cacheo de la tasa de cambio, y el permiso opcional de
API key.

## Ejecución con Docker

Este modo levanta la API junto con una base de datos **PostgreSQL** en un
contenedor, usando `config.settings.production` (con `DEBUG=False` y las
validaciones estrictas de esas settings, pero con SSL/HTTPS desactivado ya
que es HTTP local — ver `docker-compose.yml`).

```bash
cp .env.example .env
docker compose up --build
```

La API queda disponible en `http://localhost:8000/`. Las migraciones se
aplican automáticamente al iniciar el contenedor `web`.

## Variables de entorno

| Variable                        | Descripción                                                                                     | Default                                          |
|-----------------------------------|----------------------------------------------------------------------------------------------------|-----------------------------------------------------|
| `DJANGO_SETTINGS_MODULE`         | `config.settings.development` o `config.settings.production`                                      | `config.settings.development` (dev) / `...production` (Docker/gunicorn) |
| `SECRET_KEY`                     | Clave secreta de Django. **Obligatoria** en `production` (falla el arranque si falta)              | valor de desarrollo solo en `development`          |
| `ALLOWED_HOSTS`                  | Hosts permitidos, separados por coma. **Obligatoria** en `production`                              | `*`                                                 |
| `DATABASE_URL`                   | Cadena de conexión a Postgres. **Obligatoria** en `production` (no se acepta SQLite ahí)           | (vacío = SQLite, solo en `development`)             |
| `DB_SSL_REQUIRE`                 | Exigir SSL en la conexión a Postgres (solo `production`)                                           | `True`                                              |
| `SECURE_SSL_REDIRECT`            | Forzar redirección a HTTPS (solo `production`)                                                     | `True`                                              |
| `CORS_ALLOWED_ORIGINS`           | Orígenes permitidos, separados por coma (solo `production`; en `development` CORS está abierto)    | (vacío)                                             |
| `API_KEY`                        | Si se define, protege POST/PUT/PATCH/DELETE de `/books/` exigiendo el header `X-API-Key`           | (vacío = escritura abierta)                         |
| `EXCHANGE_RATE_API_URL`          | Endpoint de la API de tasas de cambio                                                              | `https://api.exchangerate-api.com/v4/latest/USD`    |
| `LOCAL_CURRENCY`                 | Moneda local objetivo para el cálculo de precios                                                   | `EUR`                                               |
| `DEFAULT_EXCHANGE_RATE`          | Tasa de cambio de respaldo si la API externa falla                                                 | `0.85`                                              |
| `PROFIT_MARGIN_PERCENTAGE`       | Margen de ganancia aplicado sobre el costo en moneda local                                         | `40`                                                |
| `EXCHANGE_RATE_CACHE_TTL_SECONDS`| Segundos que se cachea la tasa de cambio obtenida, para no golpear la API externa en cada request   | `300`                                               |

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

`cost_usd` y `selling_price_local` se serializan como **número JSON** (no
string), y `category`/`stock_quantity` están indexados en base de datos para
que `search` y `low-stock` escalen bien con más volumen de datos.

### Reglas de negocio

- `cost_usd` debe ser mayor a 0.
- `stock_quantity` no puede ser negativo.
- `isbn` debe tener 10 o 13 dígitos (se aceptan guiones como separadores).
- No se permiten libros duplicados con el mismo ISBN.
- Si la API externa de tasas de cambio falla, se usa `DEFAULT_EXCHANGE_RATE`
  como respaldo (esto se indica en la respuesta con `used_fallback_rate: true`
  y queda registrado en el log).
- La tasa de cambio obtenida se cachea por `EXCHANGE_RATE_CACHE_TTL_SECONDS`
  para no depender de la API externa en cada cálculo.
- Errores manejados: `400` (validación), `403` (falta o es inválida la API
  key, si está configurada), `404` (no encontrado), `500` (error interno),
  `503` (servicio externo no disponible).

## Autenticación (opcional)

Por defecto la API es completamente abierta. Si defines `API_KEY` en el
entorno, las operaciones de escritura (`POST`, `PUT`, `PATCH`, `DELETE` sobre
`/books/`, incluyendo `calculate-price`) exigen el header:

```
X-API-Key: <tu-api-key>
```

La lectura (`GET`) siempre es pública. Esto queda deshabilitado por defecto
para no romper la evaluación con Postman.

## Endpoints

Todas las rutas viven bajo la raíz del proyecto. El router de DRF exige
slash final (`/`) en cada ruta.

### CRUD de libros

| Método | Ruta               | Descripción                                     |
|--------|---------------------|----------------------------------------------------|
| POST   | `/books/`            | Crear libro                                        |
| GET    | `/books/`            | Listar libros (paginado, 10 por pág.)              |
| GET    | `/books/{id}/`       | Obtener libro por ID                               |
| PUT    | `/books/{id}/`       | Actualizar libro (reemplazo completo)              |
| PATCH  | `/books/{id}/`       | Actualizar libro (parcial, solo los campos enviados) |
| DELETE | `/books/{id}/`       | Eliminar libro                                     |

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

**Ejemplo — actualización parcial:**

```bash
curl -X PATCH http://127.0.0.1:8000/books/1/ \
  -H "Content-Type: application/json" \
  -d '{"stock_quantity": 40}'
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
  "calculation_timestamp": "2026-08-03T23:41:57.998913Z"
}
```

### Utilidades

| Método | Ruta        | Descripción                                         |
|--------|--------------|--------------------------------------------------------|
| GET    | `/health/`   | Healthcheck (usado por Render para verificar el servicio) |
| GET    | `/docs/`     | Documentación interactiva Swagger UI                    |
| GET    | `/schema/`   | Esquema OpenAPI en formato YAML                          |

## Colección de Postman

En `postman/bookstore-inventory-api.postman_collection.json` se incluye la
colección con todos los endpoints (incluyendo `PATCH`), y en
`postman/environment.postman_environment.json` un entorno con la variable
`base_url` (apuntando a la API desplegada en producción) y `api_key`
(opcional, solo si el despliegue tiene `API_KEY` configurada).

## Despliegue

La API se encuentra desplegada en: `<URL_DE_PRODUCCION>`

Base de datos: PostgreSQL gestionado (no SQLite) en el mismo proveedor de
despliegue (Render).

## Decisiones de diseño

- **Sin versionado de URL (`/api/v1/...`)**: las rutas se mantienen exactamente
  como las pide el enunciado (`/books/`, etc.) para no romper el contrato
  esperado por el equipo evaluador.
- **Settings separadas por entorno** (`config/settings/{base,development,production}.py`):
  `development` prioriza conveniencia (SQLite, CORS abierto, `SECRET_KEY` con
  fallback); `production` falla rápido si falta `SECRET_KEY`, `ALLOWED_HOSTS`
  o `DATABASE_URL`, y fuerza HTTPS.
- **`LOCAL_CURRENCY=EUR` por defecto**: el enunciado no especifica en qué país
  opera la cadena de librerías ni qué moneda local usa; se eligió `EUR` porque
  es la moneda del ejemplo de respuesta del propio PDF de la prueba
  (`"currency": "EUR"`, consistente con `"supplier_country": "ES"` en su
  libro de ejemplo). Es 100% configurable vía la variable de entorno
  `LOCAL_CURRENCY` sin tocar código — por ejemplo, a `VES` para el mercado
  venezolano.
- **API key opt-in** en vez de autenticación obligatoria, para no romper la
  evaluación si no se configura.

## Estructura del proyecto

```
bookstore-inventory-api/
├── config/
│   ├── settings/          # base.py, development.py, production.py
│   ├── urls.py, views.py  # healthcheck, swagger/schema
├── inventory/              # modelo Book, serializers, views, filters,
│                            # permissions, services (negocio + integracion
│                            # externa), exceptions, tests
├── postman/                 # coleccion y entorno de Postman
├── .github/workflows/ci.yml # tests automaticos en cada push
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```
