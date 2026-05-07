import os
import pytest
from app.services.email_service import send_interview_email


@pytest.mark.skipif(
    not os.getenv("SMTP_TEST_USER"),
    reason="需要设置 SMTP_TEST_USER 环境变量"
)
def test_send_real_email():
    """
    真实场景测试：会通过网络连接 QQ 邮箱服务器并发送邮件
    """
    # 模拟题目数据
    mock_questions = [
        {
            "title": "什么是 FastAPI 的依赖注入？",
            "answer": "通过 Depends() 实现组件解耦。",
            "source_url": "https://fastapi.tiangolo.com/"
        }
    ]

    target_email = os.getenv("SMTP_TEST_USER")

    print(f"正在尝试向 {target_email} 发送真实邮件...")
    status = send_interview_email(target_email, mock_questions)

    # QQ 邮箱发送成功返回 250
    assert status == 250
    print("邮件发送成功，请检查收件箱（或垃圾箱）。")
