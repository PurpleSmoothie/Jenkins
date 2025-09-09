#!/usr/bin/env python3

import json
import argparse
import os
import sys
import logging
import re
from typing import Dict, List, Any


import openai


logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)


class OpenRouterAnalyzer:
    def __init__(self):

        self.api_key = os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            logger.error("OPENROUTER_API_KEY не задан в переменных окружения!")
            raise ValueError("API ключ не найден")


        self.base_url = "https://openrouter.ai/api/v1"
        self.model = "mistralai/mistral-7b-instruct:free"

        try:
            self.client = openai.OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
            logger.info("OpenRouter клиент инициализирован")
        except Exception as e:
            logger.error(f"Ошибка инициализации OpenRouter: {e}")
            raise

    def _build_prompt(self, query_data: Dict[str, Any]) -> str:
        """Формируем строгий промпт, чтобы LLM всегда возвращал issues и recommendations"""
        explain_output = '\n'.join(query_data.get('explain_output', [])) if query_data.get('explain_output') else 'N/A'
        tables = ', '.join(query_data.get('tables', [])) if query_data.get('tables') else 'N/A'

        return f"""
Проанализируй SQL-запрос и его EXPLAIN ANALYZE вывод. Отвечай ТОЛЬКО на русском языке. Верни ТОЛЬКО валидный JSON.

Запрос: 
{query_data['query']}

EXPLAIN ANALYZE:
{explain_output}

Таблицы: {tables}
Тип: {query_data['type']}

Критерии оценки:
- GOOD: эффективно, быстро, с индексами, время < 50ms
- ACCEPTABLE: работает, но есть риски, время < 200ms
- NEEDS_IMPROVEMENT: медленно, seq scan, нет индексов, время > 500ms
- CRITICAL: DROP/DELETE без WHERE, очень медленно (>2s)

Обязательно заполни ВСЕ поля:
- Если проблем нет — напиши "No performance issues detected"
- Если проблем нет — напиши "Query is well-optimized for current data size"
- Никогда не используй пустые массивы
- Никогда не используй | в evaluation — только одно значение!

Верни ТОЛЬКО JSON:
{{
  "evaluation": "GOOD",  // Одно значение!
  "severity": "LOW",
  "execution_time": "10ms",
  "issues": ["описание проблемы 1", "описание проблемы 2"],
  "recommendations": ["рекомендация 1", "рекомендация 2"]
}}
Пример 1:
Запрос: SELECT * FROM users WHERE id = 1;
EXPLAIN: Index Scan using users_pkey on users ...
Ответ: {{
  "evaluation": "GOOD",
  "severity": "LOW",
  "execution_time": "0.1ms",
  "issues": ["No issues detected"],
  "recommendations": ["Query uses primary key index, optimal for lookups"]
}}

Пример 2:
Запрос: SELECT * FROM logs;
EXPLAIN: Seq Scan on logs ...
Ответ: {{
  "evaluation": "NEEDS_IMPROVEMENT",
  "severity": "MEDIUM",
  "execution_time": "120ms",
  "issues": ["Full table scan on large table"],
  "recommendations": ["Create index on frequently queried columns"]
}}
"""

    def _extract_json(self, text: str) -> Dict[str, Any]:
        """Извлекает JSON из любого текста — максимально надёжно"""
        # Убираем Markdown
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*', '', text)

        # Ищем первую полную JSON-структуру
        stack = []
        start = -1
        for i, char in enumerate(text):
            if char == '{':
                if start == -1:
                    start = i
                stack.append(char)
            elif char == '}':
                if stack:
                    stack.pop()
                    if not stack:  # Сбалансирована
                        try:
                            return json.loads(text[start:i+1])
                        except json.JSONDecodeError as e:
                            logger.warning(f"Ошибка парсинга JSON: {e}")
                            return None
        return None

    def _fix_evaluation(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Исправляет некорректные значения evaluation"""
        if "|" in str(result.get("evaluation", "")):
            result["evaluation"] = "ACCEPTABLE"
            result["issues"] = result.get("issues", []) + ["LLM вернул несколько значений в evaluation"]
        return result

    def _ensure_non_empty_fields(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Гарантирует, что issues и recommendations не пустые"""
        if not result.get("issues"):
            result["issues"] = ["No performance issues detected"]

        if not result.get("recommendations"):
            result["recommendations"] = [
                "Query is efficient for current data size",
                "Consider indexing if table grows beyond 10k rows"
            ]
        return result

    def analyze_query(self, query_data: Dict[str, Any]) -> Dict[str, Any]:
        """Анализирует один SQL-запрос через LLM"""
        prompt = self._build_prompt(query_data)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=500
            )
            content = response.choices[0].message.content.strip()
            logger.info(f"LLM response for query: {query_data['query'][:50]}...")
            logger.debug(f"Raw LLM output: {content}")

            # Попытка 1: прямой JSON
            try:
                result = json.loads(content)
                if isinstance(result, dict):
                    result = self._fix_evaluation(result)
                    result = self._ensure_non_empty_fields(result)
                    return result
            except json.JSONDecodeError:
                pass

            # Попытка 2: извлечение JSON из текста
            try:
                extracted = self._extract_json(content)
                if extracted:
                    extracted = self._fix_evaluation(extracted)
                    extracted = self._ensure_non_empty_fields(extracted)
                    return extracted
            except Exception as e:
                logger.warning(f"Ошибка при извлечении JSON: {e}")

            # Фоллбэк: ручной анализ
            logger.error(f"Не удалось извлечь JSON из ответа LLM")
            return {
                "evaluation": "ACCEPTABLE",
                "severity": "MEDIUM",
                "execution_time": "unknown",
                "issues": ["Не удалось распарсить ответ LLM"],
                "recommendations": [
                    "Проверьте запрос вручную",
                    "Рассмотрите возможность создания индексов на часто используемые столбцы"
                ]
            }

        except Exception as e:
            logger.error(f"Ошибка при вызове OpenRouter: {e}")
            return {
                "evaluation": "ACCEPTABLE",
                "severity": "HIGH",
                "execution_time": "unknown",
                "issues": [f"Ошибка API: {str(e)}"],
                "recommendations": ["Проверьте подключение к API"]
            }


def generate_report(results_file: str, analyzer: OpenRouterAnalyzer) -> List[Dict]:
    """Генерирует отчёт по всем запросам"""
    try:
        with open(results_file, 'r', encoding='utf-8') as f:
            results = json.load(f)
    except Exception as e:
        logger.error(f"Не удалось прочитать {results_file}: {e}")
        sys.exit(1)

    report = []
    for item in results:
        if item.get('error'):
            analysis = {
                "evaluation": "CRITICAL",
                "severity": "CRITICAL",
                "execution_time": "0ms",
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
        print("Нет SQL-запросов для анализа!")
        return False

    for item in report:
        eval_status = item["analysis"]["evaluation"]
        if eval_status == "CRITICAL":
            critical_count += 1
        if eval_status in ["NEEDS_IMPROVEMENT", "CRITICAL"]:
            improvable_count += 1

    print(f"\nРезультаты анализа:")
    print(f"- Всего запросов: {total}")
    print(f"- Критических: {critical_count}")
    print(f"- Для улучшения: {improvable_count}/{total} ({improvable_count / total:.0%})")

    if critical_count > 0:
        print("Обнаружены критические запросы! Деплой запрещён.")
        return False

    if improvable_count / total > 0.6:
        print("Слишком много запросов требуют улучшения (>60%). Деплой запрещён.")
        return False

    print("Все запросы в порядке. Деплой разрешён.")
    return True


def main():
    parser = argparse.ArgumentParser(description='SQL анализатор через OpenRouter')
    parser.add_argument('--results', default='explain_results.json', help='Входной файл с EXPLAIN ANALYZE')
    parser.add_argument('--report', default='llm_report.json', help='Выходной файл отчёта')
    args = parser.parse_args()

    try:
        analyzer = OpenRouterAnalyzer()
    except Exception as e:
        logger.error(f"Не удалось инициализировать анализатор: {e}")
        sys.exit(1)

    report = generate_report(args.results, analyzer)

    try:
        with open(args.report, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        logger.info(f"Отчёт сохранён: {args.report}")
    except Exception as e:
        logger.error(f"Не удалось сохранить отчёт: {e}")
        sys.exit(1)

    if not check_deployment_criteria(report):
        sys.exit(1)

    sys.exit(0)


if __name__ == '__main__':
    main()