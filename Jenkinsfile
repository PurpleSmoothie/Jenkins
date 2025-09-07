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
        stage('Setup Python') {
            steps {
                sh '''
                    echo "Устанавливаем Python3 и pip..."
                    apt-get update
                    apt-get install -y python3 python3-pip python3-venv
                    echo "Python3 установлен: $(python3 --version)"
                    echo "Pip установлен: $(pip3 --version)"
                '''
            }
        }
        
        stage('Create Virtual Environment') {
            steps {
                sh '''
                    echo "Создаем виртуальное окружение..."
                    python3 -m venv venv
                    source venv/bin/activate
                    echo "Виртуальное окружение активировано"
                '''
            }
        }
        
        stage('Install Dependencies') {
            steps {
                sh '''
                    source venv/bin/activate
                    echo "Устанавливаем зависимости..."
                    pip3 install psycopg2-binary sqlparse python-dotenv openai tenacity
                    echo "Зависимости установлены"
                '''
            }
        }
        
        stage('Parse SQL Files') {
            steps {
                sh '''
                    source venv/bin/activate
                    echo "Парсим SQL файлы..."
                    python3 sqlParse.py ./project_sql
                    echo "Парсинг завершен. Найдено запросов:"
                    cat parsed_queries.json | grep -o '"query"' | wc -l
                '''
            }
        }
        
        stage('Run EXPLAIN ANALYZE') {
            steps {
                sh '''
                    source venv/bin/activate
                    echo "Запускаем EXPLAIN ANALYZE..."
                    python3 explainRunner.py
                    echo "EXPLAIN ANALYZE завершен"
                '''
            }
        }
        
        stage('LLM Analysis') {
            steps {
                sh '''
                    source venv/bin/activate
                    echo "Запускаем LLM анализ..."
                    python3 LLM_aggregator.py --results explain_results.json --report llm_report.json
                    echo "LLM анализ завершен"
                '''
            }
        }
        
        stage('Generate Report') {
            steps {
                sh '''
                    source venv/bin/activate
                    echo "Генерируем финальный отчет..."
                    echo "=== ОТЧЕТ АНАЛИЗА SQL ЗАПРОСОВ ==="
                    echo "Количество проанализированных запросов:"
                    jq length parsed_queries.json
                    echo ""
                    echo "Результаты LLM анализа:"
                    jq '.[].analysis.evaluation' llm_report.json | sort | uniq -c
                    echo ""
                    echo "Детальный отчет сохранен в llm_report.json"
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
                echo "Очистка виртуального окружения..."
                rm -rf venv || true
            '''
        }
        success {
            echo "Pipeline успешно завершен!"
        }
        failure {
            echo "Pipeline завершился с ошибкой"
        }
    }