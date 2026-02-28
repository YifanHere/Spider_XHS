import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor

import requests
from loguru import logger
from retry import retry


def timestamp_to_str(timestamp):
    """
    将时间戳转换为日期时间字符串
    :param timestamp: 时间戳（毫秒或秒）
    :return: 格式化的日期时间字符串
    """
    try:
        # 如果时间戳是毫秒，转换为秒
        if timestamp > 1e10:
            timestamp = timestamp / 1000
        return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp))
    except Exception as e:
        logger.error(f'时间戳转换错误: {e}')
        return '未知'


def handle_note_info(data):
    note_id = data['note_card']['note_id']
    note_url = data['note_card']['note_url']
    note_type = data['note_card']['type']
    user_id = data['note_card']['user']['user_id']
    home_url = f'https://www.xiaohongshu.com/user/profile/{user_id}'
    nickname = data['note_card']['user']['nickname']
    avatar = data['note_card']['user']['avatar']
    title = data['note_card']['title']
    desc = data['note_card']['desc']
    liked_count = data['note_card']['interact_info']['liked_count']
    collected_count = data['note_card']['interact_info']['collected_count']
    comment_count = data['note_card']['interact_info']['comment_count']
    share_count = data['note_card']['interact_info']['share_count']
    image_list = []
    for image in data['note_card']['image_list']:
        try:
            image_list.append(image['info_list'][1]['url'])
            # success, msg, img_url = XHS_Apis.get_note_no_water_img(image['info_list'][1]['url'])
            # image_list.append(img_url)
        except:
            pass
    if note_type == '视频':
        video_cover = image_list[0] if image_list else None
        video_addr = None
        
        try:
            # 方法1：从API数据中获取视频地址（多编码支持）
            video_data = data['note_card'].get('video', {}).get('media', {})
            logger.debug(f"视频数据结构: {json.dumps(video_data, ensure_ascii=False, indent=2)}")
            
            stream = video_data.get('stream', {})
            
            # 按优先级尝试不同编码格式
            for codec in ['h264', 'h265', 'av1']:
                if codec in stream and len(stream[codec]) > 0:
                    video_addr = stream[codec][0].get('master_url') or stream[codec][0].get('url')
                    if video_addr:
                        logger.info(f"成功获取视频地址({codec}): {video_addr}")
                        break
            
            # 方法1.5：使用 origin_video_key 备选（上游优点）
            if not video_addr:
                video_info = data.get('note_card', {}).get('video', {})
                if 'consumer' in video_info:
                    origin_key = video_info['consumer'].get('origin_video_key')
                    if origin_key:
                        video_addr = f"https://sns-video-bd.xhscdn.com/{origin_key}"
                        logger.info(f"方法1.5使用origin_video_key获取视频地址: {video_addr}")
            
            # 方法2：如果所有格式都失败，抛出异常进入方法2
            if not video_addr:
                raise KeyError("stream中未找到可用的视频URL")
                
        except (KeyError, TypeError, IndexError) as e:
            # 方法2：使用备用方法获取视频地址
            logger.warning(f"方法1获取视频地址失败 ({e})，尝试备用方法2")
            try:
                from apis.xhs_pc_apis import XHS_Apis
                success, msg, video_addr = XHS_Apis.get_note_no_water_video(note_id)
                if not success or not video_addr:
                    logger.error(f"方法2也失败: {msg}")
                    video_addr = None
                else:
                    logger.info(f"方法2成功获取视频地址")
            except Exception as e2:
                logger.error(f"方法2执行异常: {e2}")
                video_addr = None
    else:
        video_cover = None
        video_addr = None
    tags_temp = data['note_card']['tag_list']
    tags = []
    for tag in tags_temp:
        try:
            tags.append(tag['name'])
        except:
            pass
    upload_time = timestamp_to_str(data['note_card']['time'])
    if 'ip_location' in data['note_card']:
        ip_location = data['note_card']['ip_location']
    else:
        ip_location = '未知'
    return {
        'note_id': note_id,
        'note_url': note_url,
        'note_type': note_type,
        'user_id': user_id,
        'home_url': home_url,
        'nickname': nickname,
        'avatar': avatar,
        'title': title,
        'desc': desc,
        'liked_count': liked_count,
        'collected_count': collected_count,
        'comment_count': comment_count,
        'share_count': share_count,
        'video_cover': video_cover,
        'video_addr': video_addr,
        'image_list': image_list,
        'tags': tags,
        'upload_time': upload_time,
        'ip_location': ip_location,
    }

def handle_comment_info(data):
    note_id = data['note_id']
    note_url = data['note_url']
    comment_id = data['id']
    user_id = data['user_info']['user_id']
    home_url = f'https://www.xiaohongshu.com/user/profile/{user_id}'
    nickname = data['user_info']['nickname']
    avatar = data['user_info']['image']
    content = data['content']
    show_tags = data['show_tags']
    like_count = data['like_count']
    upload_time = timestamp_to_str(data['create_time'])
    try:
        ip_location = data['ip_location']
    except:
        ip_location = '未知'
    pictures = []
    try:
        pictures_temp = data['pictures']
        for picture in pictures_temp:
            try:
                pictures.append(picture['info_list'][1]['url'])
                # success, msg, img_url = XHS_Apis.get_note_no_water_img(picture['info_list'][1]['url'])
                # pictures.append(img_url)
            except:
                pass
    except:
        pass
    return {
        'note_id': note_id,
        'note_url': note_url,
        'comment_id': comment_id,
        'user_id': user_id,
        'home_url': home_url,
        'nickname': nickname,
        'avatar': avatar,
        'content': content,
        'show_tags': show_tags,
        'like_count': like_count,
        'upload_time': upload_time,
        'ip_location': ip_location,
        'pictures': pictures,
    }


def handle_user_info(data):
    user_id = data['basic_info']['user_id']
    home_url = f'https://www.xiaohongshu.com/user/profile/{user_id}'
    nickname = data['basic_info']['nickname']
    avatar = data['basic_info']['image']
    desc = data['basic_info']['desc']
    follows = data['interactions'][0]['count']
    fans = data['interactions'][1]['count']
    interaction = data['interactions'][2]['count']
    tags_temp = data['tags']
    tags = []
    for tag in tags_temp:
        try:
            tags.append(tag['name'])
        except:
            pass
    return {
        'user_id': user_id,
        'home_url': home_url,
        'nickname': nickname,
        'avatar': avatar,
        'desc': desc,
        'follows': follows,
        'fans': fans,
        'interaction': interaction,
        'tags': tags,
    }


def get_html_text(url):
    headers = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36',
    }
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    r.encoding = r.apparent_encoding
    return r.text


def norm_str(s):
    if not s:
        return ''
    # 去除前后空格
    s = s.strip()
    # 替换Windows文件名非法字符
    s = s.replace('\\', '_').replace('/', '_').replace(':', '_').replace('*', '_').replace('?', '_').replace('"', '_').replace('<', '_').replace('>', '_').replace('|', '_')
    # 替换换行符和制表符
    s = s.replace('\n', '_').replace('\r', '_').replace('\t', '_')
    # 去除前后空格
    s = s.strip()
    # 限制长度，避免文件名过长
    return s[:80]


def get_data_excel(path, data_list):
    """
    将数据列表保存到Excel文件
    :param path: Excel文件路径
    :param data_list: 数据列表
    """
    import pandas as pd
    df = pd.DataFrame(data_list)
    df.to_excel(path, index=False)
    logger.info(f'数据已保存到: {path}')


@retry(tries=3, delay=1)
def download_media(url, path, proxies=None):
    """
    下载媒体文件（图片或视频）
    :param url: 媒体URL
    :param path: 保存路径
    :param proxies: 代理配置
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36',
        }
        response = requests.get(url, headers=headers, proxies=proxies, timeout=30)
        response.raise_for_status()
        with open(path, 'wb') as f:
            f.write(response.content)
        logger.info(f'下载成功: {path}')
        return True
    except Exception as e:
        logger.error(f'下载失败 {url}: {e}')
        raise


def download_note(note_info, save_dir, download_media_files=True, proxies=None):
    """
    下载笔记的媒体文件和元数据
    :param note_info: 笔记信息字典
    :param save_dir: 保存目录
    :param download_media_files: 是否下载媒体文件
    :param proxies: 代理配置
    :return: 保存的目录路径
    """
    note_id = note_info['note_id']
    note_type = note_info['note_type']
    title = norm_str(note_info['title'])[:40]
    nickname = norm_str(note_info['nickname'])[:20]
    user_id = note_info['user_id']
    
    # 创建保存目录
    note_dir = os.path.join(save_dir, f"{nickname}_{user_id}", f"{title}_{note_id}")
    os.makedirs(note_dir, exist_ok=True)
    
    # 保存元数据
    info_path = os.path.join(note_dir, 'info.json')
    with open(info_path, 'w', encoding='utf-8') as f:
        json.dump(note_info, f, ensure_ascii=False, indent=2)
    
    if not download_media_files:
        logger.info(f'跳过媒体下载: {note_dir}')
        return note_dir
    
    # 下载图片
    image_list = note_info.get('image_list', [])
    for i, img_url in enumerate(image_list):
        try:
            img_path = os.path.join(note_dir, f'image_{i+1}.jpg')
            download_media(img_url, img_path, proxies)
        except Exception as e:
            logger.error(f'下载图片失败: {e}')
    
    # 下载视频
    video_addr = note_info.get('video_addr')
    if video_addr:
        try:
            video_path = os.path.join(note_dir, 'video.mp4')
            download_media(video_addr, video_path, proxies)
        except Exception as e:
            logger.error(f'下载视频失败: {e}')
    
    logger.info(f'笔记下载完成: {note_dir}')
    return note_dir


def batch_download_notes(note_info_list, save_dir, max_workers=3, download_media_files=True, proxies=None):
    """
    批量下载笔记
    :param note_info_list: 笔记信息列表
    :param save_dir: 保存目录
    :param max_workers: 最大并发数
    :param download_media_files: 是否下载媒体文件
    :param proxies: 代理配置
    """
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for note_info in note_info_list:
            future = executor.submit(download_note, note_info, save_dir, download_media_files, proxies)
            futures.append(future)
        
        for future in futures:
            try:
                future.result()
            except Exception as e:
                logger.error(f'批量下载失败: {e}')
