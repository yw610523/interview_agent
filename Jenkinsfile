// Jenkinsfile - Interview Agent CI/CD
// 通过 GitHub Webhook 触发自动部署
pipeline {
    agent any
    
    environment {
        // Firecrawl API 地址(覆盖默认配置)
        FIRECRAWL_API_URL = 'http://192.168.1.15:3002'
        // Redis 端口(避免与宿主机Redis冲突)
        REDIS_PORT = '6679'
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
                    echo "FIRECRAWL_API_URL: ${env.FIRECRAWL_API_URL}"
                    echo "REDIS_PORT: ${env.REDIS_PORT}"
                    
                    sh """
                        chmod +x deploy/ci.sh
                        ./deploy/ci.sh
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
