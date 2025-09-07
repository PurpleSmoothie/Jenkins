pipeline {
    agent any
    stages {
        stage('Check Python') {
            steps {
                sh '''
                    # Проверяем что есть
                    echo "Доступные версии Python:"
                    ls /usr/bin/python* 2>/dev/null || echo "Python не найден"
                    
                    # Если python3 есть, используем его
                    if command -v python3 &> /dev/null; then
                        echo "Python3 найден: $(python3 --version)"
                        ln -s $(which python3) /usr/local/bin/python || true
                    else
                        echo "Устанавливаем Python3..."
                        apt-get update
                        apt-get install -y python3 python3-pip
                    fi
                    
                    echo "Python готов: $(python --version || python3 --version)"
                '''
            }
        }
        
        stage('Analyze SQL') {
            steps {
                sh '''
                    echo "Подключаемся к внешней БД: 176.108.246.204:5432"
                    python3 sqlParse.py
                '''
            }
        }
    }
}