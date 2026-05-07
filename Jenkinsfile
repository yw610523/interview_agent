// Jenkinsfile - 使用 docker-compose 部署
pipeline {
    agent any
    
    parameters {
        string(name: 'IMAGE_TAG', defaultValue: 'latest', description: 'Docker镜像标签')
        string(name: 'COMMIT_SHA', defaultValue: '', description: 'Git提交哈希')
        string(name: 'BRANCH', defaultValue: 'main', description: '分支名称')
    }
    
    environment {
        DEPLOY_DIR = '/data/interview_agent'
        IMAGE_TAG = "${params.IMAGE_TAG}"
    }
    
    stages {
        stage('Pull Latest Code') {
            steps {
                script {
                    echo "📥 拉取最新代码..."
                    
                    // 确保部署目录存在
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
        
        stage('Pull Docker Image') {
            steps {
                script {
                    echo "📥 拉取最新镜像..."
                    
                    sh """
                        cd ${DEPLOY_DIR}/deploy
                        docker compose pull app
                    """
                }
            }
        }
        
        stage('Create .env File') {
            steps {
                script {
                    echo "📝 创建 .env 文件..."
                    
                    // 使用 Jenkins 凭据生成 .env 文件
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
                        string(credentialsId: 'max-content-length', variable: 'MAX_CONTENT_LENGTH_PER_PAGE'),
                        string(credentialsId: 'model-max-input-tokens', variable: 'MODEL_MAX_INPUT_TOKENS'),
                        string(credentialsId: 'model-max-output-tokens', variable: 'MODEL_MAX_OUTPUT_TOKENS')
                    ]) {
                        sh """
                            cd ${DEPLOY_DIR}/deploy
                            
                            cat > .env << EOF
# SMTP 配置
SMTP_SERVER=${SMTP_SERVER}
SMTP_PORT=${SMTP_PORT}
SMTP_USER=${SMTP_USER}
SMTP_PASSWORD=${SMTP_PASSWORD}
SMTP_TEST_USER=${SMTP_TEST_USER}

# 爬虫配置
SITEMAP_URL=${SITEMAP_URL}
CRAWLER_TIMEOUT=${CRAWLER_TIMEOUT}
CRAWLER_MAX_URLS=${CRAWLER_MAX_URLS}
CRAWLER_DELAY=${CRAWLER_DELAY}
CRAWLER_OUTPUT_DIR=${CRAWLER_OUTPUT_DIR}
CRAWLER_USER_AGENT=${CRAWLER_USER_AGENT}

# 定时任务配置
SCHEDULER_HOUR=${SCHEDULER_HOUR}
SCHEDULER_MINUTE=${SCHEDULER_MINUTE}

# OpenAI 配置
OPENAI_API_KEY=${OPENAI_API_KEY}
OPENAI_API_BASE=${OPENAI_API_BASE}
OPENAI_MODEL=${OPENAI_MODEL}
OPENAI_EMBEDDING_MODEL=${OPENAI_EMBEDDING_MODEL}
EMBEDDING_DIMENSION=${EMBEDDING_DIMENSION}

# LLM 配置
MAX_CONTENT_LENGTH_PER_PAGE=${MAX_CONTENT_LENGTH_PER_PAGE}
MODEL_MAX_INPUT_TOKENS=${MODEL_MAX_INPUT_TOKENS}
MODEL_MAX_OUTPUT_TOKENS=${MODEL_MAX_OUTPUT_TOKENS}
EOF
                            
                            echo "✅ .env 文件创建成功"
                            cat .env
                        """
                    }
                }
            }
        }
        
        stage('Deploy with Docker Compose') {
            steps {
                script {
                    echo "🚀 使用 docker-compose 部署..."
                    
                    sh """
                        cd ${DEPLOY_DIR}/deploy
                        
                        # 停止并删除旧容器
                        docker compose down || true
                        
                        # 启动新容器
                        docker compose up -d
                        
                        echo "✅ 容器启动成功"
                    """
                }
            }
        }
        
        stage('Health Check') {
            steps {
                script {
                    echo "⏳ 等待服务启动..."
                    sleep(time: 15, unit: 'SECONDS')
                    
                    // 健康检查
                    def maxRetries = 5
                    def retryCount = 0
                    def isHealthy = false
                    
                    while (retryCount < maxRetries && !isHealthy) {
                        try {
                            sh "curl -f http://localhost:80/ || exit 1"
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
                    echo "🧹 清理旧镜像和容器..."
                    sh """
                        cd ${DEPLOY_DIR}/deploy
                        docker compose down --remove-orphans || true
                        docker image prune -f
                    """
                }
            }
        }
    }
    
    post {
        success {
            echo "✅ 部署成功！镜像标签: ${env.IMAGE_TAG}, 提交: ${params.COMMIT_SHA}"
        }
        failure {
            echo "❌ 部署失败！请检查日志"
        }
    }
}
