import json
import os
import re


def norm_str(str):
    """
    规范化字符串，移除非法字符和换行符
    
    :param str: 原始字符串
    :return: 规范化后的字符串
    """
    new_str = re.sub(r"|[\\/:*?\"<>| ]+", "", str).replace('\n', '').replace('\r', '')
    return new_str


def build_note_path(note_info, base_path, keyword=None):
    """
    构建笔记保存路径
    
    路径格式:
    - 有keyword: base_path/keyword/nickname_user_id/title_note_id
    - 无keyword: base_path/nickname_user_id/title_note_id
    
    :param note_info: 笔记信息字典，包含 note_id, title, nickname, user_id
    :param base_path: 基础保存路径
    :param keyword: 搜索关键词（可选）
    :return: 构建的保存路径
    """
    note_id = note_info['note_id']
    user_id = note_info['user_id']
    title = note_info['title']
    title = norm_str(title)[:40]
    nickname = note_info['nickname']
    nickname = norm_str(nickname)[:20]
    if title.strip() == '':
        title = f'无标题'
    if keyword:
        keyword_safe = norm_str(keyword)[:50]
        save_path = f'{base_path}/{keyword_safe}/{nickname}_{user_id}/{title}_{note_id}'
    else:
        save_path = f'{base_path}/{nickname}_{user_id}/{title}_{note_id}'
    return save_path


def extract_note_id_from_url(url):
    """
    从URL中提取note_id
    
    支持格式:
    - https://www.xiaohongshu.com/explore/abc123
    - https://www.xiaohongshu.com/explore/abc123?xsec_token=xxx
    
    :param url: 小红书笔记URL
    :return: note_id字符串，提取失败返回None
    """
    if not url:
        return None
    
    # 匹配 /explore/ 后面的 note_id
    match = re.search(r'/explore/([a-zA-Z0-9]+)', url)
    if match:
        return match.group(1)
    
    return None


def get_note_info_path(note_id, title, nickname, user_id, keyword, base_path):
    """
    获取笔记的info.json文件路径
    
    :param note_id: 笔记ID
    :param title: 笔记标题
    :param nickname: 用户昵称
    :param user_id: 用户ID
    :param keyword: 搜索关键词（可为None）
    :param base_path: 基础保存路径
    :return: info.json的完整路径
    """
    note_info = {
        'note_id': note_id,
        'title': title,
        'nickname': nickname,
        'user_id': user_id
    }
    save_path = build_note_path(note_info, base_path, keyword)
    return f'{save_path}/info.json'


def is_note_downloaded(note_id, title, nickname, user_id, keyword, base_path):
    """
    检查笔记是否已下载完成
    
    检查逻辑:
    1. info.json文件是否存在
    2. info.json中是否有download_completed字段且值为True
    
    注意: 旧的info.json可能缺少download_completed字段，应视为未下载
    
    :param note_id: 笔记ID
    :param title: 笔记标题
    :param nickname: 用户昵称
    :param user_id: 用户ID
    :param keyword: 搜索关键词（可为None）
    :param base_path: 基础保存路径
    :return: True表示已下载完成，False表示未下载或下载未完成
    """
    info_path = get_note_info_path(note_id, title, nickname, user_id, keyword, base_path)
    
    # 检查info.json是否存在
    if not os.path.exists(info_path):
        return False
    
    try:
        with open(info_path, mode='r', encoding='utf-8') as f:
            info_data = json.load(f)
        
        # 检查download_completed字段是否存在且为True
        if info_data.get('download_completed') is True:
            return True
        else:
            # 缺少download_completed字段或值为False，视为未下载完成
            return False
    except (json.JSONDecodeError, IOError):
        # JSON解析失败或读取失败，视为未下载
        return False
