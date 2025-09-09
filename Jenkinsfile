pipeline {
    agent any

    environment {
        DB_HOST = '176.108.246.204'
        DB_PORT = '5432'
        DB_NAME = 'postgres'
        DB_USER = 'postgres'
        DB_PASSWORD = credentials('db_credentials')  
        OPENROUTER_API_KEY = credentials('llm_api_key') 
    }

    stages {
        stage('Checkout') {
            steps {
                git branch: 'main', url: 'https://github.com/PurpleSmoothie/Jenkins.git'
            }
        }

 stage('Validate Required Files') {
    steps {
        script {
            echo "=== ПРОВЕРКА НАЛИЧИЯ КРИТИЧЕСКИХ ФАЙЛОВ ==="
            def requiredFiles = [
                "sqlParse.py",
                "explainRunner.py",
                "LLM_aggregator.py"
            ]
            def missingFiles = []

            requiredFiles.each { file ->
                if (!fileExists(file)) {
                    echo "❌ Файл не найден: ${file}"
                    missingFiles.add(file)
                }
            }

            if (missingFiles.size() > 0) {
                error("❌ Критические файлы отсутствуют: ${missingFiles.join(', ')}. Остановка пайплайна.")
            }

            if (!fileExists("example.sql")) {
                echo "⚠️  Внимание: example.sql не найден — будет использован альтернативный путь или файл из параметров."
            } else {
                echo "✅ example.sql присутствует"
            }

            echo "✅ Все необходимые скрипты найдены. Продолжаем..."
        }
    }
}

        stage('Setup Virtual Environment') {
            steps {
                sh '''
                    echo "=== СОЗДАНИЕ ВИРТУАЛЬНОГО ОКРУЖЕНИЯ ==="
                    python3 -m venv /var/jenkins_home/venv --clear
                    echo "Виртуальное окружение создано"
                '''
            }
        }

        stage('Install Dependencies') {
            steps {
                sh '''
                    echo "=== УСТАНОВКА ЗАВИСИМОСТЕЙ ==="
                    /var/jenkins_home/venv/bin/pip install --upgrade pip
                    /var/jenkins_home/venv/bin/pip install psycopg2-binary sqlparse python-dotenv openai tenacity
                    echo "✅ Зависимости установлены"
                '''
            }
        }

        stage('Test DB Connection') {
            steps {
                sh '''
                    echo "=== ТЕСТ ПОДКЛЮЧЕНИЯ К БАЗЕ ДАННЫХ ==="
                    /var/jenkins_home/venv/bin/python -c "
import psycopg2
try:
    conn = psycopg2.connect(
        host='$DB_HOST',
        port='$DB_PORT',
        dbname='$DB_NAME',
        user='$DB_USER',
        password='$DB_PASSWORD'
    )
    print('✅ Подключение к PostgreSQL успешно!')
    conn.close()
except Exception as e:
    print(f'❌ Ошибка подключения: {e}')
    exit(1)
"
                '''
            }
        }

        stage('Parse SQL Files') {
            steps {
                sh '''
                    echo "=== ПАРСИНГ SQL-ФАЙЛОВ ==="
                    /var/jenkins_home/venv/bin/python sqlParse.py
                    QUERY_COUNT=$(cat parsed_queries.json | jq 'length' 2>/dev/null || echo 0)
                    echo "✅ Найдено SQL-запросов: ${QUERY_COUNT}"
                '''
            }
        }

        stage('Run EXPLAIN ANALYZE') {
            steps {
                sh '''
                    echo "=== ЗАПУСК EXPLAIN ANALYZE ==="
                    /var/jenkins_home/venv/bin/python explainRunner.py
                    RESULT_COUNT=$(cat explain_results.json | jq 'length' 2>/dev/null || echo 0)
                    echo "✅ Проанализировано запросов: ${RESULT_COUNT}"
                '''
            }
        }

        stage('LLM Analysis') {
            steps {
                sh '''
                    echo "=== АНАЛИЗ ЧЕРЕЗ LLM ==="
                    /var/jenkins_home/venv/bin/python LLM_aggregator.py --results explain_results.json --report llm_report.json
                    echo "✅ LLM-анализ завершён"
                '''
                
                sh '''
                    echo "=== КОНВЕРТАЦИЯ В HTML ==="
                    /var/jenkins_home/venv/bin/python report_converter.py llm_report.json final_result.html
                    ls -la
                '''
            }
        }

        stage('Review Results') {
            steps {
                sh '''
                    echo "=== ФИНАЛЬНЫЙ ОТЧЁТ ==="
                    echo "Артефакты:"
                    ls -la *.json *.html
        
                    echo ""
                    echo "--- СТАТИСТИКА ---"
                    python3 <<EOF
import json

try:
    report = json.load(open('llm_report.json', 'r', encoding='utf-8'))
    total = len(report)
    critical = sum(1 for r in report if r['analysis']['evaluation'] == 'CRITICAL')
    needs_improvement = sum(1 for r in report if r['analysis']['evaluation'] == 'NEEDS_IMPROVEMENT')
    errors = sum(1 for r in report if r.get('analysis', {}).get('issues', []) and 'Ошибка выполнения' in r['analysis']['issues'][0])

    print(f'📊 Всего запросов: {total}')
    print(f'🔴 Критические: {critical}')
    print(f'🟡 Требуют улучшения: {needs_improvement}')
    print(f'⛔ Ошибки выполнения: {errors}')
except Exception as e:
    print(f'❌ Ошибка при чтении отчёта: {e}')
    exit(1)
EOF
        '''
            }
        }
    }

    post {
        always {
            archiveArtifacts artifacts: 'final_result.html,parsed_queries.json,explain_results.json,llm_report.json', allowEmptyArchive: true
            echo "📎 Артефакты сохранены"
        }
        success {
            echo "✅ СБОРКА УСПЕШНА"
        }
        failure {
            echo "❌ СБОРКА НЕ УДАЛАСЬ"
        }
    }
}
