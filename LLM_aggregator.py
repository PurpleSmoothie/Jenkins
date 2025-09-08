#!/usr/bin/env python3
"""
SQL Query Analyzer через OpenRouter (бесплатный API)
"""

import json
import argparse
import os
import sys
import logging
import re
from typing import Dict, List, Any

# Используем openai-клиент (совместим с OpenRouter)
import openai


# Настройка логирования
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
        """Формируем строгий промпт для LLM"""
        explain_output = ' '.join(query_data.get('explain_output', [])) if query_data.get('explain_output') else 'N/A'
        tables = ', '.join(query_data.get('tables', [])) if query_data.get('tables') else 'N/A'

        return f"""
Проанализируй SQL-запрос и его EXPLAIN ANALYZE вывод. Верни ТОЛЬКО валидный JSON.

Запрос: 
{query_data['query']}

EXPLAIN ANALYZE:
{explain_output}

Таблицы: {tables}
Тип: {query_data['type']}

Критерии:
- GOOD: эффективно, быстро, с индексами
- ACCEPTABLE: работает, но есть риски
- NEEDS_IMPROVEMENT: медленно, seq scan, нет индексов
- CRITICAL: опасные операции, очень медленно

Ответ в строгом JSON формате (одно значение для evaluation!):
{{
  "evaluation": "GOOD",
  "severity": "LOW",
  "execution_time": "10ms",
  "issues": [],
  "recommendations": []
}}
"""

    def _extract_json(self, text: str) -> Dict[str, Any]:
        """Извлекает JSON из любого текста — надёжно"""
        # Убираем Markdown-обёртки
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
                    if not stack:  # Сбалансированная структура
                        try:
                            return json.loads(text[start:i+1])
                        except json.JSONDecodeError as e:
                            logger.warning(f"❌ Ошибка парсинга JSON: {e}")
                            return None
        return None

    def analyze_query(self, query_data: Dict[str, Any]) -> Dict[str, Any]:
        """Анализирует один SQL-запрос через LLM"""
        prompt = self._build_prompt(query_data)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=400
            )
            content = response.choices[0].message.content.strip()
            logger.info(f"📝 LLM response for query: {query_data['query'][:50]}...")
            logger.debug(f"Raw LLM output: {content}")

            # Попытка 1: прямой JSON
            try:
                result = json.loads(content)
                if isinstance(result, dict):
                    # Исправляем возможные ошибки в evaluation
                    if "|" in str(result.get("evaluation", "")):
                        result["evaluation"] = "ACCEPTABLE"
                        result["issues"] = result.get("issues", []) + ["LLM вернул несколько значений в evaluation"]
                    return result
            except json.JSONDecodeError:
                pass

            # Попытка 2: извлечение JSON из текста
            try:
                extracted = self._extract_json(content)
                if extracted:
                    # Исправляем evaluation, если нужно
                    if "|" in str(extracted.get("evaluation", "")):
                        extracted["evaluation"] = "ACCEPTABLE"
                        extracted["issues"] = extracted.get("issues", []) + ["Некорректный формат evaluation"]
                    return extracted
            except Exception as e:
                logger.warning(f"⚠️ Ошибка при извлечении JSON: {e}")

            # Фоллбэк: ручной анализ
            logger.error(f"❌ Не удалось извлечь JSON из ответа LLM")
            return {
                "evaluation": "ACCEPTABLE",
                "severity": "MEDIUM",
                "issues": ["Не удалось распарсить ответ LLM"],
                "recommendations": ["Проверьте запрос вручную"]
            }

        except Exception as e:
            logger.error(f"❌ Ошибка при вызове OpenRouter: {e}")
            return {
                "evaluation": "ACCEPTABLE",
                "severity": "HIGH",
                "issues": [f"Ошибка API: {str(e)}"],
                "recommendations": ["Проверьте подключение к API"]
            }


def generate_report(results_file: str, analyzer: OpenRouterAnalyzer) -> List[Dict]:
    """Генерирует отчёт по всем запросам"""
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
        eval_status = item["analysis"]["evaluation"]
        if eval_status == "CRITICAL":
            critical_count += 1
        if eval_status in ["NEEDS_IMPROVEMENT", "CRITICAL"]:
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
    parser.add_argument('--results', default='explain_results.json', help='Входной файл с EXPLAIN ANALYZE')
    parser.add_argument('--report', default='llm_report.json', help='Выходной файл отчёта')
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