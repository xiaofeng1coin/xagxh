# modules/electricity.py
from flask import Blueprint, request, jsonify
import requests
import datetime
import calendar
import logging
import config # 导入配置
from utils import logger, speak, format_for_tts

bp = Blueprint('electricity', __name__, url_prefix='/electricity')

def get_electricity_info():
    logger.info(">>> 开始执行电费查询任务")
    
    # 检查配置
    if not config.YUXIAOR_TOKEN or not config.CONTRACT_ID:
        logger.error("请在 config.py 中填写 YUXIAOR_TOKEN 和 CONTRACT_ID")
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
        "contractId": config.CONTRACT_ID, # 引用配置
        "meterValueId": "0",
        "pageSize": "30",
        "pageNum": "1",
        "startDate": f"{fmt_year}-{fmt_month}-01 00:00:00",
        "endDate": f"{fmt_year}-{fmt_month}-{fmt_last_day} 23:59:59"
    }

    headers = {
        "xxx-yuxiaor-token": config.YUXIAOR_TOKEN, # 引用配置
        "user-agent": "YuxiaorC/1.8.1 (com.yuxiaor.c.change; build:3817; android PLQ110_16.0.0.207(CN01))",
        "accept-encoding": "gzip",
        "host": "api.yuxiaor.com",
        "content-type": "application/json; charset=utf-8"
    }

    try:
        logger.info(f"正在请求电费API...")
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status() 
        
        result = response.json()
        error_code = str(result.get("errorCode"))

        if error_code == "0" and result.get("data") and result["data"].get("data"):
            data_list = result["data"]["data"]
            if not data_list:
                return "未查询到本月数据，请稍后再试。"
            
            data_item = data_list[0]
            try:
                balance = float(data_item.get("totalAmount", 0))
                yesterday_cost = abs(float(data_item.get("subtotalAmount", 0)))
            except ValueError:
                return "电费数据解析错误。"

            str_balance = format_for_tts(balance)
            str_yesterday = format_for_tts(yesterday_cost)

            msg = f"跟着我说，当前电费余额{str_balance}元，{fmt_yesterday_month}月{fmt_yesterday_day}日消费{str_yesterday}元。"
            if balance < 20:
                msg += "注意，您的电费余额已不足20元，请及时充值。"
            return msg
        else:
            logger.error(f"API返回异常: {result}")
            return "电费查询失败，接口返回异常。"

    except Exception as e:
        logger.exception("请求过程发生异常")
        return "查询出错，系统发生连接异常。"

@bp.route('/check', methods=['GET', 'POST'])
def check_bill():
    client_ip = request.remote_addr
    logger.info(f"收到查电费请求，来源IP: {client_ip}")
    result_text = get_electricity_info()
    speak(result_text)
    return jsonify({"status": "ok", "msg": result_text})
