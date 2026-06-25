import re
from typing import Any


COUNTRIES = {
    "germany": "Germany",
    "deutschland": "Germany",
    "usa": "USA",
    "united states": "USA",
    "canada": "Canada",
    "uk": "UK",
    "france": "France",
    "japan": "Japan",
    "德国": "Germany",
    "美国": "USA",
    "加拿大": "Canada",
    "英国": "UK",
    "法国": "France",
    "日本": "Japan",
}

MATERIALS = {
    "stainless steel": "stainless steel",
    "carbon steel": "carbon steel",
    "galvanized steel": "galvanized steel",
    "aluminum": "aluminum",
    "steel": "steel",
    "不锈钢": "stainless steel",
    "碳钢": "carbon steel",
    "镀锌钢": "galvanized steel",
    "铝合金": "aluminum",
    "铝": "aluminum",
    "钢": "steel",
}

PRODUCTS = {
    "metal bracket": "metal bracket",
    "bracket": "metal bracket",
    "housing": "metal housing",
    "enclosure": "metal enclosure",
    "cabinet": "metal cabinet",
    "box": "metal box",
    "panel": "metal panel",
    "sheet metal": "sheet metal part",
    "金属支架": "金属支架",
    "支架": "金属支架",
    "铝合金外壳": "铝合金外壳",
    "外壳": "铝合金外壳",
    "机箱": "金属机箱",
    "机柜": "金属机柜",
    "箱体": "金属箱体",
    "面板": "金属面板",
    "钣金": "钣金件",
}


def detect_language(message: str) -> str:
    return "zh" if any("\u4e00" <= char <= "\u9fff" for char in message) else "en"


def extract_quantity(text: str) -> str | None:
    patterns = [
        r"(\d[\d,]*)\s*(pcs|pieces|sets|units)",
        r"(\d[\d,]*)\s*(个|件|套|台|pcs)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return " ".join(part for part in match.groups() if part)
    return None


def extract_lead_fields(message: str, visitor: dict[str, Any] | None) -> dict[str, Any]:
    visitor = visitor or {}
    lower = message.lower()
    custom = any(token in lower for token in ["custom", "oem", "odm"]) or any(token in message for token in ["定制", "按图", "来图", "图纸"])

    product = None
    for key, value in PRODUCTS.items():
        if key in lower or key in message:
            product = f"定制{value}" if custom and not value.startswith("定制") else value
            break

    material = None
    for key, value in MATERIALS.items():
        if key in lower or key in message:
            material = value
            break

    country = visitor.get("country") or None
    if not country:
        for key, value in COUNTRIES.items():
            if key in lower or key in message:
                country = value
                break

    email_match = re.search(r"[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}", message, re.IGNORECASE)
    return {
        "product": product,
        "quantity": extract_quantity(message),
        "country": country,
        "email": email_match.group(0) if email_match else visitor.get("email") or None,
        "material": material,
        "drawing_available": bool(re.search(r"\bdrawing\b|\bstep\b|\b3d\b|\bsample\b|\bsketch\b|图纸|样品|草图|模型|按图|来图", message, re.IGNORECASE)),
    }
