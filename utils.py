# utils.py
import logging
import sys
import requests
import config  # 导入配置文件

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger("SharedUtils")

def format_for_tts(num):
    """将数字转换为适合TTS朗读的格式"""
    try:
        s = str(num)
        if '.' in s:
            int_part, dec_part = s.split('.')
            trans_map = str.maketrans("0123456789", "零一二三四五六七八九")
            dec_part_chinese = dec_part.translate(trans_map)
            return f"{int_part}点{dec_part_chinese}"
        else:
            return s
    except Exception as e:
        logger.error(f"格式化数字出错: {e}")
        return str(num)

def speak(text):
    """调用HA让小爱说话"""
    # 直接使用 config 中的变量
    if not config.HA_URL or not config.HA_TOKEN or not config.SPEAKER_ENTITY_ID:
        logger.error("配置缺失，请检查 config.py")
        return

    logger.info(f"准备发送TTS指令: {text}")
    url = f"{config.HA_URL}/api/services/xiaomi_miot/intelligent_speaker"
    
    headers = {
        "Authorization": f"Bearer {config.HA_TOKEN}",
        "Content-Type": "application/json",
    }
    
    data = {
        "entity_id": config.SPEAKER_ENTITY_ID,
        "text": text,
        "execute": True 
    }

    try:
        resp = requests.post(url, json=data, headers=headers, timeout=5)
        logger.info(f"HA TTS响应: {resp.status_code}")
    except Exception as e:
        logger.error(f"连接HA TTS服务失败: {e}")
