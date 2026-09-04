import json
import pandas as pd

REQUIRED_COLUMNS = {"products": ["sku", "name", "price"], "orders": ["order_number", "date", "customer", "status"], "order_items": ["order_number", "sku", "quantity", "unit_price"]}


def prepare_quality_data(df, source_type):
    data = df.copy()
    rejected = []
    if source_type == "products" and "stock" in data:
        data["stock"] = data["stock"].fillna(0)
    required = REQUIRED_COLUMNS.get(source_type, [])
    invalid = pd.Series(False, index=data.index)
    for column in required:
        if column not in data:
            return data.iloc[0:0], pd.DataFrame([{"source_type": source_type, "reason": f"missing_column:{column}"}])
        invalid |= data[column].isna()
        if data[column].dtype == object:
            invalid |= data[column].astype(str).str.strip().eq("")
    for index, row in data[invalid].iterrows():
        rejected.append({"source_type": source_type, "source_sheet": row.get("source_sheet"), "reason": "missing_or_invalid_required_value"})
    clean = data[~invalid].copy()
    if source_type == "products":
        clean = clean.drop_duplicates("sku", keep="last")
    elif source_type == "orders":
        clean = clean.drop_duplicates("order_number", keep="last")
    elif source_type == "order_items":
        clean = clean.groupby(["order_number", "sku"], as_index=False).agg({"quantity": "sum", "unit_price": "last", "source_sheet": "last"})
    return clean, pd.DataFrame(rejected)


def build_quality_report(df, output_dir):
    datasets, rejected_frames, report = {}, [], {"input_records": int(len(df)), "rejected_records": 0, "sources": {}}
    for source_type, source_df in df.groupby("source_type"):
        clean, rejected = prepare_quality_data(source_df, source_type)
        datasets[source_type] = clean
        if not rejected.empty:
            rejected_frames.append(rejected)
        clean.to_csv(output_dir / f"normalized_{source_type}.csv", index=False, encoding="utf-8-sig")
        report["sources"][source_type] = {"read": int(len(source_df)), "accepted": int(len(clean))}
    rejected_df = pd.concat(rejected_frames, ignore_index=True) if rejected_frames else pd.DataFrame(columns=["source_type", "reason"])
    rejected_df.to_csv(output_dir / "rejected_records.csv", index=False, encoding="utf-8-sig")
    report["rejected_records"] = int(len(rejected_df))
    (output_dir / "quality_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")
    return datasets, report
