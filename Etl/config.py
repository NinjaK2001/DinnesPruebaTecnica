from pathlib import Path

COLUMN_ALIASES = {
    "sku": ["sku", "codigo", "codigo producto", "codigo_producto", "codigo sku", "cod", "cod producto"],
    "name": ["nombre", "producto", "descripcion", "descripción", "nombre producto", "nombre del producto"],
    "price": ["precio", "precio venta", "precio_venta", "valor", "pvp", "p venta", "precio ($)"],
    "stock": ["stock", "existencia", "existencias", "stock actual"],
    "order_number": ["pedido", "nro pedido", "n° pedido", "nº pedido", "numero pedido", "número pedido"],
    "date": ["fecha", "f emision", "f emisión", "fecha emision", "fecha emisión"],
    "customer": ["cliente", "razon social", "razón social"],
    "status": ["estado", "situacion", "situación"],
    "quantity": ["cant", "cantidad"],
    "unit_price": ["p unit", "p. unit", "precio unitario", "valor unitario"],
    "tax_id": ["rut", "rut cliente"],
    "active": ["activo", "activa", "vigente"],
    "description": ["descripcion", "descripción"],
    "entry": ["entrada"],
    "exit": ["salida"],
    "reason": ["motivo"],
    "document": ["documento"],
}

SUPPORTED_EXTENSIONS = {".xlsx", ".xls", ".csv"}
DEFAULT_OUTPUT_DIR = Path("output")
