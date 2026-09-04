from pathlib import Path

import pandas as pd

from config import COLUMN_ALIASES
from normalizers import (
    normalize_active,
    normalize_column_name,
    normalize_date,
    normalize_number,
    normalize_order_number,
    normalize_reason,
    normalize_sku,
    normalize_status,
    normalize_tax_id,
    normalize_text,
)

NORMALIZERS = {"sku": normalize_sku, "name": normalize_text, "customer": normalize_text, "description": normalize_text, "price": normalize_number, "stock": normalize_number, "quantity": normalize_number, "unit_price": normalize_number, "entry": normalize_number, "exit": normalize_number, "date": normalize_date, "order_number": normalize_order_number, "status": normalize_status, "reason": normalize_reason, "tax_id": normalize_tax_id, "active": normalize_active}


def detect_columns(columns):
    normalized = {normalize_column_name(column): column for column in columns}
    return {name: normalized[normalize_column_name(alias)] for name, aliases in COLUMN_ALIASES.items() for alias in aliases if normalize_column_name(alias) in normalized}


def detect_source_type(columns):
    source_columns = set(columns)
    if {"sku", "description", "entry", "exit"}.issubset(source_columns):
        return "movements"
    if {"order_number", "sku", "quantity", "unit_price"}.issubset(source_columns):
        return "order_items"
    if "tax_id" in source_columns and ({"customer", "active"} & source_columns):
        return "customers"
    if {"order_number", "date", "customer", "status"}.issubset(source_columns):
        return "orders"
    if {"sku", "name", "price", "stock"}.issubset(source_columns):
        return "products"
    return "unknown"


def detect_header_row(raw_df, max_rows=15):
    for row_index in range(min(max_rows, len(raw_df))):
        values = {normalize_column_name(value) for value in raw_df.iloc[row_index].tolist()}
        recognized = {name for name, aliases in COLUMN_ALIASES.items() if values.intersection(normalize_column_name(alias) for alias in aliases)}
        if len(recognized) >= 2:
            return row_index
    return None


def read_sheet(path, sheet_name):
    raw = pd.read_excel(path, sheet_name=sheet_name, header=None)
    header_row = detect_header_row(raw)
    if header_row is None:
        return None
    df = raw.iloc[header_row + 1:].copy()
    df.columns = raw.iloc[header_row].tolist()
    df = df.dropna(how="all")
    return standardize_dataframe(df, sheet_name)


def standardize_dataframe(df, sheet_name=None):
    detected = detect_columns(df.columns)
    source_type = detect_source_type(detected)
    if source_type == "unknown":
        return None
    if source_type == "movements":
        detected.pop("name", None)
    result = pd.DataFrame({name: df[column] for name, column in detected.items()})
    for name, normalizer in NORMALIZERS.items():
        if name in result:
            result[name] = result[name].apply(normalizer)
    result["source_sheet"] = sheet_name
    if source_type == "movements":
        result = result[result["sku"].notna()]
        result = result[~result["description"].isin({"total dia", "saldo inicial", "total"})]
    result["source_type"] = source_type
    return result


def read_excel_file(path):
    frames = [frame for sheet in pd.ExcelFile(path).sheet_names if (frame := read_sheet(path, sheet)) is not None and not frame.empty]
    if not frames:
        raise ValueError(f"No se encontraron hojas compatibles en {path}")
    return pd.concat(frames, ignore_index=True, sort=False)


def read_input(path):
    if Path(path).suffix.lower() == ".csv":
        return standardize_dataframe(pd.read_csv(path))
    return read_excel_file(path)
