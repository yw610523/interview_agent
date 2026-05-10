"""
Prompts 提示词配置测试

测试提示词配置的增删改查和同步功能
"""
from app.config.config_manager import config_manager
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestPromptsConfig:
    """Prompts 配置测试类"""

    # 类变量：保存原始的 prompts 配置（在第一次测试前读取）
    _original_prompts = None

    @classmethod
    def setup_class(cls):
        """测试类开始前，保存原始 prompts 配置"""
        cls._original_prompts = config_manager.get_config('prompts').copy()
        print(
            f"\n[SETUP] Saved original prompts config (question: {len(cls._original_prompts.get('question_extraction_system', ''))} chars, answer: {len(cls._original_prompts.get('answer_generation_system', ''))} chars)")

    @classmethod
    def teardown_class(cls):
        """测试类结束后清理（由 conftest.py 统一处理）"""
        pass  # 临时目录会在 pytest_sessionfinish 中自动清理

    def test_01_read_prompts_config(self):
        """测试读取 Prompts 配置"""
        print("\n=== Test 1: Read Prompts Config ===")

        # 使用 get_config 方法获取 prompts 配置
        prompts_config = config_manager.get_config('prompts')

        assert prompts_config is not None
        assert isinstance(prompts_config, dict)

        # 验证关键字段
        required_fields = ['question_extraction_system', 'answer_generation_system']
        for field in required_fields:
            assert field in prompts_config, f"Prompts config must contain {field} field"

        print(f"[OK] Question Extraction System: {'[set]' if prompts_config.get('question_extraction_system') else '[empty]'}")
        print(f"[OK] Answer Generation System: {'[set]' if prompts_config.get('answer_generation_system') else '[empty]'}")
        print(f"[OK] Question Extraction Length: {len(prompts_config.get('question_extraction_system', ''))} chars")
        print(f"[OK] Answer Generation Length: {len(prompts_config.get('answer_generation_system', ''))} chars")

    def test_02_update_question_extraction_prompt(self):
        """测试更新问题提取提示词"""
        print("\n=== Test 2: Update Question Extraction Prompt ===")

        # 创建新配置
        new_config = self._original_prompts.copy()
        new_config['question_extraction_system'] = 'Test prompt for question extraction'

        success = config_manager.save_config('prompts', new_config)
        assert success

        # 直接读取 Redis，无需 reload
        updated_config = config_manager.get_config('prompts')
        assert updated_config.get('question_extraction_system') == 'Test prompt for question extraction'

        print(f"[OK] Question Extraction Prompt updated")
        print(f"[OK] Length: {len(updated_config.get('question_extraction_system', ''))} chars")

    def test_03_update_answer_generation_prompt(self):
        """测试更新答案生成提示词"""
        print("\n=== Test 3: Update Answer Generation Prompt ===")

        new_config = self._original_prompts.copy()
        new_config['answer_generation_system'] = 'Test prompt for answer generation'

        success = config_manager.save_config('prompts', new_config)
        assert success

        # 直接读取 Redis，无需 reload
        updated_config = config_manager.get_config('prompts')
        assert updated_config.get('answer_generation_system') == 'Test prompt for answer generation'

        print(f"[OK] Answer Generation Prompt updated")
        print(f"[OK] Length: {len(updated_config.get('answer_generation_system', ''))} chars")

    def test_04_update_both_prompts(self):
        """测试同时更新两个提示词"""
        print("\n=== Test 4: Update Both Prompts ===")

        new_config = {
            'question_extraction_system': 'New question extraction prompt',
            'answer_generation_system': 'New answer generation prompt'
        }

        success = config_manager.save_config('prompts', new_config)
        assert success

        # 直接读取 Redis，无需 reload
        updated_config = config_manager.get_config('prompts')
        assert updated_config.get('question_extraction_system') == 'New question extraction prompt'
        assert updated_config.get('answer_generation_system') == 'New answer generation prompt'

        print(f"[OK] Both prompts updated")

    def test_05_config_persistence(self):
        """测试配置持久化到 Redis"""
        print("\n=== Test 5: Config Persistence ===")

        test_config = {
            'question_extraction_system': 'Persist test question prompt',
            'answer_generation_system': 'Persist test answer prompt'
        }

        config_manager.save_config('prompts', test_config)

        # 验证配置已保存到 Redis
        redis_config = config_manager.get_config('prompts')
        assert redis_config.get('question_extraction_system') == 'Persist test question prompt'
        assert redis_config.get('answer_generation_system') == 'Persist test answer prompt'

        print(f"[OK] Config persisted to Redis")
        print(f"[OK] Redis content verified")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
