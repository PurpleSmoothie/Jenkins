import os
import sqlparse
import json
import sys
from sqlparse.tokens import Comment, Whitespace


def parse_sql_files(directory):
    queries = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.sql'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        sql = f.read()
                except UnicodeDecodeError:
                    try:
                        with open(filepath, 'r', encoding='cp1251') as f:
                            sql = f.read()
                    except UnicodeDecodeError:
                        with open(filepath, 'r', encoding='latin-1') as f:
                            sql = f.read()

                statements = sqlparse.parse(sql)
                for stmt in statements:
                    # Получаем чистый текст запроса без комментариев
                    clean_query = get_clean_query(stmt)

                    # Проверяем, что это не пустая строка и не только комментарий
                    if clean_query and not clean_query.isspace():
                        # Определяем тип запроса
                        stmt_type = get_query_type(stmt)

                        queries.append({
                            "query": clean_query,
                            "type": stmt_type,
                            "file_path": filepath
                        })
    return queries


def get_clean_query(statement):
    """Возвращает SQL-запрос без комментариев"""
    clean_tokens = []
    for token in statement.tokens:
        if token.ttype not in (Comment,):
            # Сохраняем все токены, кроме комментариев
            clean_tokens.append(token)

    # Собираем чистый запрос
    clean_query = ''.join(str(token) for token in clean_tokens).strip()
    return clean_query


def get_query_type(statement):
    """Определяет тип SQL-запроса по первому ключевому слову"""
    # Ищем первое ключевое слово, игнорируя комментарии и пробелы
    for token in statement.tokens:
        if (token.ttype not in (Comment, Whitespace) and
                token.value.strip() and
                token.value.upper() in ['SELECT', 'INSERT', 'UPDATE', 'DELETE',
                                        'CREATE', 'DROP', 'ALTER', 'TRUNCATE', 'WITH',
                                        'EXPLAIN', 'BEGIN', 'COMMIT', 'ROLLBACK']):
            return token.value.upper().strip()

    # Если не нашли стандартное ключевое слово, анализируем содержимое
    clean_query = get_clean_query(statement).upper()

    # Проверяем различные паттерны SQL-запросов
    if clean_query.startswith(('SELECT', 'WITH')):
        return 'SELECT'
    elif clean_query.startswith('INSERT'):
        return 'INSERT'
    elif clean_query.startswith('UPDATE'):
        return 'UPDATE'
    elif clean_query.startswith('DELETE'):
        return 'DELETE'
    elif clean_query.startswith('CREATE'):
        return 'CREATE'
    elif clean_query.startswith('DROP'):
        return 'DROP'
    elif clean_query.startswith('ALTER'):
        return 'ALTER'
    elif clean_query.startswith('TRUNCATE'):
        return 'TRUNCATE'
    elif clean_query.startswith(('BEGIN', 'START TRANSACTION')):
        return 'BEGIN'
    elif clean_query.startswith('COMMIT'):
        return 'COMMIT'
    elif clean_query.startswith('ROLLBACK'):
        return 'ROLLBACK'

    return 'UNKNOWN'


if __name__ == "__main__":
    project_dir = sys.argv[1] if len(sys.argv) > 1 else '.'
    queries = parse_sql_files(project_dir)

    with open('parsed_queries.json', 'w', encoding='utf-8') as f:
        json.dump(queries, f, indent=2, ensure_ascii=False)

    print(f"Found {len(queries)} SQL queries. Saved to parsed_queries.json")