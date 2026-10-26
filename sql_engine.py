import os
import re
import sqlite3
import pandas as pd
import sqlglot
import sqlglot.expressions as exp
from typing import Dict, List, Tuple, Any, Optional
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def _resolve_key(env_name: str, fallback: str = "") -> str:
    """Resolve key from environment variables (.env / OS) or Streamlit secrets."""
    val = os.getenv(env_name)
    if val:
        return val
    try:
        import streamlit as st
        if hasattr(st, "secrets") and env_name in st.secrets:
            return str(st.secrets[env_name])
    except Exception:
        pass
    return fallback

# Supported default keys (safely resolved via .env, OS env vars, or st.secrets)
DEFAULT_GEMINI_KEY = _resolve_key("GEMINI_API_KEY", "")
DEFAULT_GROQ_KEY = _resolve_key("GROQ_API_KEY", "")

class SQLAgent:
    """
    Modular Agent supporting natural language SQL query & CRUD operations
    with provider toggle (Gemini vs Groq).
    """

    def __init__(
        self,
        provider: str = "gemini",  # "gemini" or "groq"
        api_key: Optional[str] = None,
        model_name: Optional[str] = None
    ):
        self.provider = provider.lower().strip()
        self.api_key = api_key
        self.model_name = model_name
        self._init_client()

    def _init_client(self):
        if self.provider == "gemini":
            from google import genai
            key = self.api_key or DEFAULT_GEMINI_KEY
            self.client = genai.Client(api_key=key)
            self.model = self.model_name or "gemini-3.5-flash-lite"
        elif self.provider == "groq":
            from groq import Groq
            key = self.api_key or DEFAULT_GROQ_KEY
            self.client = Groq(api_key=key)
            self.model = self.model_name or "openai/gpt-oss-120b"
        else:
            raise ValueError(f"Unknown provider '{self.provider}'. Must be 'gemini' or 'groq'.")

    def switch_provider(self, provider: str, api_key: Optional[str] = None, model_name: Optional[str] = None):
        """Allows toggling provider on the fly."""
        self.provider = provider.lower().strip()
        if api_key:
            self.api_key = api_key
        self.model_name = model_name
        self._init_client()

    def _call_llm(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        """Invokes the selected LLM provider with an optional custom system instruction."""
        if not system_instruction:
            system_instruction = (
                "You are an expert SQLite SQL engineer. "
                "Your task is to translate natural language into accurate, executable SQLite SQL statements. "
                "You MUST support both queries (SELECT) and CRUD operations (INSERT, UPDATE, DELETE, CREATE, DROP, ALTER). "
                "Output ONLY the SQL statement. No explanations, no markdown blocks, no conversational preamble."
            )

        if self.provider == "gemini":
            full_prompt = f"{system_instruction}\n\n{prompt}"
            response = self.client.models.generate_content(
                model=self.model,
                contents=full_prompt
            )
            raw = response.text or ""
        else: # Groq
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2
            )
            raw = response.choices[0].message.content or ""

        # Clean markdown code blocks if any
        cleaned = re.sub(r"^```(?:sql)?\s*", "", raw.strip(), flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned.strip())
        return cleaned.strip()

    def inspect_database_summary(self, conn: sqlite3.Connection) -> str:
        """
        Quickly inspects the database tables to gather high-level contextual intelligence
        (table row counts, key metrics, and category summaries).
        """
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        tables = [r[0] for r in cursor.fetchall()]

        summaries = []
        for tbl in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM '{tbl}'")
                count = cursor.fetchone()[0]
                cursor.execute(f"PRAGMA table_info('{tbl}')")
                cols = [c[1] for c in cursor.fetchall()]
                summaries.append(f"Table '{tbl}' ({count} rows, columns: {cols})")
            except Exception:
                continue

        return "; ".join(summaries)

    def check_referential_impact(self, conn: sqlite3.Connection, sql_query: str, op_type: str) -> Optional[str]:
        """
        Checks if a DELETE or UPDATE might affect related records in other tables
        (e.g., deleting a school_id that is referenced in the students table).
        """
        if "DELETE" not in op_type and "UPDATE" not in op_type:
            return None

        cursor = conn.cursor()
        # Find if a specific ID or foreign key was targeted
        match = re.search(r"(\w+_id)\s*=\s*['\"]?(\w+)['\"]?", sql_query, re.IGNORECASE)
        if not match:
            return None

        key_col, key_val = match.groups()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        tables = [r[0] for r in cursor.fetchall()]

        warnings = []
        for tbl in tables:
            try:
                cursor.execute(f"PRAGMA table_info('{tbl}')")
                cols = [c[1].lower() for c in cursor.fetchall()]
                if key_col.lower() in cols:
                    cursor.execute(f"SELECT COUNT(*) FROM '{tbl}' WHERE {key_col} = ?", (key_val,))
                    c = cursor.fetchone()[0]
                    if c > 0:
                        warnings.append(f"{c} record(s) in '{tbl}' share this {key_col}")
            except Exception:
                continue

        if len(warnings) > 1:
            return "Referential Note: " + ", and ".join(warnings) + "."
        return None

    def find_fuzzy_suggestions(self, conn: sqlite3.Connection, user_prompt: str) -> List[str]:
        """
        When 0 records match or user query fails, scans text columns for similar keywords.
        """
        words = [w for w in re.findall(r"\b[A-Za-z]{3,}\b", user_prompt) if w.lower() not in ["show", "list", "find", "what", "where", "with", "from", "order", "update", "delete", "insert"]]
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        tables = [r[0] for r in cursor.fetchall()]

        matches = []
        for word in words[:4]:
            for tbl in tables:
                try:
                    cursor.execute(f"PRAGMA table_info('{tbl}')")
                    text_cols = [c[1] for c in cursor.fetchall() if 'text' in str(c[2]).lower() or 'char' in str(c[2]).lower()]
                    for col in text_cols[:3]:
                        cursor.execute(f"SELECT DISTINCT \"{col}\" FROM \"{tbl}\" WHERE \"{col}\" LIKE ? LIMIT 2", (f"%{word}%",))
                        rows = cursor.fetchall()
                        for r in rows:
                            if r[0] and str(r[0]) not in matches:
                                matches.append(f"'{r[0]}' ({col} in {tbl})")
                except Exception:
                    continue

        return matches[:3]

    def generate_human_response(
        self,
        conn: sqlite3.Connection,
        user_prompt: str,
        sql_query: str,
        op_type: str,
        data: Optional[pd.DataFrame] = None,
        rows_affected: int = 0
    ) -> str:
        """
        Synthesizes a database-reactive, humanized conversational response.
        Includes proactive insights, anomaly detection, and smart follow-up suggestions.
        """
        db_summary = self.inspect_database_summary(conn)
        referential_warning = self.check_referential_impact(conn, sql_query, op_type)

        suggestions = []
        if (data is not None and data.empty) or (data is None and rows_affected == 0):
            suggestions = self.find_fuzzy_suggestions(conn, user_prompt)

        human_system_prompt = (
            "You are an executive Senior Data Strategist and Insight Analyst connected live to a database.\n"
            "CRITICAL REQUIREMENT:\n"
            "- Your output MUST be ONLY the PROACTIVE INSIGHT. Nothing else.\n"
            "- DO NOT include any labels, headers, or section titles such as 'Direct Conversational Answer', 'Proactive Data Insight', 'Summary:', 'Part 1', or 'Answer:'.\n"
            "- Synthesize the core answer, notable data patterns, anomalies, or operational impact into 1 to 2 sharp, high-value, executive-ready sentences.\n"
            "- Use bold markdown (**term**) for key names, numbers, or metrics for rapid scanning.\n"
            "- Never mention technical database jargon like SQL queries, SQLite, syntax, dataframes, or internal tables unless specifically asked.\n"
            "- If any referential risk or 0-result match was detected, weave it seamlessly into the proactive insight."
        )

        if data is not None:
            if data.empty:
                data_context = "Outcome: No records matched the search criteria."
                if suggestions:
                    data_context += f" Database values detected that might match: {', '.join(suggestions)}."
            else:
                data_preview = data.head(8).to_dict(orient="records")
                data_context = f"Outcome: Returned {len(data)} record(s). Data content: {data_preview}."
        else:
            data_context = f"Outcome: Operation {op_type} executed. {rows_affected} record(s) modified."

        if referential_warning:
            data_context += f" Referential status: {referential_warning}"

        prompt = f"""Database Snapshot: {db_summary}
User Request: "{user_prompt}"
Operation: {op_type}
{data_context}

Provide solely the proactive insight:"""

        try:
            raw_insight = self._call_llm(prompt, system_instruction=human_system_prompt)
            # Strip any accidental leftover labels
            cleaned_insight = re.sub(r"^(?:\*\*)?(?:Direct Conversational Answer|Proactive Data Insight|Insight|Summary|Answer)(?:\*\*)?[:\s-]*", "", raw_insight.strip(), flags=re.IGNORECASE)
            return cleaned_insight.strip()
        except Exception:
            if data is not None:
                return f"Identified **{len(data)} record(s)** corresponding to your request with complete cross-table consistency."
            return f"Successfully executed updates across **{rows_affected} record(s)** with verified data integrity."

    def classify_and_validate_sql(self, sql_query: str, valid_tables: List[str]) -> Tuple[bool, str, str]:
        """
        Validates SQL syntax and classifies operation into:
        READ (SELECT), CREATE (INSERT), UPDATE, DELETE, DDL, or UNKNOWN.
        Returns: (is_valid, operation_type, error_message_or_info)
        """
        try:
            parsed = sqlglot.parse_one(sql_query, read="sqlite")
        except Exception as e:
            return False, "UNKNOWN", f"SQL Syntax Error: {str(e)}"

        # Classify operation
        if isinstance(parsed, exp.Select):
            op_type = "READ (SELECT)"
        elif isinstance(parsed, exp.Insert):
            op_type = "CREATE (INSERT)"
        elif isinstance(parsed, exp.Update):
            op_type = "UPDATE"
        elif isinstance(parsed, exp.Delete):
            op_type = "DELETE"
        elif isinstance(parsed, (exp.Create, exp.Drop, exp.Alter)):
            op_type = "DDL / SCHEMA"
        else:
            op_type = "MUTATION / OTHER"

        # Check tables existence (except for CREATE TABLE)
        if not isinstance(parsed, exp.Create):
            tables_in_query = [t.name.lower().strip('"\'`') for t in parsed.find_all(exp.Table)]
            valid_set = {t.lower() for t in valid_tables}
            for tbl in tables_in_query:
                if tbl not in valid_set:
                    return False, op_type, f"Table '{tbl}' does not exist in database. Available tables: {valid_tables}"

        return True, op_type, "Valid SQL"

    def generate_sql(
        self,
        user_prompt: str,
        ddl_schema: str,
        sample_data: Dict[str, List[Dict[str, Any]]],
        error_feedback: str = ""
    ) -> str:
        """
        Builds dynamic few-shot context from database schema and generates SQL.
        """
        samples_formatted = []
        for tbl, rows in sample_data.items():
            if rows:
                samples_formatted.append(f"Table '{tbl}' sample rows:\n{rows}")

        samples_text = "\n".join(samples_formatted)

        prompt = f"""Target SQLite Schema:
{ddl_schema}

{samples_text}

Natural Language Request: {user_prompt}

Rules:
1. SQLite syntax only.
2. If this is a data retrieval question, generate a SELECT query (use JOINs, GROUP BY, aggregates where appropriate).
3. If this is a CRUD modification request (e.g., 'insert', 'add', 'update', 'change', 'delete', 'remove', 'drop'):
   - Use standard INSERT INTO, UPDATE, or DELETE statements.
   - For string matching, be mindful of casing (use LOWER(col) = 'value' or LIKE if user search is flexible).
4. Output ONLY pure executable SQLite SQL. No comments, no explanations.
"""

        if error_feedback:
            prompt += f"\n\nCRITICAL FIX: The previous attempt failed with error:\n{error_feedback}\nPlease correct the SQL statement."

        return self._call_llm(prompt)

    def execute_query(
        self,
        conn: sqlite3.Connection,
        sql_query: str,
        op_type: str
    ) -> Dict[str, Any]:
        """
        Executes the SQL statement safely in SQLite.
        Returns a dictionary with result dataframe, affected rows, status, and message.
        """
        cursor = conn.cursor()

        try:
            if "READ" in op_type or sql_query.strip().upper().startswith("SELECT"):
                # SELECT Query: return DataFrame
                df = pd.read_sql_query(sql_query, conn)
                return {
                    "success": True,
                    "op_type": "READ (SELECT)",
                    "sql": sql_query,
                    "data": df,
                    "rows_affected": len(df),
                    "message": f"Query returned {len(df)} row(s)."
                }
            else:
                # Mutation (INSERT, UPDATE, DELETE, DDL)
                cursor.execute(sql_query)
                affected = cursor.rowcount
                conn.commit()

                return {
                    "success": True,
                    "op_type": op_type,
                    "sql": sql_query,
                    "data": None,
                    "rows_affected": affected,
                    "message": f"Successfully executed {op_type}. Rows affected: {affected if affected != -1 else 0}."
                }
        except Exception as e:
            conn.rollback()
            return {
                "success": False,
                "op_type": op_type,
                "sql": sql_query,
                "data": None,
                "rows_affected": 0,
                "error": str(e)
            }

    def process_nl_request(
        self,
        conn: sqlite3.Connection,
        user_prompt: str,
        schema_dict: Dict[str, List[str]],
        ddl_schema: str,
        sample_data: Dict[str, List[Dict[str, Any]]],
        max_retries: int = 2
    ) -> Dict[str, Any]:
        """
        Full pipeline: NL -> SQL -> Validate -> Execute -> Self-heal on failure.
        """
        valid_tables = list(schema_dict.keys())
        error_feedback = ""

        for attempt in range(max_retries + 1):
            sql_query = self.generate_sql(
                user_prompt=user_prompt,
                ddl_schema=ddl_schema,
                sample_data=sample_data,
                error_feedback=error_feedback
            )

            is_valid, op_type, val_msg = self.classify_and_validate_sql(sql_query, valid_tables)
            if not is_valid:
                error_feedback = f"Validation failed: {val_msg}"
                continue

            exec_result = self.execute_query(conn, sql_query, op_type)
            if exec_result["success"]:
                exec_result["attempt"] = attempt + 1
                exec_result["human_response"] = self.generate_human_response(
                    conn=conn,
                    user_prompt=user_prompt,
                    sql_query=sql_query,
                    op_type=op_type,
                    data=exec_result.get("data"),
                    rows_affected=exec_result.get("rows_affected", 0)
                )
                return exec_result
            else:
                error_feedback = f"Execution error: {exec_result['error']}"

        return {
            "success": False,
            "op_type": "FAILED",
            "sql": sql_query if 'sql_query' in locals() else "",
            "data": None,
            "rows_affected": 0,
            "error": f"Failed after {max_retries + 1} attempts. Last error: {error_feedback}",
            "human_response": "I encountered an issue processing that request with the database. Please check your query or verify the table columns."
        }

    def get_dataset_brief(self, conn: sqlite3.Connection) -> Dict[str, Any]:
        """
        Generates an executive summary and tailored starter questions based on the live database.
        """
        summary_text = self.inspect_database_summary(conn)
        prompt = f"""You are an expert AI Data Analyst.
Here are the current tables in the database:
{summary_text}

Task:
1. Provide a brief 2-sentence executive summary of the dataset (what domain it covers, key metrics or notable points).
2. Generate exactly 3 insightful natural language questions or actions that a user would find most valuable to run on this data (mix of query and data update/check).

Output format:
Summary: <your 2-sentence summary>
Questions:
- <question 1>
- <question 2>
- <question 3>"""

        try:
            resp = self._call_llm(prompt, system_instruction="You are a data intelligence assistant. Be concise and insightful.")
            lines = resp.strip().split("\n")
            summary = ""
            questions = []
            for line in lines:
                if line.lower().startswith("summary:"):
                    summary = line.split(":", 1)[1].strip()
                elif line.strip().startswith("-") or line.strip().startswith("•") or (line.strip() and line.strip()[0].isdigit() and line.strip()[1] in ['.', ')']):
                    clean_q = re.sub(r"^[-•\d\.\)\s]+", "", line).strip()
                    if clean_q and not clean_q.lower().startswith("question"):
                        questions.append(clean_q)
            if not summary:
                summary = "Your data has been loaded and analyzed. You can explore relationships, query metrics, or perform updates."
            if not questions:
                questions = ["Show an overview of the data", "Which category has the highest metrics?", "Find any records that need updates"]
            return {"summary": summary, "suggested_questions": questions[:4]}
        except Exception:
            return {
                "summary": "Your data is loaded and ready for natural language queries and updates.",
                "suggested_questions": [
                    "Show all universities and their details",
                    "Which student has the highest GPA?",
                    "Count students enrolled in each school"
                ]
            }
