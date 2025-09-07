pipeline {
    agent any
    environment {
        DB_HOST = '176.108.246.204'
        DB_PORT = '5432'
        DB_NAME = 'your_database_name'
        DB_USER = credentials('db-user')
        DB_PASSWORD = credentials('db-password')
        OPENAI_API_KEY = credentials('openai-api-key')
    }
    stages {
        stage('Install Python and Tools') {
            steps {
                sh '''
                    echo "Устанавливаем Python3 и необходимые инструменты..."
                    apt-get update
                    apt-get install -y python3 python3-pip python3-venv
                    echo "Python3 установлен: $(python3 --version)"
                    echo "Создаем симлинк python -> python3..."
                    ln -sf $(which python3) /usr/local/bin/python || true
                    echo "Проверка: $(python --version)"
                '''
            }
        }
        
        stage('Install Dependencies') {
            steps {
                sh '''
                    echo "Устанавливаем зависимости Python..."
                    pip3 install psycopg2-binary sqlparse python-dotenv openai tenacity
                    echo "Зависимости установлены:"
                    pip3 list | grep -E "psycopg2|sqlparse|dotenv|openai|tenacity"
                '''
            }
        }
        
        stage('Parse SQL Files') {
            steps {
                sh '''
                    echo "Парсим SQL файлы..."
                    python sqlParse.py
                    echo "Парсинг завершен. Найдено запросов:"
                    grep -c '"query"' parsed_queries.json || echo "0"
                '''
            }
        }
        
        stage('Run EXPLAIN ANALYZE') {
            steps {
                sh '''
                    echo "Запускаем EXPLAIN ANALYZE..."
                    python explainRunner.py
                    echo "EXPLAIN ANALYZE завершен"
                '''
            }
        }
        
        stage('LLM Analysis') {
            steps {
                sh '''
                    echo "Запускаем LLM анализ..."
                    python LLM_aggregator.py --results explain_results.json --report llm_report.json
                    echo "LLM анализ завершен"
                '''
            }
        }
        
        stage('Generate Report') {
            steps {
                sh '''
                    echo "=== ФИНАЛЬНЫЙ ОТЧЕТ ==="
                    echo "Количество запросов: $(grep -c '"query"' parsed_queries.json)"
                    echo "Результаты анализа:"
                    python -c "
import json
with open('llm_report.json', 'r') as f:
    data = json.load(f)
    evaluations = [item['analysis']['evaluation'] for item in data]
    from collections import Counter
    counts = Counter(evaluations)
    for eval_type, count in counts.items():
        print(f'{eval_type}: {count}')
    "
                '''
            }
            post {
                always {
                    archiveArtifacts artifacts: '*.json', allowEmptyArchive: true
                }
            }
        }
    }
    
    post {
        always {
            sh '''
                echo "Очистка завершена"
            '''
        }
        success {
            echo "✅ Pipeline успешно завершен!"
        }
        failure {
            echo "❌ Pipeline завершился с ошибкой"
        }
    }
}