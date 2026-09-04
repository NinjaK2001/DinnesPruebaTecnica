import re
import unicodedata

import pandas as pd


def normalize_text(value):
    if pd.isna(value):
        return ""
    value = unicodedata.normalize("NFKD", str(value).strip().lower())
    value = "".join(char for char in value if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", value)


def normalize_column_name(column):
    value = normalize_text(column).replace("_", " ").replace("-", " ")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", "", value)).strip()


def normalize_sku(value):
    value = normalize_text(value)
    return re.sub(r"-+", "-", re.sub(r"\s+", "-", value)).upper() or None


def normalize_order_number(value):
    value = normalize_text(value)
    if not value:
        return None
    value = re.sub(r"\s+", "-", value)
    match = re.search(r"(?:ped-?)?(\d+)$", value)
    return f"PED-{match.group(1)}" if match else value.upper()


def normalize_number(value):
    if pd.isna(value):
        return None
    if isinstance(value, (int, float)):
        return None if pd.isna(value) else float(value)
    value = str(value).strip()
    if not value or normalize_text(value) in {"-", "--", "nan", "null", "none"}:
        return None
    numeric = re.sub(r"[^\d,.\-%]", "", normalize_text(value))
    if numeric.endswith("%"):
        return normalize_number(numeric[:-1]) / 100
    if "," in numeric and "." in numeric:
        numeric = numeric.replace(".", "").replace(",", ".") if numeric.rfind(",") > numeric.rfind(".") else numeric.replace(",", "")
    elif "." in numeric and len(numeric.rsplit(".", 1)[1]) == 3:
        numeric = numeric.replace(".", "")
    elif "," in numeric:
        parts = numeric.split(",")
        numeric = parts[0] + "." + parts[1] if len(parts) == 2 else "".join(parts)
    try:
        return float(numeric)
    except ValueError:
        return None


def normalize_date(value):
    if pd.isna(value):
        return None
    if isinstance(value, (int, float)) and 1 <= value <= 100000:
        return pd.Timestamp("1899-12-30") + pd.to_timedelta(value, unit="D")
    if hasattr(value, "year") and hasattr(value, "month"):
        return pd.Timestamp(value).normalize()
    value = re.sub(r"\bde\b", "", normalize_text(value))
    months = {"ene": "jan", "enero": "january", "feb": "feb", "febrero": "february", "mar": "mar", "marzo": "march", "abr": "apr", "abril": "april", "may": "may", "mayo": "may", "jun": "jun", "junio": "june", "jul": "jul", "julio": "july", "ago": "aug", "agosto": "august", "sep": "sep", "sept": "sep", "septiembre": "september", "oct": "oct", "octubre": "october", "nov": "nov", "noviembre": "november", "dic": "dec", "diciembre": "december"}
    for spanish, english in months.items():
        value = re.sub(rf"\b{spanish}\b", english, value)
    return pd.to_datetime(value, dayfirst=True, errors="coerce")


def normalize_status(value):
    value = normalize_text(value)
    return {"entregado": "ENTREGADO", "entreg": "ENTREGADO", "entreg.": "ENTREGADO", "desp": "DESPACHADO", "despachado": "DESPACHADO", "pend": "PENDIENTE", "pendiente": "PENDIENTE", "en proceso": "EN_PROCESO", "en_proceso": "EN_PROCESO", "anulado": "ANULADO"}.get(value, value.upper() or None)


def normalize_reason(value):
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
    if pd.isna(value) or not str(value).strip():
        return None
    return str(value).strip().replace(".", "").replace(" ", "").upper()


def normalize_active(value):
    value = normalize_text(value)
    if value in {"1", "s", "si", "true", "activo"}:
        return True
    if value in {"0", "-", "no", "n", "false", "inactivo"}:
        return False
    return None
