#!/usr/bin/env python3
"""
Анализатор SQL-запросов через DeepSeek.
Работает ТОЛЬКО с DeepSeek API.
"""

import json
import argparse
import os
import sys
import logging
from typing import Dict, List, Any

# Используем openai-клиент (DeepSeek совместим с OpenAI API)
import openai


# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)


class DeepSeekAnalyzer:
    def __init__(self, api_key: str = None):
        # self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")

        if not self.api_key:
            logger.error("❌ Не задан KEY в переменных окружения!")
            raise ValueError("API ключ  не найден")

        self.client = openai.OpenAI(
            api_key="free",
            base_url="https://openrouter.ai/api/v1"
        )
        self.model = "google/gemini-flash-1.5-8b"  # Бесплатная модель

    def _build_prompt(self, query_data: Dict[str, Any]) -> str:
        """Формируем промпт для DeepSeek"""
        explain_output = ' '.join(query_data.get('explain_output', [])) if query_data.get('explain_output') else 'N/A'
        tables = ', '.join(query_data.get('tables', [])) if query_data.get('tables') else 'N/A'

        return f"""
Проанализируй SQL-запрос и его EXPLAIN ANALYZE вывод по следующим критериям:

Критерии оценки:
1. Идеальный (GOOD): 
   - Использует индексы эффективно
   - Время выполнения < 50ms
   - Нет seq_scan для больших таблиц
   - Оптимальное использование памяти

2. Приемлемый (ACCEPTABLE):
   - Работает, но есть потенциальные проблемы
   - Seq scan на таблицах < 10k строк
   - Возможны улучшения для роста данных
   - Время выполнения < 200ms

3. Требует улучшения (NEEDS_IMPROVEMENT):
   - Seq scan на больших таблицах
   - Отсутствие индексов для JOIN/WHERE
   - Время выполнения > 500ms
   - Высокое использование CPU

4. Критический (CRITICAL):
   - DROP/DELETE без WHERE
   - Полное сканирование таблиц > 1M строк
   - Время выполнения > 2s
   - Блокировки транзакций

Запрос: 
{query_data['query']}

EXPLAIN ANALYZE вывод:
{explain_output}

Таблицы: {tables}
Тип запроса: {query_data['type']}

Ответ должен быть в строгом JSON формате:
{{
  "evaluation": "GOOD|ACCEPTABLE|NEEDS_IMPROVEMENT|CRITICAL",
  "severity": "LOW|MEDIUM|HIGH|CRITICAL",
  "execution_time": "время_выполнения",
  "issues": ["проблема1", "проблема2"],
  "recommendations": ["рекомендация1", "рекомендация2"]
}}
"""

    def analyze_query(self, query_data: Dict[str, Any]) -> Dict[str, Any]:
        """Отправляет запрос в DeepSeek и возвращает анализ"""
        prompt = self._build_prompt(query_data)

        try:
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=500
            )
            content = response.choices[0].message.content.strip()
            return json.loads(content)
        except Exception as e:
            logger.error(f"❌ Ошибка при вызове DeepSeek: {e}")
            return {
                "evaluation": "ошибка_анализа",
                "severity": "HIGH",
                "issues": [f"Не удалось проанализировать: {str(e)}"],
                "recommendations": ["Проверьте корректность SQL и подключение к API"]
            }


def generate_report(results_file: str, analyzer: DeepSeekAnalyzer) -> List[Dict]:
    """Читает результаты EXPLAIN и генерирует отчёт"""
    try:
        with open(results_file, 'r', encoding='utf-8') as f:
            results = json.load(f)
    except Exception as e:
        logger.error(f"❌ Не удалось прочитать {results_file}: {e}")
        sys.exit(1)

    report = []
    for item in results:
        if item.get('error'):
            analysis = {
                "evaluation": "CRITICAL",
                "severity": "CRITICAL",
                "issues": [f"Ошибка выполнения: {item['error']}"],
                "recommendations": ["Исправьте синтаксис SQL"]
            }
        else:
            analysis = analyzer.analyze_query(item)

        report.append({
            "query": item["query"],
            "type": item["type"],
            "tables": item.get("tables", []),
            "file_path": item.get("file_path", "unknown"),
            "analysis": analysis
        })

    return report


def check_deployment_criteria(report: List[Dict]) -> bool:
    """Проверяет, можно ли разрешить деплой"""
    critical_count = 0
    improvable_count = 0
    total = len(report)

    if total == 0:
        print("⚠️ Нет SQL-запросов для анализа!")
        return False

    for item in report:
        eval = item["analysis"]["evaluation"]
        if eval == "CRITICAL":
            critical_count += 1
        if eval in ["NEEDS_IMPROVEMENT", "CRITICAL"]:
            improvable_count += 1

    print(f"\n📊 Результаты анализа:")
    print(f"- Всего запросов: {total}")
    print(f"- Критических: {critical_count}")
    print(f"- Для улучшения: {improvable_count}/{total} ({improvable_count / total:.0%})")

    if critical_count > 0:
        print("❌ Обнаружены критические запросы! Деплой запрещён.")
        return False

    if improvable_count / total > 0.6:
        print("❌ Слишком много запросов требуют улучшения (>60%). Деплой запрещён.")
        return False

    print("✅ Все запросы в порядке. Деплой разрешён.")
    return True


def main():
    parser = argparse.ArgumentParser(description='SQL анализатор через DeepSeek')
    parser.add_argument('--results', default='explain_results.json', help='Входной файл с EXPLAIN ANALYZE')
    parser.add_argument('--report', default='llm_report.json', help='Выходной файл отчёта')
    args = parser.parse_args()

    # Инициализация анализатора
    try:
        analyzer = DeepSeekAnalyzer()
    except ValueError as e:
        logger.error(e)
        sys.exit(1)

    # Генерация отчёта
    report = generate_report(args.results, analyzer)

    # Сохранение отчёта
    try:
        with open(args.report, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        logger.info(f"✅ Отчёт сохранён: {args.report}")
    except Exception as e:
        logger.error(f"❌ Не удалось сохранить отчёт: {e}")
        sys.exit(1)

    # Проверка правил деплоя
    if not check_deployment_criteria(report):
        sys.exit(1)

    sys.exit(0)


if __name__ == '__main__':
    main()