"""Sina Finance 行情数据层"""

import re

import requests

SINA_URL = "https://hq.sinajs.cn/list={}"
HEADERS = {"Referer": "https://finance.sina.com.cn"}


def _sina_code(raw):
    """A股代码转 Sina 前缀。"""
    if raw.startswith(("6", "9")):
        return f"sh{raw}"
    return f"sz{raw}"


def _build_url(codes):
    return SINA_URL.format(",".join(_sina_code(c) for c in codes))


def fetch(codes):
    """请求 Sina 接口，返回 list[dict]，网络异常返回 None。"""
    if not codes:
        return []
    try:
        resp = requests.get(_build_url(codes), headers=HEADERS, timeout=5)
        resp.encoding = "gbk"
        raw = resp.text.strip()
    except requests.RequestException:
        return None

    stocks = []
    for line in raw.split("\n"):
        line = line.strip()
        if not line:
            continue
        if s := _parse(line):
            stocks.append(s)
    return stocks


def _parse(line):
    """解析单行 Sina JS 返回。

    格式：var hq_str_sh600519="贵州茅台,...";
    """
    m = re.search(r'hq_str_[a-z]+(\d+)="', line)
    if not m:
        return None
    code = m.group(1)

    try:
        data = line.split('"')[1]
    except IndexError:
        return None
    f = data.split(",")
    if len(f) < 32:
        return None

    name = f[0]
    pre_close = _f(f[2])
    price = _f(f[3])
    vol = _i(f[8])

    s = {
        "code": code,
        "name": name,
        "open": _f(f[1]),
        "pre_close": pre_close,
        "price": price,
        "high": _f(f[4]),
        "low": _f(f[5]),
        "vol": vol,
        "amount": _f(f[9]),
        "date": f[30],
        "trade_time": f[31],
    }

    if price is not None and pre_close and pre_close != 0:
        chg = round(price - pre_close, 2)
        s["change"] = chg
        s["change_pct"] = round(chg / pre_close * 100, 2)
    else:
        s["change"] = None
        s["change_pct"] = None

    return s


def _f(v):
    try:
        return float(v) if v.strip() else None
    except (ValueError, AttributeError):
        return None


def _i(v):
    try:
        return int(v) if v.strip() else None
    except (ValueError, AttributeError):
        return None
