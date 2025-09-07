import json
import argparse
import os
import sys
import openai
from tenacity import retry, stop_after_attempt, wait_exponential


class LLMAnalyzer:
    def __init__(self):
        self.client = openai.OpenAI(
            api_key=os.getenv("OPENAI_API_KEY", ""),
            base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
        )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def analyze_query(self, query_data):
        """Анализирует запрос через LLM с повторными попытками"""
        prompt = self._build_prompt(query_data)

        try:
            response = self.client.chat.completions.create(
                model="gpt-4-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=500
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            print(f"Ошибка LLM: {str(e)}")
            return {
                "evaluation": "ошибка_анализа",
                "severity": "HIGH",
                "recommendations": ["Не удалось проанализировать через LLM"]
            }

    def _build_prompt(self, query_data):
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


def generate_report(results):
    analyzer = LLMAnalyzer()
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
            "tables": item["tables"],
            "file_path": item["file_path"],
            "analysis": analysis
        })

    return report


def check_jenkins_criteria(report):
    critical_count = 0
    improvable_count = 0
    total = len(report)

    # Если нет запросов для анализа
    if total == 0:
        print("⚠️ Нет запросов для анализа!")
        return False

    for item in report:
        eval = item["analysis"]["evaluation"]
        if eval in ["CRITICAL"]:
            critical_count += 1
        if eval in ["NEEDS_IMPROVEMENT", "CRITICAL"]:
            improvable_count += 1

    print(f"\n📊 Результаты анализа:")
    print(f"- Всего запросов: {total}")
    print(f"- Критических запросов: {critical_count}")
    print(f"- Запросов для улучшения: {improvable_count}/{total} ({improvable_count / total:.0%})")

    if critical_count > 0:
        print("❌ Обнаружены критические запросы! Запрещаю деплой.")
        return False

    if improvable_count / total > 0.6:
        print("❌ Слишком много запросов требуют улучшения (>60%). Запрещаю деплой.")
        return False

    print("✅ Все запросы соответствуют стандартам. Разрешаю деплой.")
    return True


def main():
    parser = argparse.ArgumentParser(description='LLM Query Analyzer')
    parser.add_argument('--results', default='explain_results.json', help='Input EXPLAIN results')
    parser.add_argument('--report', default='llm_report.json', help='Output report file')
    args = parser.parse_args()

    with open(args.results, 'r', encoding='utf-8') as f:
        results = json.load(f)

    report = generate_report(results)

    with open(args.report, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    if not check_jenkins_criteria(report):
        sys.exit(1)

    sys.exit(0)


if __name__ == '__main__':
    main()