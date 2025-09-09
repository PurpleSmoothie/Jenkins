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


class OpenAIAnalyzer:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            logger.error("OPENAI_API_KEY не задан в переменных окружения!")
            raise ValueError("API ключ не найден")

        self.base_url = "https://api.openai.com/v1"
        self.model = "gpt-4o-mini"

        try:
            self.client = openai.OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
            logger.info("OpenAI клиент инициализирован")
        except Exception as e:
            logger.error(f"Ошибка инициализации OpenAI: {e}")
            raise

    def _build_prompt(self, query_data: Dict[str, Any]) -> str:
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

Обязательно заполни ВСЕ поля.
Верни ТОЛЬКО JSON:
{{
  "evaluation": "GOOD",
  "severity": "LOW",
  "execution_time": "10ms",
  "issues": ["описание проблемы 1"],
  "recommendations": ["рекомендация 1"]
}}
"""

    def _extract_json(self, text: str) -> Dict[str, Any]:
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*', '', text)

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
                    if not stack:
                        try:
                            return json.loads(text[start:i+1])
                        except json.JSONDecodeError as e:
                            logger.warning(f"Ошибка парсинга JSON: {e}")
                            return None
        return None

    def analyze_query(self, query_data: Dict[str, Any]) -> Dict[str, Any]:
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

            try:
                result = json.loads(content)
                if isinstance(result, dict):
                    return result
            except json.JSONDecodeError:
                extracted = self._extract_json(content)
                if extracted:
                    return extracted

            logger.error("Не удалось извлечь JSON из ответа LLM")
            return {
                "evaluation": "ACCEPTABLE",
                "severity": "MEDIUM",
                "execution_time": "unknown",
                "issues": ["Не удалось распарсить ответ LLM"],
                "recommendations": ["Проверьте запрос вручную"]
            }

        except Exception as e:
            logger.error(f"Ошибка при вызове OpenAI: {e}")
            return {
                "evaluation": "ACCEPTABLE",
                "severity": "HIGH",
                "execution_time": "unknown",
                "issues": [f"Ошибка API: {str(e)}"],
                "recommendations": ["Проверьте подключение к API"]
            }


def generate_report(results_file: str, analyzer: OpenAIAnalyzer) -> List[Dict]:
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
    parser = argparse.ArgumentParser(description='SQL анализатор через OpenAI')
    parser.add_argument('--results', default='explain_results.json', help='Входной файл с EXPLAIN ANALYZE')
    parser.add_argument('--report', default='llm_report.json', help='Выходной файл отчёта')
    args = parser.parse_args()

    try:
        analyzer = OpenAIAnalyzer()
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
