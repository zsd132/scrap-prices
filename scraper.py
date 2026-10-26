#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
废旧物资价格爬虫
用法: python3 scraper.py
输出: prices.json（同目录，供 HTML 加载）

数据源：回收商网公开报价页（无需登录即可见价格）
说明：废废网等站对未登录用户遮蔽价格（显示****），如需接入需配合浏览器自动化或登录态。
"""
from bs4 import BeautifulSoup
import json, re, sys, time, subprocess
from datetime import datetime

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

def fetch(url):
    """用 curl 拿页面（绕开 requests TLS 指纹被拦的问题）"""
    try:
        out = subprocess.check_output([
            "curl", "-s", "--max-time", "25",
            "-A", "Mozilla/5.0",
            url
        ], timeout=30)
        return out.decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"    [curl失败] {e}")
        return ""

# 要抓的品类页面（回收商网分类 URL）
SOURCES = [
    # 废塑料类
    ("PET瓶片",   "https://baojia.huishoushang.com/material/list-c24/"),
    ("PP",        "https://baojia.huishoushang.com/material/list-c28/"),
    ("PE",        "https://baojia.huishoushang.com/material/list-c27/"),
    ("ABS",       "https://baojia.huishoushang.com/material/list-c25/"),
    ("PVC",       "https://baojia.huishoushang.com/material/list-c29/"),
]

def parse_price(text):
    """把 '4700-4850' 或 '5800' 解析成 (low, high, mid)"""
    text = text.strip().replace(',', '')
    m = re.match(r'([\d.]+)\s*-\s*([\d.]+)', text)
    if m:
        lo, hi = float(m.group(1)), float(m.group(2))
        return lo, hi, (lo + hi) / 2
    try:
        v = float(text)
        return v, v, v
    except:
        return None

def scrape_one(name, url):
    """抓一个品类页，返回记录列表"""
    print(f"  抓取 {name}: {url}")
    html = fetch(url)
    if not html:
        return []
    soup = BeautifulSoup(html, 'lxml')
    items = []
    for li in soup.select('li.list-item'):
        ps = li.find_all('p')
        if len(ps) < 6:
            continue
        try:
            item_name = ps[0].get_text(strip=True)
            spec      = ps[1].get_text(strip=True)
            region    = ps[2].get_text(strip=True)
            price_txt = ps[3].get_text(strip=True)
            unit      = ps[4].get_text(strip=True)
            change    = ps[5].get_text(strip=True)
            note      = ps[6].get_text(strip=True) if len(ps) > 6 else ''
            date      = ps[7].get_text(strip=True) if len(ps) > 7 else ''
        except Exception:
            continue
        p = parse_price(price_txt)
        if not p:
            continue
        lo, hi, mid = p
        items.append({
            "category": name,
            "item": item_name,
            "spec": spec,
            "region": region,
            "price_low": lo,
            "price_high": hi,
            "price": round(mid),
            "unit": unit,
            "change": change,
            "note": note,
            "date": date,
            "source": "回收商网"
        })
    print(f"    拿到 {len(items)} 条")
    return items

def main():
    print(f"=== 废旧物资价格爬虫  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")
    all_rows = []
    for name, url in SOURCES:
        rows = scrape_one(name, url)
        all_rows.extend(rows)
        time.sleep(1.5)  # 礼貌延时
    out = {
        "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total": len(all_rows),
        "data": all_rows
    }
    out_path = "prices.json"
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\n完成：{len(all_rows)} 条记录 -> {out_path}")
    # 打印前 3 条样本
    for r in all_rows[:3]:
        print(f"  样本: {r['region']} {r['item']} {r['price']} {r['unit']} ({r['date']})")

if __name__ == "__main__":
    import sys
    # 间隔秒数：默认 3600 秒（1小时）。命令行传参可改，如 python3 scraper.py 1800
    interval = int(sys.argv[1]) if len(sys.argv) > 1 else 3600
    print(f"定时模式：每 {interval//60} 分钟跑一次，Ctrl+C 停止\n")
    while True:
        main()
        next_time = time.strftime("%H:%M:%S", time.localtime(time.time() + interval))
        print(f"\n下次抓取：{next_time}，等待中...\n")
        time.sleep(interval)
