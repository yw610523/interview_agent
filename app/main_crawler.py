"""
Sitemap 爬虫 CLI 入口点

此模块提供运行站点地图爬虫的命令行界面。

使用方法:
    python -m app.main_crawler --sitemap-url https://example.com/sitemap.xml
    python -m app.main_crawler --config app/config/crawler_config.json
"""

import argparse
import logging
import sys
from pathlib import Path

from app.services.sitemap_crawler import SitemapCrawler, CrawlConfig
from app.config.crawler_config import get_config_from_env


def setup_logging(verbose: bool = False) -> None:
    """根据详细程度配置日志记录。"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(
        description='Sitemap 爬虫 - 从站点地图爬取和分析网站',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s --sitemap-url https://example.com/sitemap.xml
  %(prog)s --sitemap-url https://example.com/sitemap.xml --max-urls 100
  %(prog)s --config crawler_config.json
  %(prog)s --sitemap-url https://example.com/sitemap.xml --output-dir ./results
        """,
    )

    # 输入选项
    input_group = parser.add_argument_group('输入选项')
    input_group.add_argument(
        '--sitemap-url', '-u',
        type=str,
        help='要爬取的站点地图 URL',
    )
    input_group.add_argument(
        '--config', '-c',
        type=str,
        help='JSON 配置文件路径',
    )

    # 爬取设置
    crawl_group = parser.add_argument_group('爬取设置')
    crawl_group.add_argument(
        '--timeout', '-t',
        type=int,
        default=30,
        help='请求超时时间（秒）（默认: 30）',
    )
    crawl_group.add_argument(
        '--max-urls', '-m',
        type=int,
        help='最大爬取 URL 数量',
    )
    crawl_group.add_argument(
        '--delay', '-d',
        type=float,
        default=0.5,
        help='请求间隔时间（秒）（默认: 0.5）',
    )
    crawl_group.add_argument(
        '--no-ssl-verify',
        action='store_true',
        help='禁用 SSL 证书验证',
    )
    crawl_group.add_argument(
        '--no-follow-redirects',
        action='store_true',
        help='不跟随重定向',
    )

    # 输出选项
    output_group = parser.add_argument_group('输出选项')
    output_group.add_argument(
        '--output-dir', '-o',
        type=str,
        default='./crawl_results',
        help='爬取结果保存目录（默认: ./crawl_results）',
    )
    output_group.add_argument(
        '--no-save',
        action='store_true',
        help='不保存结果到文件',
    )
    output_group.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='禁用详细输出',
    )
    output_group.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='启用调试日志',
    )

    return parser.parse_args()


def main() -> int:
    """主入口点。"""
    args = parse_args()

    # Setup logging
    setup_logging(verbose=args.verbose)
    logger = logging.getLogger(__name__)

    # Load configuration
    if args.config:
        config_path = Path(args.config)
        if not config_path.exists():
            logger.error(f"Configuration file not found: {config_path}")
            return 1
        config = CrawlConfig.from_json(str(config_path))
    else:
        config = get_config_from_env()

    # Override config with command line arguments
    if args.sitemap_url:
        config.sitemap_url = args.sitemap_url
    if not config.sitemap_url:
        logger.error("Sitemap URL is required. Use --sitemap-url or --config")
        return 1

    config.timeout = args.timeout
    config.delay_between_requests = args.delay
    config.verify_ssl = not args.no_ssl_verify
    config.follow_redirects = not args.no_follow_redirects
    config.output_dir = args.output_dir
    config.save_results = not args.no_save
    config.verbose = not args.quiet

    if args.max_urls:
        config.max_urls = args.max_urls

    logger.info(f"Starting crawl for: {config.sitemap_url}")
    logger.info(f"Configuration: timeout={config.timeout}s, delay={config.delay_between_requests}s")

    # Create and run crawler
    crawler = SitemapCrawler(config=config)

    try:
        results = crawler.crawl()

        # Print summary
        crawler.print_report()

        # Save results if configured
        if config.save_results:
            filepath = crawler.save_results()
            logger.info(f"Results saved to: {filepath}")

        # Return non-zero if there were failures
        if crawler.statistics.failed_scans > 0:
            logger.warning(f"{crawler.statistics.failed_scans} URLs failed to scan")
            return 1

        return 0

    except KeyboardInterrupt:
        logger.info("\nCrawl interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Crawl failed: {e}")
        if args.verbose:
            logger.exception("Detailed error:")
        return 1


if __name__ == '__main__':
    sys.exit(main())