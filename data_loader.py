import os
import re
import json
import sqlite3
import pandas as pd
from typing import Dict, List, Tuple, Any, Optional

def sanitize_identifier(name: str) -> str:
    """
    Sanitize table or column name into a clean SQLite-safe identifier.
    Example: 'School Name (US)' -> 'school_name_us'
    """
    name = str(name).strip().lower()
    # Replace any non-alphanumeric character with underscore
    name = re.sub(r'[^a-zA-Z0-9_]+', '_', name)
    # Trim leading/trailing underscores
    name = name.strip('_')
    # Identifiers cannot start with a number
    if name and name[0].isdigit():
        name = f"t_{name}"
    return name or "col"

def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Sanitizes column names and removes completely empty rows/columns.
    """
    df = df.copy()
    new_cols = []
    seen = {}
    
    for col in df.columns:
        clean_col = sanitize_identifier(str(col))
        if clean_col in seen:
            seen[clean_col] += 1
            clean_col = f"{clean_col}_{seen[clean_col]}"
        else:
            seen[clean_col] = 1
        new_cols.append(clean_col)
        
    df.columns = new_cols
    return df

def load_file_to_dataframes(file_path_or_buffer, filename: Optional[str] = None) -> Dict[str, pd.DataFrame]:
    """
    Loads CSV, Excel, or JSON file into one or more DataFrames.
    Returns a dict mapping {table_name: dataframe}.
    """
    if filename is None:
        if isinstance(file_path_or_buffer, str):
            filename = os.path.basename(file_path_or_buffer)
        elif hasattr(file_path_or_buffer, "name"):
            filename = file_path_or_buffer.name
        else:
            filename = "data_table"

    base_name = os.path.splitext(filename)[0]
    default_table_name = sanitize_identifier(base_name)
    ext = os.path.splitext(filename)[1].lower()

    dataframes: Dict[str, pd.DataFrame] = {}

    if ext == ".csv":
        try:
            df = pd.read_csv(file_path_or_buffer, encoding="utf-8")
        except UnicodeDecodeError:
            if hasattr(file_path_or_buffer, "seek"):
                file_path_or_buffer.seek(0)
            df = pd.read_csv(file_path_or_buffer, encoding="latin1")
        dataframes[default_table_name] = clean_dataframe(df)

    elif ext in [".xlsx", ".xls"]:
        excel_data = pd.read_excel(file_path_or_buffer, sheet_name=None)
        if isinstance(excel_data, dict):
            for sheet_name, df in excel_data.items():
                if len(excel_data) == 1:
                    tbl_name = default_table_name
                else:
                    tbl_name = f"{default_table_name}_{sanitize_identifier(sheet_name)}"
                dataframes[tbl_name] = clean_dataframe(df)
        else:
            dataframes[default_table_name] = clean_dataframe(excel_data)

    elif ext == ".json":
        if hasattr(file_path_or_buffer, "read"):
            content = file_path_or_buffer.read()
            if isinstance(content, bytes):
                content = content.decode("utf-8")
            data = json.loads(content)
        else:
            with open(file_path_or_buffer, "r", encoding="utf-8") as f:
                data = json.load(f)

        # Normalize JSON
        if isinstance(data, list):
            # Array of objects
            df = pd.json_normalize(data)
        elif isinstance(data, dict):
            # Check if any value is a list of records
            list_keys = [k for k, v in data.items() if isinstance(v, list) and len(v) > 0 and isinstance(v[0], dict)]
            if list_keys:
                for k in list_keys:
                    tbl_name = f"{default_table_name}_{sanitize_identifier(k)}" if len(list_keys) > 1 else default_table_name
                    dataframes[tbl_name] = clean_dataframe(pd.json_normalize(data[k]))
                return dataframes
            else:
                df = pd.json_normalize(data)
        else:
            df = pd.DataFrame([{"value": data}])

        dataframes[default_table_name] = clean_dataframe(df)

    else:
        raise ValueError(f"Unsupported file format '{ext}'. Supported formats: .csv, .xlsx, .xls, .json")

    return dataframes

def save_dataframes_to_sqlite(dataframes: Dict[str, pd.DataFrame], conn: sqlite3.Connection, if_exists: str = "replace"):
    """
    Saves a dictionary of dataframes into a SQLite database.
    """
    for table_name, df in dataframes.items():
        df.to_sql(table_name, conn, if_exists=if_exists, index=False)

def get_database_schema(conn: sqlite3.Connection) -> Tuple[Dict[str, List[str]], str, Dict[str, List[Dict[str, Any]]]]:
    """
    Returns:
    1. schema_dict: {table_name: [col1, col2, ...]}
    2. ddl_text: String containing CREATE TABLE statements
    3. sample_data: 2 sample rows per table as a dict
    """
    cursor = conn.cursor()
    cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
    tables_info = cursor.fetchall()

    schema_dict: Dict[str, List[str]] = {}
    ddl_statements: List[str] = []
    sample_data: Dict[str, List[Dict[str, Any]]] = {}

    for table_name, sql_ddl in tables_info:
        if sql_ddl:
            ddl_statements.append(f"{sql_ddl};")
        
        # Get columns via PRAGMA
        cursor.execute(f"PRAGMA table_info('{table_name}');")
        cols = [row[1] for row in cursor.fetchall()]
        schema_dict[table_name] = cols

        # Fetch sample rows (up to 2)
        try:
            cursor.execute(f"SELECT * FROM '{table_name}' LIMIT 2;")
            rows = cursor.fetchall()
            sample_rows = [dict(zip(cols, row)) for row in rows]
            sample_data[table_name] = sample_rows
        except Exception:
            sample_data[table_name] = []

    ddl_text = "\n".join(ddl_statements)
    return schema_dict, ddl_text, sample_data

def export_table(conn: sqlite3.Connection, table_name: str, format_type: str = "csv") -> Any:
    """
    Exports a table from SQLite to CSV, Excel, or JSON bytes.
    """
    df = pd.read_sql_query(f"SELECT * FROM '{table_name}'", conn)
    format_type = format_type.lower()

    if format_type == "csv":
        return df.to_csv(index=False).encode("utf-8")
    elif format_type in ["excel", "xlsx"]:
        import io
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name=table_name[:30])
        return buffer.getvalue()
    elif format_type == "json":
        return df.to_json(orient="records", indent=2).encode("utf-8")
    else:
        raise ValueError(f"Unsupported export format: {format_type}")
