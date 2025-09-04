import re
import os
from pathlib import Path
from datetime import datetime

def normalize_sql_query(raw_query):
    """
    Простая замена только параметров, без сложной логики
    """
    # Только базовые замены параметров
    replacements = [
        (r'\$(\d+)', '1'),        # $1, $2 → 1
        (r'\?', '1'),             # ? → 1
        (r':\w+', '1'),           # :param → 1
    ]
    
    normalized = raw_query
    for pattern, replacement in replacements:
        normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)
    
    return normalized

def is_valid_sql_query(query):
    """
    Проверяет, выглядит ли запрос как валидный SQL
    """
    # Минимальная длина для валидного запроса
    if len(query) < 10:
        return False
    
    # Должен содержать ключевые SQL-слова
    sql_keywords = ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER', 'DROP', 'FROM', 'WHERE', 'INTO', 'VALUES', 'SET']
    if not any(keyword in query.upper() for keyword in sql_keywords):
        return False
    
    # Не должен быть комментарием или обрывком
    invalid_patterns = [
        r'^--',      # Комментарии
        r'^\/\*',    # Блок комментариев
        r'^\.',      # Точки (обрывки)
        r'^\,',      # Запятые
        r'^\)',      # Закрывающие скобки
    ]
    
    for pattern in invalid_patterns:
        if re.match(pattern, query.strip()):
            return False
    
    return True

def find_sql_queries():
    print("Starting advanced SQL query scanner...")
    
    # Улучшенные паттерны для разных типов SQL
    sql_patterns = {
        'SELECT': re.compile(r'SELECT\s+.+?FROM\s+.+?(?:WHERE\s+.+?)?(?:LIMIT\s+.+?)?(?:OFFSET\s+.+?)?;?', re.IGNORECASE | re.DOTALL),
        'INSERT': re.compile(r'INSERT\s+INTO\s+.+?VALUES\s*\(.+?\);?', re.IGNORECASE | re.DOTALL),
        'UPDATE': re.compile(r'UPDATE\s+.+?SET\s+.+?(?:WHERE\s+.+?)?;?', re.IGNORECASE | re.DOTALL),
        'DELETE': re.compile(r'DELETE\s+FROM\s+.+?(?:WHERE\s+.+?)?;?', re.IGNORECASE | re.DOTALL),
        'CREATE': re.compile(r'CREATE\s+(?:TABLE|INDEX|VIEW)\s+.+?;?', re.IGNORECASE | re.DOTALL),
        'ALTER': re.compile(r'ALTER\s+TABLE\s+.+?;?', re.IGNORECASE | re.DOTALL)
    }
    
    found_queries = []
    
    # Ищем во всех файлах проекта
    for root, dirs, files in os.walk('.'):
        for file in files:
            # Ищем только в исходных файлах кода
            if file.endswith(('.go', '.java', '.py', '.js', '.ts', '.php', '.rb')):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        
                        for query_type, pattern in sql_patterns.items():
                            matches = pattern.findall(content)
                            for match in matches:
                                clean_query = match.strip()
                                
                                # Проверяем валидность запроса
                                if is_valid_sql_query(clean_query):
                                    # Нормализуем запрос (заменяем параметры)
                                    normalized_query = normalize_sql_query(clean_query)
                                    
                                    found_queries.append({
                                        'file': filepath,
                                        'type': query_type,
                                        'original': clean_query,
                                        'normalized': normalized_query
                                    })
                                    
                except Exception as e:
                    print(f"Error reading {filepath}: {e}")
    
    # Записываем в файл
    with open('found_queries.sql', 'w', encoding='utf-8') as f:
        f.write(f"-- Found {len(found_queries)} valid SQL queries on {datetime.now()}\n\n")
        
        for i, query in enumerate(found_queries, 1):
            f.write(f"-- Query #{i}: {query['file']} ({query['type']})\n")
            f.write(f"-- Original: {query['original']}\n")
            f.write(f"{query['normalized']}\n\n")
    
    print(f"Found {len(found_queries)} valid SQL queries in code")
    print("Results saved to found_queries.sql")

if __name__ == "__main__":
    find_sql_queries()