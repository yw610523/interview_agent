"""
LLM 配置测试

测试 LLM 配置的增删改查和同步功能
"""
from app.config.config_manager import config_manager
import pytest
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestLLMConfig:
    """LLM 配置测试类"""

    def test_01_read_llm_config(self):
        """测试读取 LLM 配置"""
        print("\n=== 测试1: 读取 LLM 配置 ===")

        llm_config = config_manager.get_config('llm')

        # 验证配置存在
        assert llm_config is not None, "LLM 配置不能为空"
        assert isinstance(llm_config, dict), "LLM 配置必须是字典类型"

        # 支持嵌套结构和平铺结构
        if 'openai' in llm_config:
            # 嵌套结构
            assert 'openai' in llm_config, "LLM 配置必须包含 openai 字段"
            assert 'embedding' in llm_config, "LLM 配置必须包含 embedding 字段"
            assert 'rerank' in llm_config, "LLM 配置必须包含 rerank 字段"
            
            print(f"[OK] API Key: {'***' if llm_config['openai'].get('api_key') else '(empty)'}")
            print(f"[OK] API Base: {llm_config['openai'].get('api_base')}")
            print(f"[OK] Model: {llm_config['openai'].get('model')}")
            print(f"[OK] Embedding Model: {llm_config['embedding'].get('model')}")
        else:
            # 平铺结构（向后兼容）
            required_fields = ['openai_api_key', 'openai_api_base', 'model', 'embedding_model']
            for field in required_fields:
                assert field in llm_config, f"LLM 配置必须包含 {field} 字段"

            print(f"[OK] API Key: {'***' if llm_config.get('openai_api_key') else '(empty)'}")
            print(f"[OK] API Base: {llm_config.get('openai_api_base')}")
            print(f"[OK] Model: {llm_config.get('model')}")
            print(f"[OK] Embedding Model: {llm_config.get('embedding_model')}")

    def test_02_update_llm_basic_config(self):
        """测试更新 LLM 基础配置"""
        print("\n=== 测试2: 更新 LLM 基础配置 ===")

        # 保存原始配置
        original_config = config_manager.get_config('llm').copy()

        try:
            # 创建新配置（嵌套结构）
            new_config = {
                'openai': {
                    'api_key': 'sk-test-key-123456',
                    'api_base': 'https://test.api.example.com/v1',
                    'model': 'gpt-4-test',
                    'max_input_tokens': 8000,
                    'max_output_tokens': 2000
                },
                'embedding': {
                    'model': 'text-embedding-test',
                    'dimension': 768
                },
                'rerank': {
                    'enabled': False,
                    'model': 'BAAI/bge-reranker-v2-m3'
                }
            }

            # 保存配置
            success = config_manager.save_config('llm', new_config)
            assert success, "保存 LLM 配置应该成功"

            print(f"[OK] 配置已保存")

            # 重新加载配置
            config_manager.reload()

            # 验证配置已更新
            updated_config = config_manager.get_config('llm')
            assert updated_config['openai']['api_key'] == 'sk-test-key-123456'
            assert updated_config['openai']['api_base'] == 'https://test.api.example.com/v1'
            assert updated_config['openai']['model'] == 'gpt-4-test'
            assert updated_config['embedding']['model'] == 'text-embedding-test'

            print(f"[OK] API Key 已更新: {'***'}")
            print(f"[OK] API Base 已更新: {updated_config['openai']['api_base']}")
            print(f"[OK] Model 已更新: {updated_config['openai']['model']}")
            print(f"[OK] Embedding Model 已更新: {updated_config['embedding']['model']}")

        finally:
            # 恢复原始配置
            config_manager.save_config('llm', original_config)
            config_manager.reload()
            print(f"[OK] 已恢复原始配置")

    def test_03_update_token_limits(self):
        """测试更新 Token 限制配置"""
        print("\n=== 测试3: 更新 Token 限制配置 ===")

        # 保存原始配置
        original_config = config_manager.get_config('llm').copy()

        try:
            # 设置 Token 限制（嵌套结构）
            new_config = original_config.copy()
            if 'openai' in new_config:
                new_config['openai']['max_input_tokens'] = 16000
                new_config['openai']['max_output_tokens'] = 4000
            else:
                new_config['max_input_tokens'] = 16000
                new_config['max_output_tokens'] = 4000

            config_manager.save_config('llm', new_config)
            config_manager.reload()

            # 验证配置
            updated_config = config_manager.get_config('llm')
            if 'openai' in updated_config:
                assert updated_config['openai']['max_input_tokens'] == 16000
                assert updated_config['openai']['max_output_tokens'] == 4000
                print(f"[OK] Max Input Tokens: {updated_config['openai']['max_input_tokens']}")
                print(f"[OK] Max Output Tokens: {updated_config['openai']['max_output_tokens']}")
            else:
                assert updated_config.get('max_input_tokens') == 16000
                assert updated_config.get('max_output_tokens') == 4000
                print(f"[OK] Max Input Tokens: {updated_config.get('max_input_tokens')}")
                print(f"[OK] Max Output Tokens: {updated_config.get('max_output_tokens')}")

        finally:
            # 恢复原始配置
            config_manager.save_config('llm', original_config)
            config_manager.reload()
            print(f"[OK] 已恢复原始配置")

    def test_04_update_embedding_dimension(self):
        """测试更新 Embedding 维度"""
        print("\n=== 测试4: 更新 Embedding 维度 ===")

        # 保存原始配置
        original_config = config_manager.get_config('llm').copy()

        try:
            # 设置 Embedding 维度（嵌套结构）
            new_config = original_config.copy()
            if 'embedding' in new_config:
                new_config['embedding']['dimension'] = 3072
            else:
                new_config['embedding_dimension'] = 3072

            config_manager.save_config('llm', new_config)
            config_manager.reload()

            # 验证配置
            updated_config = config_manager.get_config('llm')
            if 'embedding' in updated_config:
                assert updated_config['embedding']['dimension'] == 3072
                print(f"[OK] Embedding Dimension: {updated_config['embedding']['dimension']}")
            else:
                assert updated_config.get('embedding_dimension') == 3072
                print(f"[OK] Embedding Dimension: {updated_config.get('embedding_dimension')}")

        finally:
            # 恢复原始配置
            config_manager.save_config('llm', original_config)
            config_manager.reload()
            print(f"[OK] 已恢复原始配置")

    def test_05_config_persistence(self):
        """测试配置持久化"""
        print("\n=== 测试5: 配置持久化 ===")

        import yaml
        from pathlib import Path as PathLib
        from app.config.config_manager import ConfigManager

        # 保存测试配置（嵌套结构）
        test_config = {
            'openai': {
                'api_key': 'sk-persist-test-key',
                'api_base': 'https://persist.test.com/v1',
                'model': 'persist-model',
                'max_input_tokens': 128000,
                'max_output_tokens': 16384
            },
            'embedding': {
                'model': 'persist-embed',
                'dimension': 1024
            },
            'rerank': {
                'enabled': False,
                'model': 'BAAI/bge-reranker-v2-m3'
            }
        }

        config_manager.save_config('llm', test_config)

        # 从 ConfigManager 的覆盖目录读取文件（测试环境）
        config_dir = ConfigManager._config_dir_override
        if config_dir:
            # 测试环境：使用临时目录
            config_file = config_dir / 'llm.yaml'
        else:
            # 生产环境：使用项目根目录
            config_file = PathLib(__file__).parent.parent.parent / 'config' / 'llm.yaml'

        assert config_file.exists(), "配置文件应该存在"

        with open(config_file, 'r', encoding='utf-8') as f:
            file_content = yaml.safe_load(f)

        # 验证嵌套结构
        assert file_content['openai']['api_key'] == 'sk-persist-test-key'
        assert file_content['openai']['model'] == 'persist-model'

        print(f"[OK] 配置已持久化到文件")
        print(f"[OK] 文件内容验证通过")

        # 恢复原始配置（由 conftest.py 统一处理）
        print(f"[OK] 持久化测试完成")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
