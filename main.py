import json
import os
import random
import time
from typing import Any
from loguru import logger
from apis.xhs_pc_apis import XHS_Apis
from xhs_utils.common_util import init, load_keywords_config
from xhs_utils.data_util import handle_note_info, download_note, save_to_xlsx
from xhs_utils.path_util import is_note_downloaded, extract_note_id_from_url


class Data_Spider:
    def __init__(self) -> None:
        self.xhs_apis: XHS_Apis = XHS_Apis()

    def spider_note(self, note_url: str, cookies_str: str, proxies: dict | None = None) -> tuple[bool, str, dict | None]:
        """
        爬取一个笔记的信息
        :param note_url: 笔记 URL
        :param cookies_str: cookies 字符串
        :param proxies: 代理配置
        :return: (success, msg, note_info)
        """
        note_info: dict | None = None
        try:
            success, msg, note_info = self.xhs_apis.get_note_info(note_url, cookies_str, proxies)

            # 防御性检查：API 调用是否成功
            if not success:
                return False, f"API调用失败: {msg}", None

            # 防御性检查：响应是否为 None
            if note_info is None:
                return False, "API返回空响应", None

            # 防御性检查：响应是否为字典
            if not isinstance(note_info, dict):
                return False, f"API返回非预期类型: {type(note_info)}", None

            # 防御性检查：是否存在 data 字段
            if 'data' not in note_info:
                logger.debug(f"API响应缺少'data'字段。可用键: {list(note_info.keys())}")
                return False, "API响应缺少'data'字段", None

            data = note_info['data']

            # 防御性检查：data 是否为 None
            if data is None:
                return False, "API返回data=None", None

            # 防御性检查：是否存在 items 字段
            if 'items' not in data:
                logger.debug(f"API data缺少'items'字段。可用键: {list(data.keys())}")
                return False, "API响应缺少'items'字段（笔记可能已删除或不可访问）", None

            items = data['items']

            # 防御性检查：items 是否为非空列表
            if not isinstance(items, list) or len(items) == 0:
                return False, "API返回空的items列表", None

            # 现在可以安全访问 items[0]
            note_data = items[0]
            note_data['url'] = note_url
            note_info = handle_note_info(note_data)

        except KeyError as e:
            success = False
            msg = f"API响应缺少必要字段: {e}"
            logger.warning(f"{msg}。note_info类型: {type(note_info)}")
        except Exception as e:
            success = False
            msg = f"未预期的错误: {type(e).__name__}: {e}"
            logger.error(msg)

        logger.info(f'爬取笔记信息 {note_url}: {success}, msg: {msg}')
        return success, msg, note_info

    def spider_some_note(self, notes: list[str], cookies_str: str, base_path: dict[str, str], save_choice: str, excel_name: str = '', proxies: dict | None = None, keyword: str | None = None, resume: bool = False) -> None:
        """
        爬取一些笔记的信息
        :param notes: 笔记URL列表
        :param cookies_str: cookies字符串
        :param base_path: 保存路径字典
        :param save_choice: 保存选项
        :param excel_name: Excel文件名
        :param proxies: 代理配置
        :param keyword: 搜索关键词
        :param resume: 是否启用断点续传，跳过已下载的笔记
        :return:
        """
        if save_choice in ('all', 'excel') and excel_name == '':
            raise ValueError('excel_name 不能为空')
        consecutive_success = 0
        note_list = []
        skipped_count = 0
        downloaded_count = 0
        for idx, note_url in enumerate(notes):
            success, msg, note_info = self.spider_note(note_url, cookies_str, proxies)
            if not success:
                consecutive_success = 0
                if '300013' in msg or '访问频繁' in msg:
                    logger.error(f"触发小红书风控(300013)，建议：1. 等待 10-30 分钟后重试 2. 使用代理 3. 降低请求频率")
            if note_info is not None and success:
                # 检查是否已下载（仅在resume=True时）
                if resume:
                    is_downloaded = is_note_downloaded(
                        note_info['note_id'],
                        note_info['title'],
                        note_info['nickname'],
                        note_info['user_id'],
                        keyword,
                        base_path['media']
                    )
                    if is_downloaded:
                        logger.info(f"跳过已下载笔记: {note_info['note_id']} - {note_info['title'][:30]}...")
                        skipped_count += 1
                        note_list.append(note_info)  # 仍加入列表用于Excel
                        continue
                note_list.append(note_info)
                consecutive_success += 1
            # Add delay between notes (not after last one)
            if idx < len(notes) - 1:
                delay = random.uniform(4.0, 8.0)
                logger.debug(f"笔记处理间隔延迟: {delay:.1f} 秒")
                time.sleep(delay)
                # Smart cooling: long pause every 10 successful requests
                if consecutive_success >= 10:
                    cooling_delay = random.uniform(10.0, 20.0)
                    logger.info(f"连续获取10个笔记，冷却 {cooling_delay:.1f} 秒...")
                    time.sleep(cooling_delay)
                    consecutive_success = 0
        # 输出跳过统计
        if resume:
            logger.info(f"断点续传统计: 跳过 {skipped_count} 个已下载笔记，处理 {len(note_list) - skipped_count} 个新笔记")
        for note_info in note_list:
            if save_choice in ('all', 'media', 'media-video', 'media-image'):
                download_note(note_info, base_path['media'], save_choice, keyword=keyword)
        if save_choice in ('all', 'excel'):
            file_path = os.path.abspath(os.path.join(base_path['excel'], f'{excel_name}.xlsx'))
            save_to_xlsx(note_list, file_path)


    def spider_user_all_note(self, user_url: str, cookies_str: str, base_path: dict[str, str], save_choice: str, excel_name: str = '', proxies: dict | None = None) -> tuple[list[str], bool, str]:
        """
        爬取一个用户的所有笔记
        :param user_url:
        :param cookies_str:
        :param base_path:
        :return:
        """
        note_list = []
        try:
            success, msg, all_note_info = self.xhs_apis.get_user_all_notes(user_url, cookies_str, proxies)
            if success:
                logger.info(f'用户 {user_url} 作品数量: {len(all_note_info)}')
                for simple_note_info in all_note_info:
                    note_url = f"https://www.xiaohongshu.com/explore/{simple_note_info['note_id']}?xsec_token={simple_note_info['xsec_token']}"
                    note_list.append(note_url)
            if save_choice in ('all', 'excel'):
                excel_name = user_url.split('/')[-1].split('?')[0]
            self.spider_some_note(note_list, cookies_str, base_path, save_choice, excel_name, proxies)
        except Exception as e:
            success = False
            msg = str(e)
        logger.info(f'爬取用户所有视频 {user_url}: {success}, msg: {msg}')
        return note_list, success, msg

    def spider_some_search_note(self, query: str, require_num: int, cookies_str: str, base_path: dict[str, str], save_choice: str, sort_type_choice: int = 0, note_type: int = 0, note_time: int = 0, note_range: int = 0, pos_distance: int = 0, geo: dict[str, Any] | None = None, excel_name: str = '', proxies: dict | None = None, resume: bool = False) -> tuple[list[str], bool, str]:
        """
            指定数量搜索笔记，设置排序方式和笔记类型和笔记数量
            :param query 搜索的关键词
            :param require_num 搜索的数量
            :param cookies_str 你的cookies
            :param base_path 保存路径
            :param sort_type_choice 排序方式 0 综合排序, 1 最新, 2 最多点赞, 3 最多评论, 4 最多收藏
            :param note_type 笔记类型 0 不限, 1 视频笔记, 2 普通笔记
            :param note_time 笔记时间 0 不限, 1 一天内, 2 一周内天, 3 半年内
            :param note_range 笔记范围 0 不限, 1 已看过, 2 未看过, 3 已关注
            :param pos_distance 位置距离 0 不限, 1 同城, 2 附近 指定这个必须要指定 geo
            返回搜索的结果
        """
        note_list = []
        try:
            success, msg, notes = self.xhs_apis.search_some_note(query, require_num, cookies_str, sort_type_choice, note_type, note_time, note_range, pos_distance, geo, proxies)
            if success:
                notes = list(filter(lambda x: x['model_type'] == "note", notes))
                logger.info(f'搜索关键词 {query} 笔记数量: {len(notes)}')
                for note in notes:
                    note_url = f"https://www.xiaohongshu.com/explore/{note['id']}?xsec_token={note['xsec_token']}"
                    note_list.append(note_url)
            if save_choice in ('all', 'excel'):
                from xhs_utils.data_util import norm_str
                excel_name = norm_str(query)
                # Handle filename conflicts
                excel_path = os.path.join(base_path['excel'], f"{excel_name}.xlsx")
                counter = 1
                original_name = excel_name
                while os.path.exists(excel_path):
                    excel_name = f"{original_name}_{counter}"
                    excel_path = os.path.join(base_path['excel'], f"{excel_name}.xlsx")
                    counter += 1
            self.spider_some_note(note_list, cookies_str, base_path, save_choice, excel_name, proxies, keyword=query, resume=resume)
        except Exception as e:
            success = False
            msg = str(e)
        if not success:
            if '300013' in msg or '访问频繁' in msg:
                logger.error(f"触发小红书风控(300013)，建议：1. 等待 10-30 分钟后重试 2. 使用代理 3. 降低请求频率")
        logger.info(f'搜索关键词 {query} 笔记: {success}, msg: {msg}')
        return note_list, success, msg

if __name__ == '__main__':
    """
        此文件为爬虫的入口文件，可以直接运行
        apis/xhs_pc_apis.py 为爬虫的api文件，包含小红书的全部数据接口，可以继续封装
        apis/xhs_creator_apis.py 为小红书创作者中心的api文件
    """
    import argparse

    parser = argparse.ArgumentParser(description='小红书爬虫')
    parser.add_argument('--resume', action='store_true', help='启用断点续传，跳过已下载的笔记')
    args = parser.parse_args()

    cookies_str_result, base_path_result = init()
    cookies_str: str = cookies_str_result if cookies_str_result is not None else ""
    base_path: dict[str, str] = base_path_result if base_path_result is not None else {}
    if cookies_str is None:
        raise ValueError("COOKIES not found in .env file")
    if base_path is None:
        raise ValueError("Failed to initialize base paths")
    data_spider = Data_Spider()
    """
        save_choice: all: 保存所有的信息, media: 保存视频和图片（media-video只下载视频, media-image只下载图片，media都下载）, excel: 保存到excel
        save_choice 为 excel 或者 all 时，excel_name 不能为空
    """


    # # 1 爬取列表的所有笔记信息 笔记链接 如下所示 注意此url会过期！
    # notes = [
    #     r'https://www.xiaohongshu.com/explore/683fe17f0000000023017c6a?xsec_token=ABBr_cMzallQeLyKSRdPk9fwzA0torkbT_ubuQP1ayvKA=&xsec_source=pc_user',
    # ]
    # data_spider.spider_some_note(notes, cookies_str, base_path, 'all', 'test')

    # # 2 爬取用户的所有笔记信息 用户链接 如下所示 注意此url会过期！
    # user_url = 'https://www.xiaohongshu.com/user/profile/64c3f392000000002b009e45?xsec_token=AB-GhAToFu07JwNk_AMICHnp7bSTjVz2beVIDBwSyPwvM=&xsec_source=pc_feed'
    # data_spider.spider_user_all_note(user_url, cookies_str, base_path, 'all')

    # 3 搜索指定关键词的笔记（多关键词配置模式）
    config = load_keywords_config()
    keywords = config['keywords']
    params = config['global_params']

    success_count = 0
    failed_keywords = []

    for idx, query in enumerate(keywords, 1):
        logger.info(f'[{idx}/{len(keywords)}] Processing keyword: {query}')
        try:
            data_spider.spider_some_search_note(
                query,
                params['require_num'],
                cookies_str,
                base_path,
                params['save_choice'],
                params['sort_type_choice'],
                params['note_type'],
                params['note_time'],
                params['note_range'],
                params['pos_distance'],
                geo=None,
                resume=args.resume
            )
            success_count += 1
            logger.info(f'✓ Completed: {query}')
            # Add delay between keywords (not after last one)
            if idx < len(keywords):
                delay = random.uniform(5.0, 10.0)
                logger.info(f"关键词处理完成，冷却 {delay:.1f} 秒...")
                time.sleep(delay)
        except Exception as e:
            logger.error(f'✗ Failed: {query} - {str(e)}')
            failed_keywords.append((query, str(e)))

    logger.info(f'\n{"="*50}')
    logger.info(f'Crawl Summary:')
    logger.info(f'Total: {len(keywords)} | Success: {success_count} | Failed: {len(failed_keywords)}')
    if failed_keywords:
        logger.info(f'Failed keywords:')
        for kw, err in failed_keywords:
            logger.info(f'  - {kw}: {err}')
