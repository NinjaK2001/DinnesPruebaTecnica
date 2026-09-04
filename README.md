# Sistema de pedidos e inventario

Prueba técnica de una API REST con NestJS, PostgreSQL y un pipeline ETL en Python.

## Tecnologías utilizadas

- NestJS y TypeScript para la API REST.
- PostgreSQL como base de datos relacional.
- TypeORM y migraciones para versionar el esquema.
- JWT y Passport para autenticación.
- Python y pandas para el pipeline ETL.
- Excel/CSV como fuentes externas de datos.
- Docker Compose para levantar el entorno local.

La selección sigue las tecnologías sugeridas en el enunciado y permite trabajar el proyecto con una separación clara entre API, base de datos e integración de datos.

## Arquitectura

- `Backend/`: API NestJS, autenticación JWT, reglas de negocio y migraciones TypeORM.
- `Etl/`: lectura, normalización, validación y sincronización de archivos Excel/CSV.
- `docker-compose.yml`: PostgreSQL 16 para desarrollo local.
- `Etl/data/`: datasets de entrada proporcionados para la prueba.

El sistema usa las tablas `products`, `orders` y `order_items`. La API y el ETL escriben en la misma base, de modo que el reporte SQL consulta datos provenientes de ambas fuentes.

El proyecto se mantuvo separado en dos partes para facilitar su ejecución y revisión: el backend concentra las reglas transaccionales de pedidos e inventario, mientras que el ETL se encarga de adaptar los formatos externos antes de sincronizarlos.

## Requisitos

- Docker Desktop
- Node.js 20 o superior
- Python 3.11 o superior
- PostgreSQL no es necesario instalarlo localmente

## Configuración

Copiar el archivo de variables de entorno:

```powershell
Copy-Item .env.example .env
```

Revisar los valores de `.env`. El archivo `.env` no debe subirse al repositorio.

La migración [SeedAdminUser1790000000000.ts](Backend/src/database/migrations/1790000000000-SeedAdminUser.ts) crea un usuario `admin` de prueba. Su contraseña se guarda como hash bcrypt y está pensada solo para validar el login JWT en este entorno.

## Levantar la base y la API

Desde la raíz del proyecto:

```powershell
docker compose up --build
```

La API queda disponible en `http://localhost:3000`.

Compose espera a que PostgreSQL esté saludable, ejecuta las migraciones y luego inicia la API. En ejecuciones posteriores puede usarse `docker compose up` sin `--build` si no cambió el código.

Para desarrollo sin Docker de la API:

```powershell
cd Backend
npm install
npm run migration:run
npm run start:dev
```

## API

### Login

```http
POST /auth/login
Content-Type: application/json
```

```json
{
  "username": "admin",
  "password": "<password>"
}
```

Usar el token devuelto como:

```http
Authorization: Bearer <token>
```

### Productos

Todas las rutas requieren JWT:

```text
POST   /products
GET    /products
GET    /products/:id
PATCH  /products/:id
DELETE /products/:id
```

La creación y actualización validan nombre, SKU, stock y precio. El SKU es único en PostgreSQL.

### Pedidos

```http
POST /orders
Authorization: Bearer <token>
Content-Type: application/json
```

```json
{
  "customer": "Cliente de prueba",
  "items": [
    { "productId": 1, "quantity": 2 }
  ]
}
```

La operación se ejecuta en una transacción. Se bloquean los productos al descontar stock; si un producto no existe o no tiene stock suficiente, se revierte el pedido completo.

## ETL

Crear el entorno e instalar dependencias:

```powershell
cd Etl
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Ejecutar una validación sin modificar PostgreSQL:

```powershell
python etl.py --input-dir data --output-dir output --dry-run
```

Procesar un archivo específico:

```powershell
python etl.py --input data\01_catalogo_productos_2026.xlsx --dry-run
```

Sincronizar productos, pedidos y detalles:

```powershell
python etl.py --input-dir data --output-dir output --sync
```

El ETL genera:

- `normalized_products.csv`
- `normalized_orders.csv`
- `normalized_order_items.csv`
- `normalized_customers.csv`
- `normalized_movements.csv`
- `rejected_records.csv`
- `quality_report.json`

Las reglas principales son:

- Campos obligatorios faltantes: registro rechazado.
- Stock vacío de productos: se interpreta como `0`.
- Fechas, importes, porcentajes, SKU y estados se normalizan.
- Productos se deduplican por `sku`.
- Pedidos se deduplican por `external_order_number`.
- Detalles se consolidan por `(pedido, sku)`.
- Los `upsert` permiten ejecutar el proceso varias veces sin duplicar datos.

## KPI

El reporte se calcula en PostgreSQL mediante una función almacenada y se expone por la API:

```http
GET /orders/reports/top-products?from=2026-01-01&to=2026-12-31
Authorization: Bearer <token>
```

Devuelve los cinco productos con más unidades vendidas, el monto vendido y el stock actual. Excluye pedidos anulados o cancelados. El endpoint solo valida parámetros y ejecuta la función SQL; la agregación ocurre en PostgreSQL.

## Pruebas y validación

```powershell
cd Backend
npm run build
npm run test
npm run test:e2e
```

La función SQL también puede probarse directamente:

```powershell
docker exec dinnes-postgres psql -U dinnes -d dinnes -c "SELECT * FROM top_selling_products('2026-01-01', '2026-12-31', 5);"
```

## Decisiones y mejoras futuras

- Se eligió NestJS por su separación modular y TypeScript.
- Se eligió Python/pandas para tolerar Excel/CSV con encabezados variables y formatos sucios.
- Se usan migraciones y restricciones únicas para proteger la integridad e idempotencia.
- Clientes y movimientos se normalizan, pero no se cargan a la base de datos de momento.
- Con más tiempo agregaría esas entidades, validación formal de RUT, más pruebas de integración y documentación OpenAPI/Swagger.”

La solución prioriza que el flujo sea reproducible: el esquema se crea mediante migraciones, los datos externos se procesan con reglas explícitas y el reporte se calcula en PostgreSQL. Esto permite revisar cada parte por separado y repetir la carga sin generar duplicados.
