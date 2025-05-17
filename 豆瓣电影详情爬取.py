#python时间到
import logging
import logging
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from lxml import etree
import time
import re
import random

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 请求头配置
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36 Edg/136.0.0.0',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Referer': 'https://movie.douban.com/',  # 模拟从豆瓣内部跳转
}

# 使用 Session 对象
session = requests.Session()
session.headers.update(headers)


# 代理 IP 列表 (你需要替换成你自己的代理 IP)
# proxies = [
#     {'http': 'http://221.204.223.178', 'https': 'http://123.30.154.171'},
#     {'http': 'http://218.87.205.2', 'https': 'http://128.199.121.61'},
# ]

def get_page(url, retry_times=3):
    """获取页面内容"""
    for i in range(retry_times):
        try:
            # 随机选择一个代理 IP
            # proxy = random.choice(proxies) if proxies else None

            response = session.get(url, timeout=10)
            if response.status_code == 200:
                return response.content
            else:
                logger.warning(f"请求失败，状态码: {response.status_code}，URL: {url}")
        except Exception as e:
            logger.error(f"请求异常: {str(e)}，URL: {url}")
            if i < retry_times - 1:  # 如果不是最后一次重试
                time.sleep(random.uniform(1, 3))  # 随机延迟
                continue
        return None


def extract_details(li_element):
    """从列表元素中提取电影详情"""
    try:
        # 提取标题 - 适应Top250页面的结构
        title_node = li_element.xpath('.//span[@class="title"][1]/text()')
        title = title_node[0].strip() if title_node else None

        # 提取URL - 适应Top250页面的结构
        url_node = li_element.xpath('.//div[@class="hd"]/a/@href')
        detail_url = url_node[0] if url_node else None

        if title and detail_url:
            return title, detail_url
        return None
    except Exception as e:
        logger.error(f"提取详情失败: {str(e)}")
        return None


def process_movie(li_element):
    """处理单个电影元素"""
    try:
        result = extract_details(li_element)
        if result:
            title, url = result
            logger.info(f"成功处理电影: {title}")
            return title, url  # 返回 title 和 url
        return None
    except Exception as e:
        logger.error(f"处理电影失败: {str(e)}")
        return None


def extract_movie_details(url):
    """提取电影详情页面的数据"""
    try:
        content = get_page(url)
        if not content:
            logger.warning(f"无法获取电影详情页面内容: {url}")
            return None

        html = etree.HTML(content)

        # 提取电影类型
        genres = html.xpath('//span[@property="v:genre"]/text()')

        # 提取评分
        rating = html.xpath('//strong[@property="v:average"]/text()')
        rating = rating[0] if rating else "暂无评分"

        # 提取导演
        director = html.xpath('//a[@rel="v:directedBy"]/text()')
        director = director[0] if director else "未知"

        # 提取主演
        actors = html.xpath('//a[@rel="v:starring"]/text()')
        actors = actors[:3] if actors else ["未知"]

        # 提取年份
        year = html.xpath('//span[@class="year"]/text()')
        year = year[0].strip('()') if year else "未知"

        # 提取简介
        summary = html.xpath('//span[@property="v:summary"]/text()')
        summary = summary[0].strip() if summary else "暂无简介"

        movie_details = {
            'genres': genres,
            'rating': rating,
            'director': director,
            'actors': actors,
            'year': year,
            'summary': summary
        }

        return movie_details

    except Exception as e:
        logger.error(f"提取电影详情失败: {str(e)}")
        return None


def optimize_crawl(base_url):
    """优化的爬虫主函数"""
    try:
        # 获取主页面
        content = get_page(base_url)
        if not content:
            raise ValueError(f"无法获取页面内容: {base_url}")

        # 解析HTML
        html = etree.HTML(content)

        li_elements = html.xpath('//*[@id="content"]/div/div[1]/ol/li')

        # 添加调试信息
        logger.info(f"页面内容长度: {len(content)}")
        logger.info(f"找到的电影元素数量: {len(li_elements)}")

        if not li_elements:
            # 如果没有找到元素，输出页面内容片段以供调试
            logger.warning("未找到电影列表元素")
            logger.debug(f"页面内容片段: {content[:500]}")  # 只显示前500字符
            return []

        # 使用线程池处理
        results = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_li = {executor.submit(process_movie, li): li for li in li_elements}

            for future in as_completed(future_to_li):
                try:
                    result = future.result()
                    if result:
                        title, url = result
                        movie_details = extract_movie_details(url)  # 提取电影详情
                        if movie_details:
                            results.append((title, url, movie_details))  # 保存电影详情
                except Exception as e:
                    logger.error(f"处理电影信息失败: {str(e)}")

        return results

    except Exception as e:
        logger.error(f"爬虫运行失败: {str(e)}")
        return []


def main():
    all_movies = []

    for page in range(1, 11):
        logger.info(f"正在爬取第 {page} 页...")
        base_url = f'https://movie.douban.com/top250?start={(page - 1) * 25}'
        movies = optimize_crawl(base_url)

        if movies:
            all_movies.extend(movies)
            logger.info(f"第 {page} 页爬取完成，获取到 {len(movies)} 部电影信息")

        # 添加随机延迟，避免被封
        time.sleep(random.uniform(2, 4))

    # 保存数据到文件
    with open('douban_movies.txt', 'w', encoding='utf-8') as f:
        for title, url, details in all_movies:
            f.write(f"电影名称：{title}\n")
            f.write(f"详情链接：{url}\n")
            f.write(f"评分：{details['rating']}\n")
            f.write(f"年份：{details['year']}\n")
            f.write(f"导演：{details['director']}\n")
            f.write(f"主演：{', '.join(details['actors'])}\n")
            f.write(f"类型：{', '.join(details['genres'])}\n")
            f.write(f"简介：{details['summary']}\n")
            f.write("-" * 80 + "\n")

    logger.info(f"爬取完成，共获取 {len(all_movies)} 部电影信息")


if __name__ == "__main__":
    main()