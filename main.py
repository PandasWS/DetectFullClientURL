import requests
import concurrent.futures
import datetime
import time
import random
import threading
from queue import Queue, Empty
import sys
import signal

# 配置参数
base_url_configs = [
    {
        "name": "RAG Main Setup",
        "base_url": "http://rofull.gnjoy.com/RAG_SETUP_{}.exe",
        "start_date": "200304",
        "date_format": "%y%m%d",
    },
    {
        "name": "Zero Main Setup",
        "base_url": "http://rofull.gnjoy.com/ZERO_SETUP_{}.exe",
        "start_date": "200304",
        "date_format": "%y%m%d",
    },
    {
        "name": "RAG Main (Files)",
        "base_url": "http://rofull.gnjoy.com/Ragnarok_{}.zip",
        "start_date": "200304",
        "date_format": "%y%m%d",
    },
    {
        "name": "Zero Main (Files)",
        "base_url": "http://rofull.gnjoy.com/RagnarokZero_{}.zip",
        "start_date": "200304",
        "date_format": "%y%m%d",
    },
    {
        "name": "RAG Sakray (Files)",
        "base_url": "http://rofull.gnjoy.com/RAG_SETUP_{}_SAK.zip",
        "start_date": "211028",
        "date_format": "%y%m%d",
    },
    {
        "name": "Zero Sakray (Files)",
        "base_url": "http://rofull.gnjoy.com/ROZ_SETUP_{}_Sak.zip",
        "start_date": "20221021",
        "date_format": "%Y%m%d",
    },
]
end_date = datetime.datetime.now()
threads_count = 10
cooldown = 0
output_file = "valid_links.txt"

user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
    "Mozilla/5.0 (Windows NT 10.0; WOW64; rv:45.0) Gecko/20100101 Firefox/45.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.1 Safari/605.1.15",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 10; SM-G975F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.72 Mobile Safari/537.36",
]

stop_event = threading.Event()


def save_valid_link(url, content_length):
    """
    保存有效链接到输出文件

    参数:
    url (str): 有效链接的 URL
    content_length (int): 链接内容的大小(以字节为单位)
    """
    if content_length < 100 * 1024**2:
        return

    if content_length >= 1024**3:
        size = content_length / (1024**3)
        unit = "GB"
    elif content_length >= 1024**2:
        size = content_length / (1024**2)
        unit = "MB"
    elif content_length >= 1024:
        size = content_length / 1024
        unit = "KB"
    else:
        size = content_length
        unit = "Bytes"

    size_str = f"{size:.2f} {unit}"
    print(f"[FOUND] {url} | Size: {size_str}")
    with open(output_file, "a") as f:
        f.write(f"{url} | Size: {size_str}\n")


def check_link(date_str, base_url):
    """
    检查指定日期格式的链接是否有效

    参数:
    date_str (str): 日期字符串，用于生成完整链接
    base_url (str): 链接的基础 URL
    """
    if stop_event.is_set():
        return

    url = base_url.format(date_str)
    headers = {"User-Agent": random.choice(user_agents)}
    try:
        response = requests.head(url, headers=headers, timeout=10)
        if response.status_code == 200:
            content_length = int(response.headers.get("Content-Length", 0))
            save_valid_link(url, content_length)
    except requests.RequestException:
        pass
    time.sleep(cooldown)


def group_worker(config):
    """
    处理每个配置组的链接检查任务

    参数:
    config (dict): 配置组的信息，包括名称、基础 URL、开始日期和日期格式
    """
    name, base_url = config["name"], config["base_url"]
    start_date = datetime.datetime.strptime(config["start_date"], config["date_format"])
    date_format = config["date_format"]
    print(f"\n[INFO] Starting checks for [{name}] - Base URL: {base_url}")
    with open(output_file, "a") as f:
        f.write(f"\n[INFO] Starting checks for [{name}] - Base URL: {base_url}\n")

    date_queue = Queue()
    current_date = start_date
    while current_date <= end_date:
        date_queue.put(current_date.strftime(date_format))
        current_date += datetime.timedelta(days=1)

    with concurrent.futures.ThreadPoolExecutor(max_workers=threads_count) as executor:
        futures = [
            executor.submit(check_link, date_queue.get(), base_url)
            for _ in range(date_queue.qsize())
        ]
        while True:
            if all(f.done() for f in futures) or stop_event.is_set():
                if stop_event.is_set():
                    print("\n[INFO] Stopping ongoing tasks...")
                    for f in futures:
                        f.cancel()
                break
            time.sleep(1)


def signal_handler(_sig, _frame):
    """
    处理 Ctrl+C 中断信号，停止所有线程

    参数:
    _sig (int): 信号编号(未使用)
    _frame (FrameType): 当前堆栈帧(未使用)
    """
    print("\n[INFO] Process interrupted. Stopping threads...")
    stop_event.set()


def main():
    """
    主函数，控制程序的执行流程，包括信号处理和每个配置组的处理
    """
    signal.signal(signal.SIGINT, signal_handler)
    with open(output_file, "a") as f:
        f.write(
            f"\n--- Execution started at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n"
        )

    for config in base_url_configs:
        if stop_event.is_set():
            break
        group_worker(config)


if __name__ == "__main__":
    main()
