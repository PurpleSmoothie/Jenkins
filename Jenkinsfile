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
                // Python работает везде где есть Jenkins!
                sh 'python3 sql_scanner.py'
                // или если python3 не работает:
                sh 'python sql_scanner.py'
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