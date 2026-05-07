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
                    
                    // 使用 Jenkins 凭据注入环境变量
                    withCredentials([
                        string(credentialsId: 'smtp-server', variable: 'SMTP_SERVER'),
                        string(credentialsId: 'smtp-port', variable: 'SMTP_PORT'),
                        string(credentialsId: 'smtp-user', variable: 'SMTP_USER'),
                        string(credentialsId: 'smtp-password', variable: 'SMTP_PASSWORD'),
                        string(credentialsId: 'smtp-test-user', variable: 'SMTP_TEST_USER'),
                        string(credentialsId: 'sitemap-url', variable: 'SITEMAP_URL'),
                        string(credentialsId: 'crawler-timeout', variable: 'CRAWLER_TIMEOUT'),
                        string(credentialsId: 'crawler-max-urls', variable: 'CRAWLER_MAX_URLS'),
                        string(credentialsId: 'crawler-delay', variable: 'CRAWLER_DELAY'),
                        string(credentialsId: 'crawler-output-dir', variable: 'CRAWLER_OUTPUT_DIR'),
                        string(credentialsId: 'crawler-user-agent', variable: 'CRAWLER_USER_AGENT'),
                        string(credentialsId: 'scheduler-hour', variable: 'SCHEDULER_HOUR'),
                        string(credentialsId: 'scheduler-minute', variable: 'SCHEDULER_MINUTE'),
                        string(credentialsId: 'openai-api-key', variable: 'OPENAI_API_KEY'),
                        string(credentialsId: 'openai-api-base', variable: 'OPENAI_API_BASE'),
                        string(credentialsId: 'openai-model', variable: 'OPENAI_MODEL'),
                        string(credentialsId: 'openai-embedding-model', variable: 'OPENAI_EMBEDDING_MODEL'),
                        string(credentialsId: 'embedding-dimension', variable: 'EMBEDDING_DIMENSION'),
                        string(credentialsId: 'redis-url', variable: 'REDIS_URL'),
                        string(credentialsId: 'max-content-length', variable: 'MAX_CONTENT_LENGTH_PER_PAGE'),
                        string(credentialsId: 'model-max-input-tokens', variable: 'MODEL_MAX_INPUT_TOKENS'),
                        string(credentialsId: 'model-max-output-tokens', variable: 'MODEL_MAX_OUTPUT_TOKENS')
                    ]) {
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
                              -e SMTP_SERVER=${SMTP_SERVER} \\
                              -e SMTP_PORT=${SMTP_PORT} \\
                              -e SMTP_USER=${SMTP_USER} \\
                              -e SMTP_PASSWORD=${SMTP_PASSWORD} \\
                              -e SMTP_TEST_USER=${SMTP_TEST_USER} \\
                              -e SITEMAP_URL=${SITEMAP_URL} \\
                              -e CRAWLER_TIMEOUT=${CRAWLER_TIMEOUT} \\
                              -e CRAWLER_MAX_URLS=${CRAWLER_MAX_URLS} \\
                              -e CRAWLER_DELAY=${CRAWLER_DELAY} \\
                              -e CRAWLER_OUTPUT_DIR=${CRAWLER_OUTPUT_DIR} \\
                              -e CRAWLER_USER_AGENT=${CRAWLER_USER_AGENT} \\
                              -e SCHEDULER_HOUR=${SCHEDULER_HOUR} \\
                              -e SCHEDULER_MINUTE=${SCHEDULER_MINUTE} \\
                              -e OPENAI_API_KEY=${OPENAI_API_KEY} \\
                              -e OPENAI_API_BASE=${OPENAI_API_BASE} \\
                              -e OPENAI_MODEL=${OPENAI_MODEL} \\
                              -e OPENAI_EMBEDDING_MODEL=${OPENAI_EMBEDDING_MODEL} \\
                              -e EMBEDDING_DIMENSION=${EMBEDDING_DIMENSION} \\
                              -e REDIS_URL=${REDIS_URL} \\
                              -e MAX_CONTENT_LENGTH_PER_PAGE=${MAX_CONTENT_LENGTH_PER_PAGE} \\
                              -e MODEL_MAX_INPUT_TOKENS=${MODEL_MAX_INPUT_TOKENS} \\
                              -e MODEL_MAX_OUTPUT_TOKENS=${MODEL_MAX_OUTPUT_TOKENS} \\
                              ${env.IMAGE_NAME}
                            
                            echo "✅ 容器启动成功"
                        """
                    }
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
