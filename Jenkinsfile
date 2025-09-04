pipeline {
    agent any
    stages {
        stage('Checkout') {
            steps { 
                git branch: 'main', 
                url: 'https://github.com/PurpleSmoothie/Jenkins.git',
                credentialsId: 'b395780c-f5db-4f07-b20f-0abea15002ca'
            }
        }
        
        stage('Find SQL Queries') {
            steps {
                script {
                    if (isUnix()) {
                        sh 'python3 sql_scanner.py'
                    } else {
                        // Используй полный путь к Python
                        bat '"C:\\Users\\user\\AppData\\Local\\Programs\\Python\\Python313\\python.exe" sql_scanner.py'
                    }
                }
            }
        }
        
        stage('Save Results') {
            steps {
                archiveArtifacts artifacts: 'found_queries.sql', 
                fingerprint: true
            }
        }
    }
}