// Jenkinsfile - Interview Agent CI/CD
// 通过 GitHub Webhook 触发自动部署
pipeline {
    agent any
    
    parameters {
        booleanParam(
            name: 'USE_EXTERNAL_REDIS',
            defaultValue: true,
            description: '是否使用外置 Redis（默认是）'
        )
    }
    
    stages {
        stage('Checkout Code') {
            steps {
                script {
                    echo "📥 拉取最新代码..."
                    // Jenkins 会自动 checkout 代码到工作空间
                    checkout scm
                }
            }
        }
        
        stage('Deploy with CI Script') {
            steps {
                script {
                    echo "🚀 执行部署脚本..."
                    
                    // 根据参数选择 docker-compose 文件
                    def composeFile = params.USE_EXTERNAL_REDIS ? 'docker-compose-external-redis.yml' : 'docker-compose.yml'
                    echo "使用配置文件: ${composeFile}"
                    
                    sh """
                        chmod +x deploy/ci.sh
                        COMPOSE_FILE=${composeFile} ./deploy/ci.sh
                    """
                }
            }
        }
    }
    
    post {
        success {
            echo "✅ 部署成功！"
        }
        failure {
            echo "❌ 部署失败！请检查日志"
        }
    }
}
