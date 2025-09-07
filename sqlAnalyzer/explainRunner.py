import json
import psycopg2
from psycopg2 import sql
import os
from dotenv import load_dotenv

load_dotenv()

def run_explain_analyze():
    # Подключение к тестовой БД
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "db"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )
    conn.autocommit = False
    cursor = conn.cursor()

    # Загружаем запросы
    with open('parsed_queries.json', 'r') as f:
        queries = json.load(f)

    results = []
    for query_obj in queries:
        query = query_obj["query"]
        try:
            cursor.execute("BEGIN;")  # Начинаем транзакцию
            explain_query = sql.SQL("EXPLAIN (ANALYZE, VERBOSE, COSTS, BUFFERS) {}").format(
                sql.SQL(query)
            )
            cursor.execute(explain_query)
            explain_result = "\n".join([str(row) for row in cursor.fetchall()])

            results.append({
                "query": query,
                "type": query_obj["type"],
                "explain_output": explain_result
            })
            cursor.execute("ROLLBACK;")  # Откатываем изменения
        except Exception as e:
            cursor.execute("ROLLBACK;")
            print(f"Error analyzing query: {query}\n{str(e)}")

    conn.close()

    # Сохраняем результаты
    with open('explain_results.json', 'w') as f:
        json.dump(results, f, indent=2)

    print(f"Analyzed {len(results)} queries. Results saved to explain_results.json")


if __name__ == "__main__":
    run_explain_analyze()