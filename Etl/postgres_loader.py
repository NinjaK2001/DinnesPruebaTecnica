import os

import pandas as pd


def load_env_file(path):
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"\''))


def sync_to_postgres(datasets, args):
    import psycopg2
    connection = psycopg2.connect(host=args.db_host or os.getenv("POSTGRES_HOST", "localhost"), port=args.db_port or os.getenv("POSTGRES_PORT", "5432"), dbname=args.db_name or os.getenv("POSTGRES_DB"), user=args.db_user or os.getenv("POSTGRES_USER"), password=args.db_password or os.getenv("POSTGRES_PASSWORD"))
    try:
        with connection, connection.cursor() as cursor:
            for row in datasets.get("products", pd.DataFrame()).to_dict("records"):
                cursor.execute("INSERT INTO products (name, sku, stock, price) VALUES (%s, %s, %s, %s) ON CONFLICT (sku) DO UPDATE SET name=EXCLUDED.name, stock=EXCLUDED.stock, price=EXCLUDED.price, updated_at=NOW()", (row["name"], row["sku"], row.get("stock", 0), row["price"]))
            for row in datasets.get("orders", pd.DataFrame()).to_dict("records"):
                cursor.execute("INSERT INTO orders (external_order_number, date, status, customer) VALUES (%s, %s, %s, %s) ON CONFLICT (external_order_number) DO UPDATE SET date=EXCLUDED.date, status=EXCLUDED.status, customer=EXCLUDED.customer, updated_at=NOW()", (row["order_number"], row["date"].to_pydatetime(), row["status"], row["customer"]))
            for row in datasets.get("order_items", pd.DataFrame()).to_dict("records"):
                cursor.execute("SELECT id FROM orders WHERE external_order_number=%s", (row["order_number"],))
                order = cursor.fetchone()
                cursor.execute("SELECT id FROM products WHERE sku=%s", (row["sku"],))
                product = cursor.fetchone()
                if order and product:
                    cursor.execute("INSERT INTO order_items (\"orderId\", \"productId\", quantity, unit_price) VALUES (%s, %s, %s, %s) ON CONFLICT (\"orderId\", \"productId\") DO UPDATE SET quantity=EXCLUDED.quantity, unit_price=EXCLUDED.unit_price", (order[0], product[0], row["quantity"], row["unit_price"]))
    finally:
        connection.close()
