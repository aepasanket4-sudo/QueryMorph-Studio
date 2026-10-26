import sys
import os
import argparse
import sqlite3
import pandas as pd
from data_loader import (
    load_file_to_dataframes,
    save_dataframes_to_sqlite,
    get_database_schema,
    export_table
)
from sql_engine import SQLAgent, DEFAULT_GEMINI_KEY, DEFAULT_GROQ_KEY

# Ensure clean UTF-8 console output in Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

def setup_sample_excel_if_missing(folder: str = "sample_data") -> str:
    """Creates a sample courses.xlsx if not already present."""
    os.makedirs(folder, exist_ok=True)
    excel_path = os.path.join(folder, "courses.xlsx")
    if not os.path.exists(excel_path):
        courses_df = pd.DataFrame([
            {"course_id": "CS101", "course_name": "Intro to Computer Science", "credits": 4, "department": "Computer Science"},
            {"course_id": "MATH201", "course_name": "Linear Algebra", "credits": 3, "department": "Mathematics"},
            {"course_id": "PHYS150", "course_name": "General Physics", "credits": 4, "department": "Physics"},
            {"course_id": "BUS300", "course_name": "Principles of Management", "credits": 3, "department": "Business"}
        ])
        courses_df.to_excel(excel_path, index=False, engine="openpyxl")
    return excel_path

def load_all_sample_files(conn: sqlite3.Connection):
    """Loads CSV, Excel, and JSON into the SQLite connection."""
    sample_dir = os.path.join(os.path.dirname(__file__), "sample_data")
    setup_sample_excel_if_missing(sample_dir)

    supported_exts = [".csv", ".xlsx", ".xls", ".json"]
    loaded_tables = []

    for file_name in os.listdir(sample_dir):
        ext = os.path.splitext(file_name)[1].lower()
        if ext in supported_exts:
            full_path = os.path.join(sample_dir, file_name)
            dfs = load_file_to_dataframes(full_path)
            save_dataframes_to_sqlite(dfs, conn)
            loaded_tables.extend(dfs.keys())

    return loaded_tables

def print_banner(provider: str, model: str):
    print("=" * 70)
    print(" 🚀 UNIVERSAL TEXT-TO-SQL & CRUD ENGINE")
    print(f" • Active Provider : {provider.upper()}")
    print(f" • Model Name      : {model}")
    print(f" • Supported Types : CSV, Excel (.xlsx/.xls), JSON")
    print("=" * 70)

def run_agent_turn(agent: SQLAgent, conn: sqlite3.Connection, prompt: str, verbose: bool = False):
    print(f"\n💬 You: \"{prompt}\"")
    schema_dict, ddl_schema, sample_data = get_database_schema(conn)

    result = agent.process_nl_request(
        conn=conn,
        user_prompt=prompt,
        schema_dict=schema_dict,
        ddl_schema=ddl_schema,
        sample_data=sample_data
    )

    if result["success"]:
        # Pure proactive insight
        human_msg = result.get("human_response", result.get("message", "Request completed."))
        print(f"💡 Insight: {human_msg}")

        # Show tabular results if present
        if result["data"] is not None and not result["data"].empty:
            print("\n📊 Data Preview:")
            print(result["data"].to_string(index=False))

        # Technical details only if verbose
        if verbose:
            print(f"\n[Specs] SQL: {result['sql']} | Operation: {result['op_type']}")
    else:
        error_msg = result.get("human_response", f"Unable to process: {result.get('error')}")
        print(f"⚠️ Notice: {error_msg}")
        if verbose and result.get("sql"):
            print(f"[Specs] Attempted SQL: {result['sql']} | Error: {result.get('error')}")

def main():
    parser = argparse.ArgumentParser(description="Natural Language SQL & CRUD Agent")
    parser.add_argument(
        "--provider",
        choices=["gemini", "groq"],
        default="gemini",
        help="LLM provider to use: 'gemini' (default) or 'groq'"
    )
    parser.add_argument("--interactive", action="store_true", help="Start interactive CLI loop")
    args = parser.parse_args()

    # 1. Connect to In-Memory SQLite database
    conn = sqlite3.connect(":memory:")

    # 2. Ingest CSV, Excel, and JSON files
    tables = load_all_sample_files(conn)

    # 3. Initialize Agent with Provider Toggle
    agent = SQLAgent(provider=args.provider)
    print_banner(agent.provider, agent.model)
    print(f"📂 Loaded Tables into SQLite: {tables}\n")

    # Display current schema DDL
    _, ddl, _ = get_database_schema(conn)
    print("📋 Current Database Schema:")
    print(ddl)

    # 4. Demonstrate Full End-to-End CRUD Spectrum
    print("\n" + "=" * 70)
    print("🎯 DEMO: FULL CRUD & SQL OPERATIONS IN NATURAL LANGUAGE")
    print("=" * 70)

    # READ (SELECT)
    run_agent_turn(agent, conn, "List all universities ordered by school_name")

    # CREATE (INSERT)
    run_agent_turn(
        agent,
        conn,
        "Insert a new university with school_id 6, school_name 'Stanford', location 'Palo Alto', and nickname 'Cardinal'"
    )

    # READ (Verification of Insert)
    run_agent_turn(agent, conn, "Find the university located in Palo Alto")

    # UPDATE (Modification)
    run_agent_turn(
        agent,
        conn,
        "Update Stanford's nickname to 'The Cardinal Tree'"
    )

    # MULTI-TABLE JOIN (CSV + JSON)
    run_agent_turn(
        agent,
        conn,
        "Show each university school_name along with the number of enrolled students and their average GPA"
    )

    # DELETE (Removal)
    run_agent_turn(agent, conn, "Delete the university with school_id 6")

    # 5. Export demonstration
    print("\n" + "=" * 70)
    print("💾 DATA EXPORT DEMO")
    print("=" * 70)
    csv_bytes = export_table(conn, "universities", "csv")
    print(f"✅ Successfully exported 'universities' to CSV ({len(csv_bytes)} bytes)")
    json_bytes = export_table(conn, "universities", "json")
    print(f"✅ Successfully exported 'universities' to JSON ({len(json_bytes)} bytes)")
    excel_bytes = export_table(conn, "universities", "excel")
    print(f"✅ Successfully exported 'universities' to Excel ({len(excel_bytes)} bytes)")

    # 6. Optional Interactive CLI Loop
    if args.interactive:
        print("\n" + "=" * 70)
        print("💡 INTERACTIVE MODE ENABLED")
        print("Commands:")
        print("  • Type any question or CRUD command (e.g., 'Add a student', 'Find GPA > 3.5')")
        print("  • Type 'toggle' to switch between Groq and Gemini")
        print("  • Type 'tables' to list tables")
        print("  • Type 'exit' or 'quit' to close")
        print("=" * 70)

        while True:
            try:
                user_input = input("\n👉 Enter request: ").strip()
                if not user_input:
                    continue
                if user_input.lower() in ["exit", "quit"]:
                    print("Exiting...")
                    break
                elif user_input.lower() == "toggle":
                    new_provider = "gemini" if agent.provider == "groq" else "groq"
                    agent.switch_provider(new_provider)
                    print(f"🔄 Switched provider to: {agent.provider.upper()} ({agent.model})")
                elif user_input.lower() == "tables":
                    schema, _, _ = get_database_schema(conn)
                    for tbl, cols in schema.items():
                        print(f"  • {tbl}: {', '.join(cols)}")
                else:
                    run_agent_turn(agent, conn, user_input)
            except (KeyboardInterrupt, EOFError):
                break

if __name__ == "__main__":
    main()