#!/usr/bin/env python3

import json
import argparse
import os
import sys
import logging
from typing import Dict, List, Any

import openai


logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)


class OpenRouterAnalyzer:
    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY не задан")
        self.base_url = "https://openrouter.ai/api/v1"
        self.model = "mistralai/mistral-7b-instruct:free"  # Бесплатная модель

        try:
            self.client = openai.OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
            logger.info("✅ OpenRouter клиент инициализирован")
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации OpenRouter: {e}")
            raise

    def _build_prompt(self, query_data: Dict[str, Any]) -> str:
        explain_output = ' '.join(query_data.get('explain_output', [])) if query_data.get('explain_output') else 'N/A'
        tables = ', '.join(query_data.get('tables', [])) if query_data.get('tables') else 'N/A'

        return f"""
Проанализируй SQL-запрос и его EXPLAIN ANALYZE вывод.

Запрос: 
{query_data['query']}

EXPLAIN ANALYZE вывод:
{explain_output}

Таблицы: {tables}
Тип запроса: {query_data['type']}

Оцени по критериям:
- GOOD: эффективно, быстро, с индексами
- ACCEPTABLE: работает, но есть риски
- NEEDS_IMPROVEMENT: медленно, seq scan, нет индексов
- CRITICAL: опасные операции, очень медленно

Ответ в JSON:
{{
  "evaluation": "GOOD|ACCEPTABLE|NEEDS_IMPROVEMENT|CRITICAL",
  "severity": "LOW|MEDIUM|HIGH|CRITICAL",
  "execution_time": "время",
  "issues": ["список проблем"],
  "recommendations": ["рекомендации"]
}}
"""

    def analyze_query(self, query_data: Dict[str, Any]) -> Dict[str, Any]:
        prompt = self._build_prompt(query_data)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=400
            )
            content = response.choices[0].message.content.strip()

            # Часто LLM возвращает просто JSON без обёртки
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                # Если не JSON — попробуем извлечь
                import re
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
                else:
                    raise ValueError("Не удалось извлечь JSON")

        except Exception as e:
            logger.error(f"❌ Ошибка при вызове OpenRouter: {e}")
            return {
                "evaluation": "ACCEPTABLE",
                "severity": "MEDIUM",
                "issues": [f"Ошибка анализа: {str(e)}"],
                "recommendations": ["Проверьте запрос вручную"]
            }


def generate_report(results_file: str, analyzer: OpenRouterAnalyzer) -> List[Dict]:
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
    parser = argparse.ArgumentParser(description='SQL анализатор через OpenRouter')
    parser.add_argument('--results', default='explain_results.json', help='Файл с EXPLAIN ANALYZE')
    parser.add_argument('--report', default='llm_report.json', help='Выходной отчёт')
    args = parser.parse_args()

    try:
        analyzer = OpenRouterAnalyzer()
    except Exception as e:
        logger.error(f"❌ Не удалось инициализировать анализатор: {e}")
        sys.exit(1)

    report = generate_report(args.results, analyzer)

    try:
        with open(args.report, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        logger.info(f"✅ Отчёт сохранён: {args.report}")
    except Exception as e:
        logger.error(f"❌ Не удалось сохранить отчёт: {e}")
        sys.exit(1)

    if not check_deployment_criteria(report):
        sys.exit(1)

    sys.exit(0)


if __name__ == '__main__':
    main()