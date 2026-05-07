// Jenkinsfile - 简化版，适用于公开镜像
pipeline {
    agent any
    
    parameters {
        string(name: 'IMAGE', defaultValue: 'ghcr.io/yw610523/interview_agent', description: 'Docker镜像地址')
        string(name: 'TAG', defaultValue: 'latest', description: '镜像标签')
        string(name: 'COMMIT_SHA', defaultValue: '', description: 'Git提交哈希')
        string(name: 'BRANCH', defaultValue: 'main', description: '分支名称')
    }
    
    environment {
        CONTAINER_NAME = 'interview_agent'
        IMAGE_NAME = "${params.IMAGE}:${params.TAG}"
    }
    
    stages {
        stage('Pull Docker Image') {
            steps {
                script {
                    echo "📥 拉取镜像: ${env.IMAGE_NAME}"
                    
                    // 公开镜像无需认证，直接拉取
                    sh "docker pull ${env.IMAGE_NAME}"
                }
            }
        }
        
        stage('Deploy Container') {
            steps {
                script {
                    echo "🚀 部署容器..."
                    
                    sh """
                        # 停止并删除旧容器
                        if docker ps -a | grep -q ${CONTAINER_NAME}; then
                            echo "🛑 停止旧容器..."
                            docker stop ${CONTAINER_NAME} || true
                            docker rm ${CONTAINER_NAME} || true
                        fi
                        
                        # 启动新容器
                        docker run -d \\
                          --name ${CONTAINER_NAME} \\
                          --restart unless-stopped \\
                          -p 8000:8000 \\
                          -v /data/interview_agent:/app/data \\
                          -e DATABASE_URL=${DATABASE_URL} \\
                          -e REDIS_URL=${REDIS_URL} \\
                          -e OPENAI_API_KEY=${OPENAI_API_KEY} \\
                          ${env.IMAGE_NAME}
                        
                        echo "✅ 容器启动成功"
                    """
                }
            }
        }
        
        stage('Health Check') {
            steps {
                script {
                    echo "⏳ 等待服务启动..."
                    sleep(time: 10, unit: 'SECONDS')
                    
                    // 健康检查
                    def maxRetries = 5
                    def retryCount = 0
                    def isHealthy = false
                    
                    while (retryCount < maxRetries && !isHealthy) {
                        try {
                            sh "curl -f http://localhost:8000/health || exit 1"
                            isHealthy = true
                            echo "✅ 健康检查通过"
                        } catch (Exception e) {
                            retryCount++
                            if (retryCount >= maxRetries) {
                                error("❌ 健康检查失败，服务可能未正常启动")
                            }
                            echo "⏳ 健康检查失败，重试 ${retryCount}/${maxRetries}..."
                            sleep(time: 5, unit: 'SECONDS')
                        }
                    }
                }
            }
        }
        
        stage('Cleanup') {
            steps {
                script {
                    echo "🧹 清理旧镜像..."
                    sh "docker image prune -f"
                }
            }
        }
    }
    
    post {
        success {
            echo "✅ 部署成功！镜像: ${env.IMAGE_NAME}, 提交: ${params.COMMIT_SHA}"
        }
        failure {
            echo "❌ 部署失败！请检查日志"
        }
    }
}
