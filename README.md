# ⚡ QueryMorph Studio
### The Universal Conversational Data Engine & Autonomous CRUD Workspace

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://querymorph-studio.streamlit.app/)
[![GitHub Repo](https://img.shields.io/badge/GitHub-Repository-blue?logo=github)](https://github.com/aepasanket4-sudo/QueryMorph-Studio)

> 🚀 **Live Demo:** Access the live application directly in your browser at **[https://querymorph-studio.streamlit.app/](https://querymorph-studio.streamlit.app/)**

A modular AI-powered system that ingests **CSV, Excel (.xlsx, .xls), and JSON** files into an in-memory SQL relational database and performs **any SQL query, analytical join, or CRUD mutation** using **Natural Language**.

---

## 🌟 Key Features

1. **Multi-Format Ingestion**:
   - **CSV**: Automatic UTF-8/Latin1 detection, header cleaning.
   - **Excel**: Ingests `.xlsx` and `.xls`, automatically converting sheets into separate SQL tables.
   - **JSON**: Ingests record arrays and nested JSON schemas using `pd.json_normalize`.
   - **Multi-File Joins**: Ingest multiple different files (e.g. `universities.csv` + `students.json`) and run SQL `JOIN`s across them.

2. **Full CRUD & SQL Operations via Natural Language**:
   - **Create / Insert**: *"Add a new student named John Doe with GPA 3.9"* -> `INSERT INTO students ...`
   - **Read / Query**: *"Which university has the highest average GPA?"* -> `SELECT ... JOIN ... GROUP BY ...`
   - **Update**: *"Change Alice's status to Graduated"* -> `UPDATE students SET status = 'Graduated' WHERE ...`
   - **Delete**: *"Remove all records where GPA is below 2.0"* -> `DELETE FROM students WHERE ...`
   - **DDL**: *"Add a new column called scholarship_amount to students"* -> `ALTER TABLE students ADD ...`

3. **Provider Toggle (Groq & Gemini)**:
   - Toggle seamlessly between **Groq** (`openai/gpt-oss-120b`, `llama-3.3-70b-versatile`) and **Gemini** (`gemini-2.5-flash`, `gemini-3.5-flash-lite`).

4. **Self-Healing SQL Retry Loop**:
   - Parses queries with `sqlglot` to validate syntax and table existence.
   - Automatically passes runtime database errors back to the LLM to self-heal.

5. **Data Export**:
   - Download updated tables back into **CSV**, **Excel**, or **JSON**.

---

## 🏗️ Architecture

```
├── data_loader.py    # Universal ingestion (CSV/Excel/JSON), SQLite conversion & data export
├── sql_engine.py     # SQLAgent with Groq/Gemini toggle, SQLGlot validation & CRUD executor
├── app.py            # CLI application & automated CRUD demonstration test suite
├── dashboard.py      # Interactive Streamlit Web UI with live table preview & export
└── sample_data/      # Sample datasets for instant testing (CSV, Excel, JSON)
```

---

## 🚀 Quickstart

### 1. Run the CLI & CRUD Demo (`app.py`)
To test the complete CRUD lifecycle and SQL joins across CSV, Excel, and JSON:

```bash
# Using Groq (default)
python app.py --provider groq

# Using Gemini
python app.py --provider gemini

# Interactive CLI mode (type your own queries & CRUD instructions)
python app.py --provider groq --interactive
```

### 2. Launch the Web Studio (`dashboard.py`)

#### Option A: Instant Live Web App
Access the deployed cloud studio without local setup:  
👉 **[https://querymorph-studio.streamlit.app/](https://querymorph-studio.streamlit.app/)**

#### Option B: Run Locally
```bash
streamlit run dashboard.py
```
- Toggle between **Groq** and **Gemini** in the sidebar.
- Upload any combination of CSV, Excel, or JSON files.
- Ask questions, make updates, insert rows, or delete records in plain English.
- Export and download your updated dataset in CSV, Excel, or JSON format.
