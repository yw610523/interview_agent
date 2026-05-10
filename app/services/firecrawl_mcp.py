"""
Firecrawl MCP 集成服务

此模块提供与 Firecrawl MCP 服务的集成，用于解析动态渲染的网页内容。
支持自托管和官方 API 两种模式。
"""

import logging
from typing import Dict, List, Optional, Any

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class FirecrawlResult(BaseModel):
    """Firecrawl 爬取结果模型"""
    success: bool = True
    markdown: Optional[str] = None
    html: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    url: str = ""
    title: Optional[str] = None
    content_type: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "success": self.success,
            "markdown": self.markdown,
            "html": self.html,
            "metadata": self.metadata,
            "error": self.error,
            "url": self.url,
            "title": self.title,
            "content_type": self.content_type,
        }


class FirecrawlMCPService:
    """
    Firecrawl MCP 服务集成类

    支持两种模式：
    1. 自托管 Firecrawl 服务（Docker）
    2. Firecrawl 官方 API（需要 API Key）
    """

    def __init__(
        self,
        api_url: str = "http://firecrawl:3002",
        api_key: Optional[str] = None,
        timeout: int = 60,
        api_version: str = "v2",
    ):
        """
        初始化 Firecrawl MCP 服务。

        参数:
            api_url: Firecrawl 服务地址（自托管或官方 API）
            api_key: Firecrawl API Key（官方 API 必须提供）
            timeout: 请求超时时间（秒）
            api_version: API 版本号（默认 v2）
        """
        # 清理 URL 末尾的斜杠
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.api_version = api_version

    async def scrape_url(
        self,
        url: str,
        formats: List[str] = None,
        only_main_content: bool = True,
        wait_for: Optional[str] = None,
        actions: List[Dict[str, Any]] = None,
    ) -> FirecrawlResult:
        """
        使用 Firecrawl 爬取单个 URL。

        参数:
            url: 要爬取的 URL
            formats: 返回格式列表 ["markdown", "html", "rawHtml"]，默认 ["markdown"]
            only_main_content: 是否只提取主要内容
            wait_for: 等待 CSS 选择器或时间（如 "1000" 表示 1 秒）
            actions: 额外的浏览器操作（如点击、滚动等）

        返回:
            FirecrawlResult 对象
        """
        if formats is None:
            formats = ["markdown"]

        try:
            # 构建 API 端点：{api_url}/{api_version}/scrape
            endpoint = f"{self.api_url}/{self.api_version}/scrape"

            # 构建请求 payload
            payload = {
                "url": url,
                "formats": formats,
                "onlyMainContent": only_main_content,
            }

            # 添加可选参数
            if wait_for:
                payload["waitFor"] = wait_for
            if actions:
                payload["actions"] = actions

            # 设置请求头
            headers = {
                "Content-Type": "application/json",
            }

            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            # 发送请求
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(endpoint, json=payload, headers=headers)
                response.raise_for_status()

                data = response.json()

                # 解析响应
                if data.get("success"):
                    result_data = data.get("data", {})
                    return FirecrawlResult(
                        success=True,
                        markdown=result_data.get("markdown"),
                        html=result_data.get("html"),
                        metadata=result_data.get("metadata", {}),
                        url=url,
                        title=result_data.get("metadata", {}).get("title"),
                        content_type=result_data.get("metadata", {}).get("contentType"),
                    )
                else:
                    return FirecrawlResult(
                        success=False,
                        error=data.get("error", "Unknown error"),
                        url=url,
                    )

        except httpx.TimeoutException:
            logger.error(f"Firecrawl 请求超时: {url}")
            return FirecrawlResult(
                success=False,
                error=f"Request timed out after {self.timeout} seconds",
                url=url,
            )
        except httpx.HTTPError as e:
            logger.error(f"Firecrawl HTTP 错误: {str(e)}")
            return FirecrawlResult(
                success=False,
                error=f"HTTP error: {str(e)}",
                url=url,
            )
        except Exception as e:
            logger.error(f"Firecrawl 未知错误: {str(e)}")
            return FirecrawlResult(
                success=False,
                error=f"Unexpected error: {str(e)}",
                url=url,
            )

    async def map_url(
        self,
        url: str,
        search: Optional[str] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """
        使用 Firecrawl Map 功能发现网站的所有页面。

        参数:
            url: 起始 URL
            search: 可选的搜索关键词过滤
            limit: 返回的最大 URL 数量

        返回:
            包含 URLs 列表的字典
        """
        try:
            endpoint = f"{self.api_url}/{self.api_version}/map"

            payload = {
                "url": url,
                "limit": limit,
            }

            if search:
                payload["search"] = search

            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(endpoint, json=payload, headers=headers)
                response.raise_for_status()

                data = response.json()
                return data

        except Exception as e:
            logger.error(f"Firecrawl Map 错误: {str(e)}")
            return {"success": False, "error": str(e)}

    def is_available(self) -> bool:
        """
        检查 Firecrawl 服务是否可用。

        返回:
            bool: 服务是否可用
        """
        try:
            import requests
            health_url = f"{self.api_url}/health"
            response = requests.get(health_url, timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.debug(f"Firecrawl 健康检查失败: {str(e)}")
            return False

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> "FirecrawlMCPService":
        """
        从配置字典创建 FirecrawlMCPService 实例。

        参数:
            config: 配置字典，包含以下键：
                - firecrawl_api_url: API URL（必填）
                - firecrawl_api_key: API Key（可选）
                - firecrawl_timeout: 超时时间
                - firecrawl_api_version: API 版本（默认 v2）

        返回:
            FirecrawlMCPService 实例
        """
        return cls(
            api_url=config.get("firecrawl_api_url", "http://firecrawl:3002"),
            api_key=config.get("firecrawl_api_key"),
            timeout=config.get("firecrawl_timeout", 60),
            api_version=config.get("firecrawl_api_version", "v2"),
        )
