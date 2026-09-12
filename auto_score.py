#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import hashlib
import json
import logging
import os
import random
import sys
import time
from datetime import datetime

import requests

# ══════════════════════════════════════════════════════════════
#  全局配置
# ══════════════════════════════════════════════════════════════
SALT = 'aslkdvcniu34h9tgufh278wv2'
BASE_URL = 'https://i.ilife798.com'
VERSION_CODE = '3.1.7'
VERSION_NUM = '31007'
SESSION_FILE = 'ilife_accounts.json'

ACCOUNTS = []


class C:
    R = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    GRN = '\033[92m'
    YEL = '\033[93m'
    CYA = '\033[96m'


if os.name == 'nt':
    os.system('')

# [修复1]: 显式指定 stream=sys.stdout，彻底杜绝终端默认将 stderr 标红的问题
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    stream=sys.stdout
)


# ══════════════════════════════════════════════════════════════
#  配置持久化
# ══════════════════════════════════════════════════════════════
def load_config():
    global ACCOUNTS
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, 'r', encoding='utf-8') as f:
                ACCOUNTS = json.load(f)
        except Exception as e:
            logging.error(f"读取本地配置文件失败: {e}")


def save_config():
    try:
        with open(SESSION_FILE, 'w', encoding='utf-8') as f:
            json.dump(ACCOUNTS, f, ensure_ascii=False, indent=4)
        print(f"  {C.GRN}✅ 账号矩阵已保存至: {SESSION_FILE}{C.R}")
    except Exception as e:
        logging.error(f"保存配置文件失败: {e}")


# ══════════════════════════════════════════════════════════════
#  网络通信与签名
# ══════════════════════════════════════════════════════════════
def get_sign(business_id: str, token: str, uid: str) -> str:
    now_ms = int(time.time() * 1000)
    token8 = token[-8:] if token else ""
    uid8 = uid[-8:] if uid else ""
    n = (now_ms // 10000) * 10
    plain = business_id + str(n) + token8 + uid8 + SALT
    return hashlib.md5(plain.encode("utf-8")).hexdigest()


def get_headers(token: str):
    headers = {
        'user-agent': f'Android_ilife798_{VERSION_CODE}',
        'VersionCode': VERSION_NUM,
        'ApplicationType': '1,1',
        'Content-Type': 'application/json; charset=utf-8',
        'Accept': 'application/json',
    }
    if token:
        headers['Authorization'] = token
    return headers


def api_get(path, token: str, params=None):
    try:
        return requests.get(BASE_URL + path, params=params, headers=get_headers(token), timeout=20)
    except Exception as e:
        logging.error(f"GET 异常: {e}")
        return None


def api_post(path, token: str, params=None, json_body=None):
    try:
        return requests.post(BASE_URL + path, params=params, json=json_body, headers=get_headers(token), timeout=20)
    except Exception as e:
        logging.error(f"POST 异常: {e}")
        return None


def verify_session(acc: dict) -> bool:
    if not acc.get('token'):
        return False
    r = api_get('/api/v1/acc/stat', token=acc['token'])
    if not r:
        return False
    try:
        return str(r.json().get('code', r.json().get('status'))) in ('0', '200', 'None')
    except Exception:
        return False


# ══════════════════════════════════════════════════════════════
#  多账号录入
# ══════════════════════════════════════════════════════════════
def interactive_login(default_phone=""):
    print(f"\n{C.BOLD}{C.YEL}--- 正在录入账号凭证 ---{C.R}")
    phone = input(f"  {C.CYA}请输入手机号 [{default_phone}]: {C.R}").strip() or default_phone
    if not phone:
        return None

    seed = random.random()
    ts = int(time.time() * 1000)
    print(f"  {C.DIM}验证码链接: {BASE_URL}/api/v1/captcha/?s={seed}&r={ts}{C.R}")
    auth_code = input(f"  {C.CYA}请输入图形验证码: {C.R}").strip()

    r = api_post('/api/v1/acc/login/code', token="", json_body={"un": phone, "authCode": auth_code, "s": seed})
    if str((r.json() if r else {}).get('code')) != '0':
        print(f"  {C.YEL}⚠️ 验证码下发失败，请重试。{C.R}")
        return None

    print(f"  {C.GRN}✅ 短信已下发！{C.R}")
    sms_code = input(f"  {C.CYA}请输入短信验证码: {C.R}").strip()

    r_login = api_post('/api/v1/acc/login', token="", json_body={"un": phone, "authCode": sms_code, "openCode": ""})
    res_login = r_login.json() if r_login else {}

    if str(res_login.get('code')) == '0':
        inner = res_login.get('data', {})
        print(f"  {C.GRN}✅ 登录成功！{C.R}")
        return {'phone': phone, 'token': inner['al']['token'], 'uid': inner['al']['uid']}
    return None


def setup_accounts_menu():
    global ACCOUNTS
    load_config()
    valid_accs = []
    for acc in ACCOUNTS:
        print(f"  {C.DIM}校验账号 {acc['phone']}...{C.R}")
        if verify_session(acc):
            print(f"  {C.GRN}✅ 凭证有效{C.R}")
            valid_accs.append(acc)
        else:
            print(f"  {C.YEL}⚠️ 凭证失效，请重新登录{C.R}")
            new_acc = interactive_login(default_phone=acc['phone'])
            if new_acc:
                valid_accs.append(new_acc)

    ACCOUNTS = valid_accs
    while True:
        ans = input(f"\n  {C.BOLD}当前有效账号数: {len(ACCOUNTS)}。是否添加新账号？[y/N]: {C.R}").strip().lower()
        if ans == 'y':
            new_acc = interactive_login()
            if new_acc:
                ACCOUNTS = [a for a in ACCOUNTS if a['phone'] != new_acc['phone']]
                ACCOUNTS.append(new_acc)
        else:
            break

    if not ACCOUNTS:
        print(f"  {C.YEL}无有效账号，退出。{C.R}")
        sys.exit(1)

    save_config()


# ══════════════════════════════════════════════════════════════
#  单账号执行逻辑
# ══════════════════════════════════════════════════════════════
def process_single_account(acc: dict, skip_verify=False):
    token, uid, phone = acc['token'], acc['uid'], acc['phone']

    if not skip_verify and not verify_session(acc):
        logging.warning(f"账号 {phone} Token 已失效，跳过。")
        return

    r = api_get('/api/v1/acc/score/mission-lst', token=token)
    if not r or r.status_code != 200:
        logging.error(f"获取任务列表失败: {phone}")
        return

    data = r.json()
    inner = data.get('data', {})
    acc_info = inner.get('accScoreRsp') or {}
    logging.info(f"当前有效积分: {acc_info.get('score', 0)}  |  累计总积分: {acc_info.get('totalScore', 0)}")

    # [修复2]: 提取动态限制字典。服务端的 limit 实际代表【剩余可领次数】
    # 示例: [{'limit': 0, 'refId': 'popsreen'}] -> 剩余 0 次
    remain_dict = {}
    for l_info in acc_info.get('limits', []):
        ref = l_info.get('refId')
        val = l_info.get('limit')
        if ref and val is not None:
            remain_dict[ref] = int(val)

    tasks = []
    daily = inner.get('dailyRSP') or {}
    daily_info = acc_info.get('daily', {})

    # 1. 签到校验 (根据 ltime 确认今日是否已完成)
    ltime = daily_info.get('ltime', 0)
    is_signed_today = False
    if ltime:
        try:
            last_date = datetime.fromtimestamp(int(ltime) / 1000).date()
            if last_date == datetime.now().date():
                is_signed_today = True
        except Exception:
            pass

    if daily.get('adId'):
        if not is_signed_today:
            tasks.append({
                'name': '每日签到', 'refId': daily.get('adId'),
                'score': int(daily.get('score', 5)), 'type': 1,
                'week': daily_info.get('week'),
                'runs_needed': 1
            })
        else:
            logging.info(f"  -> [跳过] 每日签到: 今日已完成")

    # 2. 任务列表解析
    for m in inner.get('missions') or []:
        name = m.get('name', '')
        refId = m.get('refId', '')
        score = int(m.get('score', 0))

        # 过滤无效、跳转或非正常的权益任务
        if score == 0 or m.get('url') or '权益' in name or score > 100:
            continue

        # 如果服务端动态 limits 明确指定了该任务的剩余配额，以此为准
        if refId in remain_dict:
            remain_runs = remain_dict[refId]
        else:
            # 兜底计算
            base_limit = int(m.get('limit', 1))
            if base_limit <= 0:
                base_limit = 5
            remain_runs = max(0, base_limit - max(0, int(m.get('cnt', 0))))

        task_type = 2
        if refId == 'popsreen' or '广告' in name or '全屏' in name:
            task_type = 4

        if remain_runs > 0:
            tasks.append({
                'name': name, 'refId': refId, 'score': score,
                'type': task_type, 'week': None,
                'runs_needed': remain_runs
            })
        else:
            logging.info(f"  -> [跳过] {name}: 剩余次数为 0，已全部完成")

    if not tasks:
        logging.info("所有可用任务均已达上限，无需执行。")

    for idx, target in enumerate(tasks, 1):
        total_runs = target['runs_needed']
        logging.info(
            f"队列 [{idx}/{len(tasks)}]: {target['name']} (剩余待执行: {total_runs} 次, TaskType: {target['type']})")

        for r_idx in range(total_runs):
            sign = get_sign(target['refId'], token, uid)
            body = {
                "adId": target['refId'],
                "type": 101,
                "weekday": target['week'],
                "addScoreType": target['type'],
                "addScore": target['score']
            }
            body = {k: v for k, v in body.items() if v is not None}

            r_post = api_post('/api/v1/acc/score/score-send', token=token, params={'sign': sign, 's': 0},
                              json_body=body)

            should_break = False
            if r_post:
                res = r_post.json()
                code = str(res.get('code', res.get('status')))
                if code in ('0', '200', 'None'):
                    logging.info(f"  -> 第 {r_idx + 1}/{total_runs} 次上报成功 (服务端: {res.get('msg', 'OK')})")
                else:
                    logging.warning(
                        f"  -> 第 {r_idx + 1}/{total_runs} 次失败: [{code}] {res.get('msg')}，跳过当前任务剩余次数")
                    should_break = True
            else:
                should_break = True

            time.sleep(random.uniform(12.0, 18.0))
            if should_break:
                break

    # 3. 最终积分回显
    logging.info(f"--- 账号 {phone} 最终积分结算 ---")
    r_final = api_get('/api/v1/acc/score/mission-lst', token=token)
    if r_final and r_final.status_code == 200:
        final_data = r_final.json().get('data', {}).get('accScoreRsp', {})
        logging.info(
            f"✅ 账号 {phone} 最新有效积分: {final_data.get('score', 0)}  |  累计总积分: {final_data.get('totalScore', 0)}")


# ══════════════════════════════════════════════════════════════
#  多账号宏观调度
# ══════════════════════════════════════════════════════════════
def execute_daily_routine(skip_verify=False):
    logging.info(">>> 开始执行每日多账号自动化流水线 <<<")
    for idx, acc in enumerate(ACCOUNTS, 1):
        logging.info(f"\n[{idx}/{len(ACCOUNTS)}] 正在处理账号: {acc['phone']} {'=' * 20}")
        process_single_account(acc, skip_verify)
        if idx < len(ACCOUNTS):
            wait_time = random.uniform(20.0, 45.0)
            logging.info(f"账号切换等待 {wait_time:.1f} 秒...")
            time.sleep(wait_time)
    logging.info(">>> 今日全部账号流水线执行完毕 <<<\n")


def run_scheduler(target_time="08:15"):
    logging.info(f"后台调度启动，定时每日 {target_time} 执行，挂机中...")
    while True:
        try:
            if datetime.now().strftime("%H:%M") == target_time:
                execute_daily_routine()
                time.sleep(61)
            else:
                time.sleep(20)
        except KeyboardInterrupt:
            logging.info("手动终止程序。")
            break
        except Exception as e:
            time.sleep(60)


if __name__ == '__main__':
    print(f"{C.CYA}=== 慧生活798 自动化辅助系统 (多账号版) ==={C.R}")
    setup_accounts_menu()
    execute_daily_routine(skip_verify=True)
    run_scheduler(target_time="08:15")