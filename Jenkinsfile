// Jenkinsfile - Interview Agent CI/CD
// 通过 GitHub Webhook 触发自动部署
pipeline {
    agent any

    parameters {
        // AI 模型配置
        password(name: 'OPENAI_API_KEY', defaultValue: 'sk-ERuRNVNN9ntK5VBX0eD2792c59E046A2B80eA7Fb75Cb82D1', description: 'OpenAI API Key')
        string(name: 'OPENAI_API_BASE', defaultValue: 'https://one-api.yys2024.cn/v1', description: 'OpenAI API 基础地址')
        string(name: 'OPENAI_MODEL', defaultValue: 'deepseek', description: '使用的对话模型名称')

        // Embedding 配置
        string(name: 'EMBEDDING_API_BASE', defaultValue: 'https://one-api.yys2024.cn/v1', description: 'Embedding API 基础地址')
        password(name: 'EMBEDDING_API_KEY', defaultValue: 'sk-ERuRNVNN9ntK5VBX0eD2792c59E046A2B80eA7Fb75Cb82D1', description: 'Embedding API Key')
        string(name: 'EMBEDDING_MODEL', defaultValue: 'BAAI/bge-m3', description: '向量模型名称')
        string(name: 'EMBEDDING_DIMENSION', defaultValue: '1024', description: '向量维度')

        // Rerank 配置
        booleanParam(name: 'RERANK_ENABLED', defaultValue: true, description: '是否启用重排序 (Rerank)')
        string(name: 'RERANK_API_BASE', defaultValue: 'https://siliconflow.cn/v1', description: 'Rerank API 基础地址')
        password(name: 'RERANK_API_KEY', defaultValue: 'sk-yeathgugpljvxgnrjviegxojtomivpwwqkqgxwdvjirwxalj', description: 'Rerank API Key')
        string(name: 'RERANK_MODEL', defaultValue: 'BAAI/bge-reranker-v2-m3', description: '重排序模型名称')

        // Redis 配置
        string(name: 'REDIS_HOST', defaultValue: 'hp.yys2024.cn', description: 'Redis 地址')
        string(name: 'REDIS_PORT', defaultValue: '6679', description: 'Redis 端口')
        password(name: 'REDIS_PASSWORD', defaultValue: '', description: 'Redis 密码 (留空则不使用)')

        // SMTP 邮件配置
        string(name: 'SMTP_SERVER', defaultValue: 'smtp.qq.com', description: 'SMTP 服务器地址')
        string(name: 'SMTP_PORT', defaultValue: '587', description: 'SMTP 端口')
        string(name: 'SMTP_USER', defaultValue: 'ryan890219@qq.com', description: '发件人邮箱')
        password(name: 'SMTP_PASSWORD', defaultValue: 'yhgmvbegazuajdbg', description: 'SMTP 授权码')


        string(name: 'FIRECRAWL_API_URL', defaultValue: 'http://192.168.1.15:3002', description: 'firecrawl访问地址')
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
                    withEnv([
                        "OPENAI_API_KEY=${params.OPENAI_API_KEY}",
                        "OPENAI_API_BASE=${params.OPENAI_API_BASE}",
                        "OPENAI_MODEL=${params.OPENAI_MODEL}",
                        "EMBEDDING_API_BASE=${params.EMBEDDING_API_BASE}",
                        "EMBEDDING_API_KEY=${params.EMBEDDING_API_KEY}",
                        "EMBEDDING_MODEL=${params.EMBEDDING_MODEL}",
                        "EMBEDDING_DIMENSION=${params.EMBEDDING_DIMENSION}",
                        "RERANK_ENABLED=${params.RERANK_ENABLED}",
                        "RERANK_API_BASE=${params.RERANK_API_BASE}",
                        "RERANK_API_KEY=${params.RERANK_API_KEY}",
                        "RERANK_MODEL=${params.RERANK_MODEL}",
                        "REDIS_HOST=${params.REDIS_HOST}",
                        "REDIS_PORT=${params.REDIS_PORT}",
                        "REDIS_PASSWORD=${params.REDIS_PASSWORD}",
                        "SMTP_SERVER=${params.SMTP_SERVER}",
                        "SMTP_PORT=${params.SMTP_PORT}",
                        "SMTP_USER=${params.SMTP_USER}",
                        "SMTP_PASSWORD=${params.SMTP_PASSWORD}",
                        "FIRECRAWL_API_URL=${params.FIRECRAWL_API_URL}"
                    ]) {
                        sh """
                            chmod +x deploy/ci.sh
                            ./deploy/ci.sh
                        """
                    }
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
