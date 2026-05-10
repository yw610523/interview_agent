import os

import emails
from jinja2 import Environment, FileSystemLoader

# 导入统一配置管理器
from app.config.config_manager import config_manager


def send_interview_email(recipient: str, questions: list):
    # 1. 直接使用 jinja2 渲染 HTML 内容
    env = Environment(loader=FileSystemLoader('app/templates'))
    template = env.get_template('email_template.html')
    html_content = template.render(questions=questions)

    # 2. 设置发件人显示名称[cite: 2]
    display_name = "面试官 AI 助手"
    # 优先从 config.yaml 读取，兼容环境变量
    smtp_config = config_manager.get_config('smtp')
    sender_email = smtp_config.get('user') or os.getenv("SMTP_USER")
    formatted_sender = f"{display_name} <{sender_email}>"

    # 3. 构建邮件对象，直接传入渲染好的 html_content[cite: 2]
    message = emails.html(
        subject="每日面试精选",
        html=html_content,
        mail_from=formatted_sender
    )
    
    # 优先从 config.yaml 读取 SMTP 配置
    smtp_settings = {
        "host": smtp_config.get('server') or os.getenv("SMTP_SERVER"),
        "port": smtp_config.get('port') or os.getenv("SMTP_PORT"),
        "ssl": True,
        "user": sender_email,
        "password": smtp_config.get('password') or os.getenv("SMTP_PASSWORD"),
    }
    
    # 4. 发送邮件[cite: 2]
    r = message.send(to=recipient, smtp=smtp_settings)
    print(f"DEBUG: 状态码 = {r.status_code}")
    print(f"DEBUG: 错误信息 = {r.error}")
    return r.status_code
