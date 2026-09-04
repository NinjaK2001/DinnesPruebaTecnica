import argparse
import json
import os
import re
import unicodedata
from pathlib import Path

import pandas as pd


# ============================================================
# ALIASES DE COLUMNAS
# ============================================================

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


# ============================================================
# NORMALIZACIONES COMUNES
# ============================================================

def normalize_text(value):
    """
    Normaliza texto:

    - NaN/None -> ""
    - elimina espacios laterales
    - convierte a minúsculas
    - elimina acentos
    - convierte múltiples espacios en uno
    """

    if pd.isna(value):
        return ""

    value = str(value).strip().lower()

    value = unicodedata.normalize("NFKD", value)

    value = "".join(
        char
        for char in value
        if not unicodedata.combining(char)
    )

    value = re.sub(r"\s+", " ", value)

    return value


def normalize_column_name(column):
    """
    Normaliza nombres de columnas.

    Ejemplos:

        Codigo
        código
        CODIGO_PRODUCTO
        codigo-producto
    """

    column = normalize_text(column)

    column = column.replace("_", " ")
    column = column.replace("-", " ")
    column = re.sub(r"[^a-z0-9 ]", "", column)
    column = re.sub(r"\s+", " ", column).strip()

    return column


def normalize_sku(value):
    """
    Normaliza SKU.

    Ejemplos:

        FER 0026 -> FER-0026
        fer-0026 -> FER-0026
        FER-0026 -> FER-0026
    """

    if pd.isna(value):
        return None

    value = normalize_text(value)

    if not value:
        return None

    value = re.sub(r"\s+", "-", value)

    value = re.sub(r"-+", "-", value)

    return value.upper()


def normalize_order_number(value):
    """
    Normaliza identificadores de pedido.

    Ejemplos:

        ped-1001 -> PED-1001
        PED-1001 -> PED-1001
        1001     -> PED-1001
        ped 1001 -> PED-1001
    """

    if pd.isna(value):
        return None

    value = normalize_text(value)

    if not value:
        return None

    # Normaliza espacios.
    value = re.sub(r"\s+", "-", value)

    # Busca un número al final.
    #
    # Acepta:
    # PED-1001
    # PED1001
    # PED 1001
    # 1001
    match = re.search(
        r"(?:ped-?)?(\d+)$",
        value,
    )

    if not match:
        return value.upper()

    return f"PED-{match.group(1)}"


def normalize_number(value):
    """
    Convierte valores numéricos provenientes de Excel/CSV.

    Ejemplos:

        3740       -> 3740.0
        "$ 3.740"  -> 3740.0
        "1.915,00" -> 1915.0
        "15%"      -> 0.15
        "-"        -> None
        ""         -> None

    Los valores vacíos NO se convierten automáticamente a 0.
    """

    if pd.isna(value):
        return None

    if isinstance(value, (int, float)):

        if pd.isna(value):
            return None

        return float(value)

    value = str(value).strip()

    if not value:
        return None

    normalized = normalize_text(value)

    if normalized in {
        "-",
        "--",
        "nan",
        "null",
        "none",
    }:
        return None

    # Porcentaje.
    if normalized.endswith("%"):

        numeric = normalized[:-1].strip()

        try:

            numeric = numeric.replace(".", "")
            numeric = numeric.replace(",", ".")

            return float(numeric) / 100

        except ValueError:

            return None

    # Elimina símbolos monetarios y otros caracteres.
    numeric = re.sub(
        r"[^\d,.\-]",
        "",
        normalized,
    )

    if not numeric:
        return None

    # Caso chileno:
    #
    # 1.915,00 -> 1915.00
    if "," in numeric and "." in numeric:

        if numeric.rfind(",") > numeric.rfind("."):

            numeric = numeric.replace(".", "")
            numeric = numeric.replace(",", ".")

        else:

            # Caso:
            # 1,915.00 -> 1915.00

            numeric = numeric.replace(",", "")

    # Caso:
    #
    # 3.740 -> 3740
    elif "." in numeric:

        parts = numeric.split(".")

        if len(parts) == 2 and len(parts[1]) == 3:

            numeric = "".join(parts)

    # Caso:
    #
    # 1915,00 -> 1915.00
    elif "," in numeric:

        parts = numeric.split(",")

        if len(parts) == 2:

            numeric = (
                parts[0]
                + "."
                + parts[1]
            )

        else:

            numeric = "".join(parts)

    try:

        return float(numeric)

    except ValueError:

        return None


def normalize_date(value):
    """
    Normaliza fechas a pandas.Timestamp.

    Soporta:

        2026-01-03
        03.01.2026
        06-ene-26
        18 de enero de 2026
        objetos datetime de Excel
        seriales Excel como 46058
    """

    if pd.isna(value):
        return None

    if isinstance(value, pd.Timestamp):

        return value.normalize()

    if hasattr(value, "year") and hasattr(value, "month"):

        try:

            return pd.Timestamp(value).normalize()

        except Exception:

            pass

    # Excel serial.
    if isinstance(value, (int, float)):

        if 1 <= value <= 100000:

            try:

                return (
                    pd.Timestamp("1899-12-30")
                    + pd.to_timedelta(
                        value,
                        unit="D",
                    )
                )

            except Exception:

                return None

    value = str(value).strip()

    if not value:
        return None

    normalized = normalize_text(value)

    # "18 de enero de 2026"
    #
    # ->
    #
    # "18 enero 2026"
    normalized = re.sub(
        r"\bde\b",
        "",
        normalized,
    )

    normalized = re.sub(
        r"\s+",
        " ",
        normalized,
    ).strip()

    months = {
        "ene": "jan",
        "enero": "january",
        "feb": "feb",
        "febrero": "february",
        "mar": "mar",
        "marzo": "march",
        "abr": "apr",
        "abril": "april",
        "may": "may",
        "mayo": "may",
        "jun": "jun",
        "junio": "june",
        "jul": "jul",
        "julio": "july",
        "ago": "aug",
        "agosto": "august",
        "sep": "sep",
        "sept": "sep",
        "septiembre": "september",
        "oct": "oct",
        "octubre": "october",
        "nov": "nov",
        "noviembre": "november",
        "dic": "dec",
        "diciembre": "december",
    }

    for spanish, english in months.items():

        normalized = re.sub(
            rf"\b{spanish}\b",
            english,
            normalized,
        )

    try:

        return pd.to_datetime(
            normalized,
            dayfirst=True,
            errors="coerce",
        )

    except Exception:

        return None


def normalize_status(value):
    """
    Normaliza estados de pedidos.
    """

    if pd.isna(value):
        return None

    value = normalize_text(value)

    if not value:
        return None

    status_map = {
        "entregado": "ENTREGADO",
        "entreg": "ENTREGADO",
        "entreg.": "ENTREGADO",

        "desp": "DESPACHADO",
        "despachado": "DESPACHADO",

        "pend": "PENDIENTE",
        "pendiente": "PENDIENTE",

        "en proceso": "EN_PROCESO",
        "en_proceso": "EN_PROCESO",

        "anulado": "ANULADO",
    }

    return status_map.get(
        value,
        value.upper(),
    )


def normalize_reason(value):
    """
    Normaliza motivos de movimientos.

    Ejemplos:

        ingreso             -> OTRO
        compra              -> COMPRA
        venta               -> VENTA
        venta pedido 1030   -> VENTA
        despacho            -> VENTA
        devolución          -> DEVOLUCION
        merma               -> MERMA
    """

    if pd.isna(value):
        return None

    value = normalize_text(value)

    if not value:
        return None

    if "compra" in value:
        return "COMPRA"

    if "venta" in value or "despacho" in value:
        return "VENTA"

    if "devol" in value:
        return "DEVOLUCION"

    if "merma" in value:
        return "MERMA"

    return "OTRO"


def normalize_tax_id(value):
    """
    Normaliza RUT.

    Ejemplo:

        12.345.678-9 -> 12345678-9
    """

    if pd.isna(value):
        return None

    value = str(value).strip()

    if not value:
        return None

    value = value.replace(".", "")
    value = value.replace(" ", "")

    return value.upper()


def normalize_active(value):
    """
    Normaliza valores de activo.

        1 / S / SI -> True
        0 / - / NO / N -> False
    """

    if pd.isna(value):
        return None

    value = normalize_text(value)

    if value in {
        "1",
        "s",
        "si",
        "sí",
        "true",
        "activo",
    }:
        return True

    if value in {
        "0",
        "-",
        "no",
        "n",
        "false",
        "inactivo",
    }:
        return False

    return None


# ============================================================
# DETECCIÓN DE COLUMNAS
# ============================================================

def find_standard_column(columns, aliases):
    """
    Busca una columna usando aliases normalizados.
    """

    normalized_columns = {
        normalize_column_name(column): column
        for column in columns
    }

    for alias in aliases:

        alias = normalize_column_name(alias)

        if alias in normalized_columns:

            return normalized_columns[alias]

    return None


def detect_columns(df):
    """
    Detecta columnas conocidas.

    Ejemplo:

        {
            "sku": "SKU",
            "name": "DESCRIPCION",
            "entry": "ENTRADA",
            "exit": "SALIDA"
        }
    """

    detected = {}

    for standard_name, aliases in COLUMN_ALIASES.items():

        column = find_standard_column(
            df.columns,
            aliases,
        )

        if column:
            detected[standard_name] = column

    return detected


# ============================================================
# DETECTOR DE TIPO DE FUENTE
# ============================================================

def detect_source_type(df):
    """
    Determina el tipo de información de un DataFrame.

    Tipos posibles:

        products
        orders
        order_items
        customers
        movements
        unknown
    """

    detected = detect_columns(df)
    
    columns = set(detected.keys())

    # --------------------------------------------------------
    # MOVIMIENTOS
    # --------------------------------------------------------

    if {
        "sku",
        "description",
        "entry",
        "exit",
    }.issubset(columns):

        return "movements"

    # --------------------------------------------------------
    # DETALLE DE PEDIDOS
    # --------------------------------------------------------

    if {
        "order_number",
        "sku",
        "quantity",
        "unit_price",
    }.issubset(columns):

        return "order_items"

    # --------------------------------------------------------
    # CLIENTES
    # --------------------------------------------------------

    if (
        "tax_id" in columns
        and (
            "customer" in columns
            or "active" in columns
        )
    ):

        return "customers"

    # --------------------------------------------------------
    # PEDIDOS
    # --------------------------------------------------------

    if {
        "order_number",
        "date",
        "customer",
        "status",
    }.issubset(columns):

        return "orders"

    # --------------------------------------------------------
    # PRODUCTOS
    # --------------------------------------------------------

    if {
        "sku",
        "name",
        "price",
        "stock",
    }.issubset(columns):

        return "products"

    return "unknown"


# ============================================================
# DETECCIÓN DE HEADER
# ============================================================

def detect_header_row(raw_df, max_rows=15):
    """
    Busca una fila que contenga al menos dos columnas
    reconocibles.

    Esto evita considerar cualquier aparición aislada
    de "SKU" como encabezado.
    """

    rows_to_check = min(
        max_rows,
        len(raw_df),
    )

    for row_index in range(rows_to_check):

        row = raw_df.iloc[row_index]

        values = [
            normalize_column_name(value)
            for value in row.tolist()
        ]

        recognized = set()

        for standard_name, aliases in COLUMN_ALIASES.items():

            normalized_aliases = {
                normalize_column_name(alias)
                for alias in aliases
            }

            if any(
                value in normalized_aliases
                for value in values
            ):

                recognized.add(standard_name)

        if len(recognized) >= 2:

            return row_index

    return None


# ============================================================
# LECTURA DE HOJAS EXCEL
# ============================================================

def read_sheet(excel_file, sheet_name):

    print(f"\nProcesando hoja: {sheet_name}")

    raw_df = pd.read_excel(
        excel_file,
        sheet_name=sheet_name,
        header=None,
    )

    header_row = detect_header_row(raw_df)

    if header_row is None:

        print(
            "  [IGNORADA] "
            "No se encontró encabezado reconocible."
        )

        return None

    print(
        f"  Encabezado encontrado en fila: "
        f"{header_row + 1}"
    )

    headers = raw_df.iloc[
        header_row
    ].tolist()

    df = raw_df.iloc[
        header_row + 1:
    ].copy()

    df.columns = headers

    # Elimina filas completamente vacías.
    df = df.dropna(how="all")

    detected_columns = detect_columns(df)

    source_type = detect_source_type(df)

    # --------------------------------------------------------
    # CORRECCIÓN ESPECÍFICA DE MOVIMIENTOS
    # --------------------------------------------------------
    #
    # DESCRIPCION puede coincidir tanto con "name"
    # como con "description".
    #
    # En movimientos queremos solamente "description".

    if source_type == "movements":

        detected_columns.pop(
            "name",
            None,
        )

    print(
        f"  Columnas detectadas: "
        f"{detected_columns}"
    )

    print(
        f"  Tipo de fuente: "
        f"{source_type}"
    )

    if source_type == "unknown":

        print(
            "  [IGNORADA] "
            "Las columnas no corresponden "
            "a una fuente conocida."
        )

        return None

    # --------------------------------------------------------
    # ESTANDARIZACIÓN DE NOMBRES
    # --------------------------------------------------------

    standardized = pd.DataFrame()

    for standard_name, original_column in detected_columns.items():

        standardized[standard_name] = df[
            original_column
        ]

    # Trazabilidad.
    standardized["source_sheet"] = sheet_name

    # ========================================================
    # NORMALIZACIONES COMUNES
    # ========================================================

    if "sku" in standardized.columns:

        standardized["sku"] = standardized[
            "sku"
        ].apply(normalize_sku)

    if "name" in standardized.columns:

        standardized["name"] = standardized[
            "name"
        ].apply(normalize_text)

    if "customer" in standardized.columns:

        standardized["customer"] = standardized[
            "customer"
        ].apply(normalize_text)

    if "description" in standardized.columns:

        standardized["description"] = standardized[
            "description"
        ].apply(normalize_text)

    if "price" in standardized.columns:

        standardized["price"] = standardized[
            "price"
        ].apply(normalize_number)

    if "stock" in standardized.columns:

        standardized["stock"] = standardized[
            "stock"
        ].apply(normalize_number)

    if "quantity" in standardized.columns:

        standardized["quantity"] = standardized[
            "quantity"
        ].apply(normalize_number)

    if "unit_price" in standardized.columns:

        standardized["unit_price"] = standardized[
            "unit_price"
        ].apply(normalize_number)

    if "entry" in standardized.columns:

        standardized["entry"] = standardized[
            "entry"
        ].apply(normalize_number)

    if "exit" in standardized.columns:

        standardized["exit"] = standardized[
            "exit"
        ].apply(normalize_number)

    if "date" in standardized.columns:

        standardized["date"] = standardized[
            "date"
        ].apply(normalize_date)

    if "order_number" in standardized.columns:

        standardized["order_number"] = standardized[
            "order_number"
        ].apply(normalize_order_number)

    if "status" in standardized.columns:

        standardized["status"] = standardized[
            "status"
        ].apply(normalize_status)

    if "reason" in standardized.columns:

        standardized["reason"] = standardized[
            "reason"
        ].apply(normalize_reason)

    if "tax_id" in standardized.columns:

        standardized["tax_id"] = standardized[
            "tax_id"
        ].apply(normalize_tax_id)

    if "active" in standardized.columns:

        standardized["active"] = standardized[
            "active"
        ].apply(normalize_active)

    # ========================================================
    # FILTROS ESPECÍFICOS DE MOVIMIENTOS
    # ========================================================

    if source_type == "movements":

        # Un movimiento real necesita SKU.
        standardized = standardized[
            standardized["sku"].notna()
        ].copy()

        # Elimina filas de resumen.
        if "description" in standardized.columns:

            standardized = standardized[
                ~standardized["description"].isin([
                    "total dia",
                    "saldo inicial",
                    "total",
                ])
            ].copy()

    return standardized, source_type


# ============================================================
# LECTURA DE EXCEL
# ============================================================

def read_excel_file(file_path):

    excel = pd.ExcelFile(file_path)

    print("Hojas encontradas:")

    for sheet_name in excel.sheet_names:

        print(
            f"  - {sheet_name}"
        )

    datasets = []

    for sheet_name in excel.sheet_names:

        result = read_sheet(
            file_path,
            sheet_name,
        )

        if result is None:
            continue

        df, source_type = result

        if not df.empty:

            df["source_type"] = source_type

            datasets.append(df)

    if not datasets:

        raise ValueError(
            "No se encontraron hojas "
            "con datos compatibles."
        )

    return pd.concat(
        datasets,
        ignore_index=True,
    )


# ============================================================
# LECTURA DE CSV
# ============================================================

def read_csv_file(file_path):

    df = pd.read_csv(file_path)

    source_type = detect_source_type(df)

    print(
        f"Tipo de fuente detectado: "
        f"{source_type}"
    )

    if source_type == "unknown":

        raise ValueError(
            "El CSV no corresponde "
            "a una fuente conocida."
        )

    detected_columns = detect_columns(df)

    # Misma corrección que para Excel.
    if source_type == "movements":

        detected_columns.pop(
            "name",
            None,
        )

    standardized = pd.DataFrame()

    for standard_name, original_column in detected_columns.items():

        standardized[standard_name] = df[
            original_column
        ]

    standardized["source_type"] = source_type
    standardized["source_sheet"] = None

    # ========================================================
    # NORMALIZACIONES COMUNES
    # ========================================================

    if "sku" in standardized.columns:

        standardized["sku"] = standardized[
            "sku"
        ].apply(normalize_sku)

    if "name" in standardized.columns:

        standardized["name"] = standardized[
            "name"
        ].apply(normalize_text)

    if "customer" in standardized.columns:

        standardized["customer"] = standardized[
            "customer"
        ].apply(normalize_text)

    if "description" in standardized.columns:

        standardized["description"] = standardized[
            "description"
        ].apply(normalize_text)

    if "price" in standardized.columns:

        standardized["price"] = standardized[
            "price"
        ].apply(normalize_number)

    if "stock" in standardized.columns:

        standardized["stock"] = standardized[
            "stock"
        ].apply(normalize_number)

    if "quantity" in standardized.columns:

        standardized["quantity"] = standardized[
            "quantity"
        ].apply(normalize_number)

    if "unit_price" in standardized.columns:

        standardized["unit_price"] = standardized[
            "unit_price"
        ].apply(normalize_number)

    if "entry" in standardized.columns:

        standardized["entry"] = standardized[
            "entry"
        ].apply(normalize_number)

    if "exit" in standardized.columns:

        standardized["exit"] = standardized[
            "exit"
        ].apply(normalize_number)

    if "date" in standardized.columns:

        standardized["date"] = standardized[
            "date"
        ].apply(normalize_date)

    if "order_number" in standardized.columns:

        standardized["order_number"] = standardized[
            "order_number"
        ].apply(normalize_order_number)

    if "status" in standardized.columns:

        standardized["status"] = standardized[
            "status"
        ].apply(normalize_status)

    if "reason" in standardized.columns:

        standardized["reason"] = standardized[
            "reason"
        ].apply(normalize_reason)

    if "tax_id" in standardized.columns:

        standardized["tax_id"] = standardized[
            "tax_id"
        ].apply(normalize_tax_id)

    if "active" in standardized.columns:

        standardized["active"] = standardized[
            "active"
        ].apply(normalize_active)

    return standardized


# ============================================================
# CALIDAD Y SINCRONIZACION
# ============================================================

REQUIRED_COLUMNS = {
    "products": ["sku", "name", "price"],
    "orders": ["order_number", "date", "customer", "status"],
    "order_items": [
        "order_number",
        "sku",
        "quantity",
        "unit_price",
    ],
}


def is_missing(value):
    return value is None or pd.isna(value)


def prepare_quality_data(df, source_type):
    """
    Aplica reglas deterministas antes de cargar:

    - Productos: stock vacio se interpreta como 0.
    - Campos clave o numericos invalidos se rechazan.
    - Duplicados se consolidan por su clave natural.
    """

    data = df.copy()
    rejected = []

    if source_type == "products" and "stock" in data.columns:
        data["stock"] = data["stock"].fillna(0)

    required = REQUIRED_COLUMNS.get(source_type, [])
    for column in required:
        if column not in data.columns:
            rejected.append({
                "source_type": source_type,
                "reason": f"missing_column:{column}",
            })
            return data.iloc[0:0], pd.DataFrame(rejected)

    invalid = pd.Series(False, index=data.index)
    for column in required:
        invalid |= data[column].isna()
        if data[column].dtype == object:
            invalid |= data[column].astype(str).str.strip().eq("")

    if source_type in {"products", "order_items"}:
        numeric_columns = {
            "products": ["price", "stock"],
            "order_items": ["quantity", "unit_price"],
        }[source_type]
        for column in numeric_columns:
            if column in data.columns:
                invalid |= data[column].apply(is_missing)

    for index, row in data[invalid].iterrows():
        rejected.append({
            "source_type": source_type,
            "source_sheet": row.get("source_sheet"),
            "reason": "missing_or_invalid_required_value",
        })

    clean = data[~invalid].copy()

    if source_type == "products":
        clean = clean.sort_values("source_sheet" if "source_sheet" in clean else "sku")
        clean = clean.drop_duplicates("sku", keep="last")
    elif source_type == "orders":
        clean = clean.drop_duplicates("order_number", keep="last")
    elif source_type == "order_items":
        clean = (
            clean.sort_values("source_sheet")
            .groupby(["order_number", "sku"], as_index=False)
            .agg({
                "quantity": "sum",
                "unit_price": "last",
                "source_sheet": "last",
            })
        )

    return clean, pd.DataFrame(rejected)


def load_input_files(input_paths):
    frames = []
    for input_path in input_paths:
        if input_path.suffix.lower() == ".csv":
            frame = read_csv_file(input_path)
        else:
            frame = read_excel_file(input_path)
        frame["source_file"] = input_path.name
        frames.append(frame)

    if not frames:
        raise ValueError("No se encontraron archivos de entrada.")

    return pd.concat(frames, ignore_index=True, sort=False)


def build_quality_report(df, output_dir):
    normalized = {}
    rejected_frames = []

    for source_type, source_df in df.groupby("source_type"):
        clean, rejected = prepare_quality_data(source_df, source_type)
        normalized[source_type] = clean
        if not rejected.empty:
            rejected_frames.append(rejected)
        clean.to_csv(
            output_dir / f"normalized_{source_type}.csv",
            index=False,
            encoding="utf-8-sig",
        )

    rejected_df = (
        pd.concat(rejected_frames, ignore_index=True)
        if rejected_frames
        else pd.DataFrame(columns=["source_type", "reason"])
    )
    rejected_df.to_csv(
        output_dir / "rejected_records.csv",
        index=False,
        encoding="utf-8-sig",
    )

    report = {
        "input_records": int(len(df)),
        "rejected_records": int(len(rejected_df)),
        "sources": {},
    }
    for source_type, source_df in df.groupby("source_type"):
        report["sources"][source_type] = {
            "read": int(len(source_df)),
            "accepted": int(len(normalized[source_type])),
        }

    (output_dir / "quality_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=True),
        encoding="utf-8",
    )
    return normalized, report


def load_env_file(path):
    """Carga pares KEY=VALUE sin sobreescribir variables existentes."""

    if not path.exists():
        return

    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"\''))


def sync_to_postgres(datasets, args):
    try:
        import psycopg2
    except ImportError as error:
        raise RuntimeError(
            "Instala las dependencias del ETL con: "
            "pip install -r requirements.txt"
        ) from error

    connection = psycopg2.connect(
        host=args.db_host or os.getenv("POSTGRES_HOST", "localhost"),
        port=args.db_port or os.getenv("POSTGRES_PORT", "5432"),
        dbname=args.db_name or os.getenv("POSTGRES_DB"),
        user=args.db_user or os.getenv("POSTGRES_USER"),
        password=args.db_password or os.getenv("POSTGRES_PASSWORD"),
    )

    try:
        with connection:
            with connection.cursor() as cursor:
                products = datasets.get("products", pd.DataFrame())
                for row in products.to_dict("records"):
                    cursor.execute(
                        """
                        INSERT INTO products (name, sku, stock, price)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (sku) DO UPDATE SET
                          name = EXCLUDED.name,
                          stock = EXCLUDED.stock,
                          price = EXCLUDED.price,
                          updated_at = NOW()
                        """,
                        (row["name"], row["sku"], row.get("stock", 0), row["price"]),
                    )

                orders = datasets.get("orders", pd.DataFrame())
                for row in orders.to_dict("records"):
                    cursor.execute(
                        """
                        INSERT INTO orders
                          (external_order_number, date, status, customer)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (external_order_number) DO UPDATE SET
                          date = EXCLUDED.date,
                          status = EXCLUDED.status,
                          customer = EXCLUDED.customer,
                          updated_at = NOW()
                        """,
                        (
                            row["order_number"],
                            row["date"].to_pydatetime(),
                            row["status"],
                            row["customer"],
                        ),
                    )

                items = datasets.get("order_items", pd.DataFrame())
                for row in items.to_dict("records"):
                    cursor.execute(
                        "SELECT id FROM orders WHERE external_order_number = %s",
                        (row["order_number"],),
                    )
                    order = cursor.fetchone()
                    cursor.execute(
                        "SELECT id FROM products WHERE sku = %s",
                        (row["sku"],),
                    )
                    product = cursor.fetchone()
                    if not order or not product:
                        continue
                    cursor.execute(
                        """
                        INSERT INTO order_items
                          ("orderId", "productId", quantity, unit_price)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT ("orderId", "productId") DO UPDATE SET
                          quantity = EXCLUDED.quantity,
                          unit_price = EXCLUDED.unit_price
                        """,
                        (
                            order[0],
                            product[0],
                            row["quantity"],
                            row["unit_price"],
                        ),
                    )
    finally:
        connection.close()


# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="ETL de datos externos")
    parser.add_argument(
        "--input",
        action="append",
        help="Archivo Excel/CSV de entrada. Puede repetirse.",
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        help="Directorio cuyos archivos Excel/CSV se procesaran.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output"),
        help="Directorio para datos limpios y reportes.",
    )
    parser.add_argument(
        "--sync",
        action="store_true",
        help="Sincroniza productos, pedidos y detalles con PostgreSQL.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Procesa y reporta sin conectarse a PostgreSQL.",
    )
    parser.add_argument("--db-host")
    parser.add_argument("--db-port")
    parser.add_argument("--db-name")
    parser.add_argument("--db-user")
    parser.add_argument("--db-password")
    args = parser.parse_args()

    input_paths = [Path(path) for path in (args.input or [])]
    if args.input_dir:
        input_paths.extend(
            sorted(
                path
                for path in args.input_dir.iterdir()
                if path.suffix.lower() in {".xlsx", ".xls", ".csv"}
            )
        )
    if not input_paths:
        parser.error("Debe indicar --input o --input-dir.")

    for input_path in input_paths:
        if not input_path.exists():
            raise FileNotFoundError(f"No existe el archivo: {input_path}")
        if input_path.suffix.lower() not in {".xlsx", ".xls", ".csv"}:
            raise ValueError("Formato no soportado. Use .xlsx, .xls o .csv")

    if args.sync and args.dry_run:
        parser.error("--sync y --dry-run son opciones excluyentes.")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    load_env_file(Path(__file__).resolve().parents[1] / ".env")
    df = load_input_files(input_paths)
    datasets, report = build_quality_report(df, args.output_dir)

    print("\n===================================")
    print("RESULTADO DE CALIDAD")
    print("===================================")
    print(json.dumps(report, indent=2, ensure_ascii=True))

    if args.sync:
        sync_to_postgres(datasets, args)
        print("\nSincronizacion PostgreSQL completada.")
    else:
        print(
            "\nDry-run completado. Para cargar a PostgreSQL use "
            "--sync despues de ejecutar las migraciones."
        )


if __name__ == "__main__":
    main()