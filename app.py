# app.py
from flask import Flask, request
import requests
import json
import datetime
import calendar
import logging
import sys
import os  # 新增：用于读取环境变量

# ================= 配置区域 (改为从环境变量获取) =================
# 如果环境变量不存在，第二个参数作为默认值，或者直接为 None
YUXIAOR_TOKEN = os.getenv("YUXIAOR_TOKEN")
CONTRACT_ID = os.getenv("CONTRACT_ID")

HA_BASE_URL = os.getenv("HA_URL")
HA_TOKEN = os.getenv("HA_TOKEN")
SPEAKER_ENTITY_ID = os.getenv("PLAYER_ENTITY_ID")

# 简单的检查，防止配置漏填
if not all([YUXIAOR_TOKEN, CONTRACT_ID, HA_BASE_URL, HA_TOKEN, SPEAKER_ENTITY_ID]):
    print("【严重错误】环境变量缺失！请检查 deploy.sh 中的配置。")
# =============================================================

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

def get_electricity_info():
    """查询电费逻辑"""
    logger.info(">>> 开始执行电费查询任务")
    
    # 再次检查配置
    if not YUXIAOR_TOKEN or not CONTRACT_ID:
        logger.error("缺少电费Token或户号")
        return "系统配置错误，缺少必要的电费查询凭证。"

    now = datetime.datetime.now()
    year = now.year
    month = now.month
    
    _, last_day = calendar.monthrange(year, month)
    fmt_year = str(year)
    fmt_month = f"{month:02d}"
    fmt_last_day = f"{last_day:02d}"
    
    yesterday_date = now - datetime.timedelta(days=1)
    fmt_yesterday_month = f"{yesterday_date.month:02d}"
    fmt_yesterday_day = f"{yesterday_date.day:02d}"

    url = "https://api.yuxiaor.com/api-service-server/tapp/v1/intelligent/meter/meter-operation-log"
    
    params = {
        "meterType": "2",
        "contractId": CONTRACT_ID,
        "meterValueId": "0",
        "pageSize": "30",
        "pageNum": "1",
        "startDate": f"{fmt_year}-{fmt_month}-01 00:00:00",
        "endDate": f"{fmt_year}-{fmt_month}-{fmt_last_day} 23:59:59"
    }

    headers = {
        "xxx-yuxiaor-token": YUXIAOR_TOKEN,
        "user-agent": "YuxiaorC/1.8.1 (com.yuxiaor.c.change; build:3817; android PLQ110_16.0.0.207(CN01))",
        "accept-encoding": "gzip",
        "host": "api.yuxiaor.com",
        "content-type": "application/json; charset=utf-8"
    }

    try:
        logger.info(f"正在请求电费API...")
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        logger.info(f"API响应状态码: {response.status_code}")
        
        response.raise_for_status()
        result = response.json()

        if result.get("errorCode") == 0 and result.get("data") and result["data"].get("data"):
            data_list = result["data"]["data"]
            if not data_list:
                logger.warning("API返回成功，但数据列表为空")
                return "未查询到本月数据，请稍后再试。"
                
            data_item = data_list[0]
            
            try:
                balance = float(data_item.get("totalAmount", 0))
                yesterday_cost = abs(float(data_item.get("subtotalAmount", 0)))
            except ValueError:
                logger.error("数据格式转换错误")
                return "电费数据解析错误。"

            logger.info(f"解析成功 -> 余额: {balance}, 昨日: {yesterday_cost}")

            msg = f"当前电费余额{balance}元，{fmt_yesterday_month}月{fmt_yesterday_day}日消费{yesterday_cost}元。"
            
            if balance < 20:
                logger.info("触发低余额提醒 (<20元)")
                msg += "注意，您的电费余额已不足20元，请及时充值。"
            
            return msg
        else:
            logger.error(f"API业务逻辑错误: {result}")
            return "电费查询失败，接口返回异常。"

    except Exception as e:
        logger.exception("请求过程发生异常")
        return "查询出错，系统发生连接异常。"

def speak(text):
    """调用HA让小爱说话"""
    if not HA_BASE_URL or not HA_TOKEN or not SPEAKER_ENTITY_ID:
        logger.error("HA配置缺失，无法语音播报")
        return

    logger.info(f"准备发送TTS指令: {text}")
    
    url = f"{HA_BASE_URL}/api/services/xiaomi_miot/intelligent_speaker"
    
    headers = {
        "Authorization": f"Bearer {HA_TOKEN}",
        "Content-Type": "application/json",
    }
    
    data = {
        "entity_id": SPEAKER_ENTITY_ID,
        "text": text,
        "execute": True 
    }

    try:
        resp = requests.post(url, json=data, headers=headers, timeout=5)
        logger.info(f"HA TTS响应: {resp.status_code} - {resp.text}")
    except Exception as e:
        logger.error(f"连接HA TTS服务失败: {e}")

@app.route('/check', methods=['GET', 'POST'])
def check_bill():
    client_ip = request.remote_addr
    logger.info(f"收到触发请求，来源IP: {client_ip}")
    
    result_text = get_electricity_info()
    speak(result_text)
    
    return json.dumps({"status": "ok", "msg": result_text}, ensure_ascii=False)

if __name__ == '__main__':
    logger.info("服务启动，监听端口 5000")
    app.run(host='0.0.0.0', port=5000)
