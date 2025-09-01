pipeline {
    agent any
    stages {
        stage('Checkout') {
            steps { 
                git branch: 'main', 
                url: 'https://github.com/PurpleSmoothie/Jenkins.git',
                credentialsId: 'github-creds'
            }
        }
        
        stage('Find SQL Queries') {
            steps {
                script {
                    // Универсальный вызов для Linux и Windows
                    if (isUnix()) {
                        // Для Linux/macOS
                        sh 'python3 sql_scanner.py'
                    } else {
                        // Для Windows
                        bat 'python sql_scanner.py'
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