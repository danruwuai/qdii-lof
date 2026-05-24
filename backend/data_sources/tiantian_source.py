"""天天基金 JSONP API：基金估算净值"""
import re
import httpx


async def get_estimated_nav(fund_code: str) -> dict | None:
    """
    获取基金实时估算净值
    返回: {fundcode, name, dwjz(单位净值), gsz(估算净值), gszzl(估算涨跌幅), gztime}
    """
    url = f"http://fundgz.1234567.com.cn/js/{fund_code}.js"
    try:
        import time
        rt = str(int(time.time() * 1000))
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url, params={"rt": rt})
            text = resp.text
            # 解析 JSONP: jsonpgz({...})
            match = re.search(r"jsonpgz\((\{.*?\})\)", text)
            if not match:
                return None
            import json
            data = json.loads(match.group(1))
            return {
                "fundcode": data.get("fundcode", fund_code),
                "name": data.get("name", ""),
                "dwjz": float(data["dwjz"]) if data.get("dwjz") else None,
                "gsz": float(data["gsz"]) if data.get("gsz") else None,
                "gszzl": float(data["gszzl"]) if data.get("gszzl") else None,
                "gztime": data.get("gztime", ""),
            }
    except Exception:
        return None
