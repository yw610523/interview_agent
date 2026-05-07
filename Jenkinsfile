// Jenkinsfile - Interview Agent CI/CD
// 通过 GitHub Webhook 触发自动部署
pipeline {
    agent any
    
    environment {
        DEPLOY_DIR = '/data/interview_agent'
    }
    
    stages {
        stage('Pull Latest Code') {
            steps {
                script {
                    echo "📥 拉取最新代码..."
                    
                    sh """
                        mkdir -p ${DEPLOY_DIR}
                        cd ${DEPLOY_DIR}
                        
                        # 如果已存在git仓库，则pull；否则clone
                        if [ -d .git ]; then
                            git pull origin main
                        else
                            git clone https://github.com/yw610523/interview_agent.git .
                        fi
                    """
                }
            }
        }
        
        stage('Deploy with CI Script') {
            steps {
                script {
                    echo "🚀 执行部署脚本..."
                    
                    sh """
                        cd ${DEPLOY_DIR}
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
