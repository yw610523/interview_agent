import os

import emails
from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader

load_dotenv()  # 显式加载 .env 文件


def send_interview_email(recipient: str, questions: list):
    # 1. 直接使用 jinja2 渲染 HTML 内容
    env = Environment(loader=FileSystemLoader('app/templates'))
    template = env.get_template('email_template.html')
    html_content = template.render(questions=questions)

    # 2. 设置发件人显示名称[cite: 2]
    display_name = "面试官 AI 助手"
    sender_email = os.getenv("SMTP_USER")
    formatted_sender = f"{display_name} <{sender_email}>"

    # 3. 构建邮件对象，直接传入渲染好的 html_content[cite: 2]
    message = emails.html(
        subject="每日面试精选",
        html=html_content,
        mail_from=formatted_sender
    )
    smtp_settings = {
        "host": os.getenv("SMTP_SERVER"),
        "port": os.getenv("SMTP_PORT"),
        "ssl": True,
        "user": os.getenv("SMTP_USER"),
        "password": os.getenv("SMTP_PASSWORD"),
    }
    # 4. 发送邮件[cite: 2]
    r = message.send(to=recipient, smtp=smtp_settings)
    print(f"DEBUG: 状态码 = {r.status_code}")
    print(f"DEBUG: 错误信息 = {r.error}")
    return r.status_code
