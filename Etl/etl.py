import argparse
import json
from pathlib import Path

from config import DEFAULT_OUTPUT_DIR, SUPPORTED_EXTENSIONS
from postgres_loader import load_env_file, sync_to_postgres
from quality import build_quality_report
from readers import read_input


def parse_args():
    parser = argparse.ArgumentParser(description="ETL de datos externos")
    parser.add_argument("--input", action="append", help="Archivo de entrada; puede repetirse.")
    parser.add_argument("--input-dir", type=Path, help="Directorio de archivos Excel/CSV.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--sync", action="store_true", help="Sincroniza productos, pedidos y detalles.")
    parser.add_argument("--dry-run", action="store_true", help="Procesa sin escribir en PostgreSQL.")
    parser.add_argument("--db-host")
    parser.add_argument("--db-port")
    parser.add_argument("--db-name")
    parser.add_argument("--db-user")
    parser.add_argument("--db-password")
    args = parser.parse_args()

    paths = [Path(value) for value in (args.input or [])]
    if args.input_dir:
        paths.extend(sorted(path for path in args.input_dir.iterdir() if path.suffix.lower() in SUPPORTED_EXTENSIONS))
    if not paths:
        parser.error("Debe indicar --input o --input-dir.")
    if args.sync and args.dry_run:
        parser.error("--sync y --dry-run son opciones excluyentes.")
    for path in paths:
        if not path.exists():
            raise FileNotFoundError(f"No existe el archivo: {path}")
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            raise ValueError(f"Formato no soportado: {path.suffix}")
    args.input_paths = paths
    return args


def main():
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    load_env_file(Path(__file__).resolve().parents[1] / ".env")

    frames = []
    for path in args.input_paths:
        frame = read_input(path)
        frame["source_file"] = path.name
        frames.append(frame)

    import pandas as pd
    data = pd.concat(frames, ignore_index=True, sort=False)
    datasets, report = build_quality_report(data, args.output_dir)

    print("===================================")
    print("RESULTADO DE CALIDAD")
    print("===================================")
    print(json.dumps(report, indent=2, ensure_ascii=True))

    if args.sync:
        sync_to_postgres(datasets, args)
        print("Sincronizacion PostgreSQL completada.")
    else:
        print("Dry-run completado. Use --sync para cargar PostgreSQL.")


if __name__ == "__main__":
    main()
