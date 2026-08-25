"""Static seed data for MySQL initialization."""

from __future__ import annotations

from datetime import datetime, timedelta
import time

from sqlalchemy import func, insert, select


PRODUCTS_ZH = {
    "栀子花车载香薰": {
        "name": "栀子花车载香薰",
        "description": "栀子花车载香薰是一款为汽车提供舒适和放松的香薰产品。它可以帮助用户缓解疲劳、缓解压力，提升驾驶体验。",
        "cover_image": "tos://xiangyuxuan-test/custom_support/product/栀子花车载香薰.PNG",
    },
    "车载手机超级快充": {
        "name": "车载手机超级快充",
        "description": "车载手机超级快充是一款为汽车提供充电功能的产品。它可以为汽车提供充足的电力，延长电池寿命。",
        "cover_image": "tos://xiangyuxuan-test/custom_support/product/车载手机超级快充.jpeg",
    },
    "车载收纳盒": {
        "name": "车载收纳盒",
        "description": "车载收纳盒是一款为汽车提供收纳功能的产品。它可以帮助用户整理车辆内的物品，提高工作效率。",
        "cover_image": "tos://xiangyuxuan-test/custom_support/product/车载收纳盒.PNG",
    },
    "车载手机快充普通隐藏式": {
        "name": "车载手机快充普通隐藏式",
        "description": "车载手机快充普通隐藏式是一款为汽车提供充电功能的产品。它可以为汽车提供充足的电力，延长电池寿命。",
        "cover_image": "tos://xiangyuxuan-test/custom_support/product/车载手机快充普通隐藏式.jpeg",
    },
    "活性炭车载除味包": {
        "name": "活性炭车载除味包",
        "description": "活性炭车载除味包是一款为汽车提供除味功能的产品。它可以帮助用户去除车内的灰尘、污垢，提高车内空气质量。",
        "cover_image": "tos://xiangyuxuan-test/custom_support/product/活性炭车载除味包.PNG",
    },
    "可爱风腰靠垫": {
        "name": "可爱风腰靠垫",
        "description": "可爱风腰靠垫是一款为汽车提供安全保障的产品。它可以帮助用户避免车辆碰撞，提高车辆安全性。",
        "cover_image": "tos://xiangyuxuan-test/custom_support/product/可爱风腰靠垫.JPEG",
    },
    "汽车遮阳挡": {
        "name": "汽车遮阳挡",
        "description": "汽车遮阳挡是一款为汽车提供遮阳功能的产品。它可以帮助用户在雨天、雪天等恶劣天气下，提供充足的遮阳保护。",
        "cover_image": "tos://xiangyuxuan-test/custom_support/product/汽车遮阳挡.PNG",
    },
    "通用型汽车脚垫": {
        "name": "通用型汽车脚垫",
        "description": "通用型汽车脚垫是一款为汽车提供支撑功能的产品。它可以帮助用户在车辆行驶过程中，提供稳定的支撑。",
        "cover_image": "tos://xiangyuxuan-test/custom_support/product/通用型汽车脚垫.PNG",
    },
    "小动物靠枕": {
        "name": "小动物靠枕",
        "description": "小动物靠枕是一款为汽车提供安全保障的产品。它可以帮助用户避免车辆碰撞，提高车辆安全性。",
        "cover_image": "tos://xiangyuxuan-test/custom_support/product/小动物靠枕.PNG",
    },
    "折叠旋转电动无线充车载支架": {
        "name": "折叠旋转电动无线充车载支架",
        "description": "折叠旋转电动无线充车载支架是一款为汽车提供充电功能的产品。它可以为汽车提供充足的电力，延长电池寿命。",
        "cover_image": "tos://xiangyuxuan-test/custom_support/product/折叠旋转电动无线充车载支架.PNG",
    },
}

PRODUCTS_EN = {
    "Women's Floral Graphic T-Shirts": {
        "name": "Women's Floral Graphic T-Shirts",
        "description": "Women's Floral Graphic T-Shirts is a soft, breathable, and easy-to-style top featuring a charming wildflower design, perfect for everyday wear and any casual occasion",
        "cover_image": "https://sf16-sg.tiktokcdn.com/obj/eden-sg/lm_sth/ljhwZthlaukjlkulzlp/ark/application/demo/shop_guide/product/Women's Floral Graphic T-Shirts.png",
    },
    "Men's Straight Cut Pants": {
        "name": "Men's Straight Cut Pants",
        "description": "Men's Straight Cut Pants is a comfortable, all-season essential, featuring a timeless fit and easy machine-wash care.",
        "cover_image": "https://sf16-sg.tiktokcdn.com/obj/eden-sg/lm_sth/ljhwZthlaukjlkulzlp/ark/application/demo/shop_guide/product/Men's Straight Cut Pants.png",
    },
    "Long Sleeve V Neck Blouses": {
        "name": "Long Sleeve V Neck Blouses",
        "description": "Long Sleeve V Neck Blouses is a breathable and stylish blouse, perfect for versatile, year-round wear",
        "cover_image": "https://sf16-sg.tiktokcdn.com/obj/eden-sg/lm_sth/ljhwZthlaukjlkulzlp/ark/application/demo/shop_guide/product/Long Sleeve V Neck Blouses.png",
    },
    "Women's Strap Flounce Long Dress": {
        "name": "Women's Strap Flounce Long Dress",
        "description": "Women's Strap Flounce Long Dress is a flowing, boho-inspired piece that blends effortless beauty with a flattering design for any occasion",
        "cover_image": "https://sf16-sg.tiktokcdn.com/obj/eden-sg/lm_sth/ljhwZthlaukjlkulzlp/ark/application/demo/shop_guide/product/Women's Strap Flounce Long Dress.png",
    },
    "Adult Unisex T-Shirt": {
        "name": "Adult Unisex T-Shirt",
        "description": "Adult Unisex T-Shirt is a durable, heavyweight essential offering all-day comfort and timeless style for everyday wear or work",
        "cover_image": "https://sf16-sg.tiktokcdn.com/obj/eden-sg/lm_sth/ljhwZthlaukjlkulzlp/ark/application/demo/shop_guide/product/Adult Unisex T-Shirt.png",
    },
    "Unisex Vintage Baseball Cap": {
        "name": "Unisex Vintage Baseball Cap",
        "description": "Unisex Vintage Baseball Cap is a relaxed, vintage-washed essential with an unstructured crown, available in 10 colors to match any style effortlessly",
        "cover_image": "https://sf16-sg.tiktokcdn.com/obj/eden-sg/lm_sth/ljhwZthlaukjlkulzlp/ark/application/demo/shop_guide/product/Unisex Vintage Baseball Cap.png",
    },
    "Pink Large Shoulder Tote Bag": {
        "name": "Pink Large Shoulder Tote Bag",
        "description": "Pink Large Shoulder Tote Bag is a stylish and spacious everyday essential, crafted from soft, durable material with a charming bow accent for a perfect blend of fashion and function",
        "cover_image": "https://sf16-sg.tiktokcdn.com/obj/eden-sg/lm_sth/ljhwZthlaukjlkulzlp/ark/application/demo/shop_guide/product/Pink Large Shoulder Tote Bag.png",
    },
    "Ballet Flat": {
        "name": "Ballet Flat",
        "description": "Ballet Flat is an elegant shoe featuring a sweet bow detail and a comfortable low heel for effortless style and comfort",
        "cover_image": "https://sf16-sg.tiktokcdn.com/obj/eden-sg/lm_sth/ljhwZthlaukjlkulzlp/ark/application/demo/shop_guide/product/Ballet Flat.png",
    },
}


def build_product_rows():
    rows = []
    for language, source in (("zh", PRODUCTS_ZH), ("en", PRODUCTS_EN)):
        for item in source.values():
            rows.append(
                {
                    "language": language,
                    "name": item["name"],
                    "description": item["description"],
                    "cover_image": item["cover_image"],
                }
            )
    return rows


def build_demo_order_rows(account_id: str, now: int):
    return [
        {
            "order_id": f"{account_id}_1",
            "account_id": account_id,
            "status": "已发货",
            "product_name": "车载收纳盒",
            "tracking_number": f"SF{account_id}0001",
            "reason": None,
            "created_at": now,
            "updated_at": now,
        },
        {
            "order_id": f"{account_id}_2",
            "account_id": account_id,
            "status": "未发货",
            "product_name": "汽车遮阳挡",
            "tracking_number": None,
            "reason": None,
            "created_at": now,
            "updated_at": now,
        },
        {
            "order_id": f"{account_id}_3",
            "account_id": account_id,
            "status": "未发货",
            "product_name": "可爱风腰靠垫",
            "tracking_number": None,
            "reason": None,
            "created_at": now,
            "updated_at": now,
        },
    ]


def build_demo_tracking_rows(tracking_number: str, now: int):
    base = datetime.fromtimestamp(now) - timedelta(days=3)
    return [
        {
            "tracking_number": tracking_number,
            "event_time": int((base + timedelta(hours=0)).timestamp()),
            "status": "待揽收",
            "location": "上海转运中心",
            "description": "包裹在上海转运中心等待揽收",
            "created_at": now,
        },
        {
            "tracking_number": tracking_number,
            "event_time": int((base + timedelta(hours=8)).timestamp()),
            "status": "已揽收",
            "location": "杭州转运中心",
            "description": "快递员已在杭州转运中心揽收",
            "created_at": now,
        },
        {
            "tracking_number": tracking_number,
            "event_time": int((base + timedelta(hours=16)).timestamp()),
            "status": "派送中",
            "location": "北京转运中心",
            "description": "包裹已到达北京转运中心，正在派送",
            "created_at": now,
        },
    ]


def build_default_faq_rows(account_id: str, now: int):
    return [
        {
            "account_id": account_id,
            "question": "这款收纳盒适合什么车型？",
            "answer": "适合大多数家用车和常见 SUV 车型。",
            "score": 5,
            "status": "approved",
            "source": "seed",
            "created_at": now,
        },
        {
            "account_id": account_id,
            "question": "物流一般多久到？",
            "answer": "一般 2 到 5 天，具体以地区和快递实际为准。",
            "score": 5,
            "status": "approved",
            "source": "seed",
            "created_at": now,
        },
    ]


def ensure_seed_data(engine) -> None:
    from database import faq_documents, orders, products, tracking_events

    now = int(time.time())
    with engine.begin() as conn:
        if _is_empty(conn, products):
            conn.execute(insert(products), build_product_rows())
        if _is_empty(conn, orders):
            conn.execute(insert(orders), build_demo_order_rows("100000", now))
        if _is_empty(conn, tracking_events):
            conn.execute(insert(tracking_events), build_demo_tracking_rows("SF1000000001", now))
        if _is_empty(conn, faq_documents):
            conn.execute(insert(faq_documents), build_default_faq_rows("100000", now))


def _is_empty(conn, table) -> bool:
    return conn.execute(select(func.count()).select_from(table)).scalar_one() == 0
