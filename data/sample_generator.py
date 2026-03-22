"""模拟数据生成器

生成逼真的淘宝电商数据用于系统演示和测试。
"""

import random
from datetime import date, timedelta

from config import (
    CrowdLevel, ConsumptionTier, AgeGroup, Gender, Platform,
    CreativeType, PromotionType, DEFAULT_CONFIG
)
from models.crowd import CrowdProfile, CrowdSegment
from models.product import Product, ProductMetrics
from models.campaign import Campaign, AdGroup, Keyword, Creative, Promotion


# 地域权重 (模拟真实分布)
REGION_WEIGHTS = {
    "广东": 15, "浙江": 12, "江苏": 11, "上海": 8, "北京": 7,
    "山东": 6, "四川": 5, "湖北": 4, "福建": 4, "河南": 4,
    "湖南": 3, "安徽": 3, "河北": 3, "辽宁": 3, "重庆": 2,
    "陕西": 2, "江西": 2, "广西": 2, "云南": 2, "天津": 2,
}

# 商品模板
PRODUCT_TEMPLATES = [
    {"title": "2026春季新款女士连衣裙修身显瘦", "price": 189.0, "category": "女装"},
    {"title": "男士休闲短袖T恤纯棉圆领", "price": 79.0, "category": "男装"},
    {"title": "儿童夏季运动套装纯棉透气", "price": 59.0, "category": "童装"},
    {"title": "真皮女士手提包大容量通勤", "price": 359.0, "category": "箱包"},
    {"title": "男士商务休闲皮鞋真皮软底", "price": 269.0, "category": "男鞋"},
    {"title": "智能手表运动防水心率监测", "price": 499.0, "category": "数码"},
    {"title": "家用空气净化器除甲醛除菌", "price": 899.0, "category": "家电"},
    {"title": "护肤套装补水保湿美白淡斑", "price": 238.0, "category": "美妆"},
    {"title": "有机坚果零食大礼包混合装", "price": 69.0, "category": "食品"},
    {"title": "婴儿纯棉纱布浴巾柔软吸水", "price": 45.0, "category": "母婴"},
]

# 关键词模板
KEYWORD_TEMPLATES = {
    "女装": ["连衣裙", "春装新款", "女装修身", "显瘦连衣裙", "小个子连衣裙", "气质连衣裙"],
    "男装": ["男士T恤", "纯棉短袖", "男装夏季", "休闲T恤", "潮牌短袖"],
    "童装": ["儿童套装", "童装夏季", "男童运动装", "女童套装", "纯棉童装"],
    "箱包": ["女士手提包", "真皮女包", "通勤包", "大容量包", "品牌女包"],
    "男鞋": ["男士皮鞋", "商务皮鞋", "休闲皮鞋", "真皮男鞋", "软底皮鞋"],
    "数码": ["智能手表", "运动手表", "防水手表", "心率手表", "蓝牙手表"],
    "家电": ["空气净化器", "除甲醛", "家用净化器", "卧室净化器", "除菌净化"],
    "美妆": ["护肤套装", "补水保湿", "美白套装", "淡斑精华", "护肤品女"],
    "食品": ["坚果零食", "混合坚果", "零食大礼包", "每日坚果", "有机坚果"],
    "母婴": ["婴儿浴巾", "纱布浴巾", "宝宝浴巾", "纯棉浴巾", "婴儿用品"],
}


def _weighted_choice(weights: dict):
    """加权随机选择"""
    items = list(weights.keys())
    ws = list(weights.values())
    return random.choices(items, weights=ws, k=1)[0]


def generate_crowd_profiles(n: int = 2000) -> list[CrowdProfile]:
    """生成模拟人群数据"""
    profiles = []
    regions = list(REGION_WEIGHTS.keys())
    region_ws = list(REGION_WEIGHTS.values())

    for i in range(n):
        # AIPL分布: A占40%, I占30%, P占20%, L占10%
        crowd_level = random.choices(
            list(CrowdLevel),
            weights=[40, 30, 20, 10],
            k=1
        )[0]

        # 根据人群阶段设置不同的行为数据
        if crowd_level == CrowdLevel.AWARENESS:
            pv = random.randint(1, 5)
            fav = random.randint(0, 1)
            cart = 0
            purchases = 0
            amount = 0
        elif crowd_level == CrowdLevel.INTEREST:
            pv = random.randint(3, 15)
            fav = random.randint(1, 3)
            cart = random.randint(0, 2)
            purchases = 0
            amount = 0
        elif crowd_level == CrowdLevel.PURCHASE:
            pv = random.randint(5, 20)
            fav = random.randint(1, 5)
            cart = random.randint(1, 3)
            purchases = random.randint(1, 3)
            amount = purchases * random.uniform(50, 500)
        else:  # LOYALTY
            pv = random.randint(10, 50)
            fav = random.randint(3, 10)
            cart = random.randint(2, 5)
            purchases = random.randint(3, 10)
            amount = purchases * random.uniform(80, 600)

        profile = CrowdProfile(
            user_id=f"U{i+1:06d}",
            age_group=random.choice(list(AgeGroup)),
            gender=random.choices([Gender.FEMALE, Gender.MALE], weights=[65, 35])[0],
            region=random.choices(regions, weights=region_ws)[0],
            consumption_tier=random.choice(list(ConsumptionTier)),
            crowd_level=crowd_level,
            page_views=pv,
            favorites=fav,
            cart_adds=cart,
            purchases=purchases,
            purchase_amount=round(amount, 2),
            last_visit_days=random.randint(0, 30),
            visit_frequency=random.randint(1, 20),
        )
        profiles.append(profile)

    return profiles


def generate_products(days: int = 30) -> list[Product]:
    """生成模拟商品数据"""
    products = []
    today = date.today()

    for i, tmpl in enumerate(PRODUCT_TEMPLATES):
        daily_metrics = []
        base_impressions = random.randint(2000, 10000)

        for d in range(days):
            current_date = today - timedelta(days=days - d - 1)
            # 增加一些随机波动和周末效应
            weekday_factor = 1.2 if current_date.weekday() >= 5 else 1.0
            noise = random.uniform(0.7, 1.3)

            impressions = int(base_impressions * weekday_factor * noise)
            ctr = random.uniform(0.02, 0.06)
            clicks = int(impressions * ctr)
            fav_rate = random.uniform(0.03, 0.08)
            cart_rate = random.uniform(0.05, 0.12)
            cvr = random.uniform(0.01, 0.05)

            favorites = int(clicks * fav_rate)
            cart_adds = int(clicks * cart_rate)
            orders = int(clicks * cvr)
            gmv = orders * tmpl["price"] * random.uniform(0.8, 1.0)
            cost = clicks * random.uniform(0.5, 2.5)

            daily_metrics.append(ProductMetrics(
                date=current_date,
                impressions=impressions,
                clicks=clicks,
                favorites=favorites,
                cart_adds=cart_adds,
                orders=orders,
                gmv=round(gmv, 2),
                cost=round(cost, 2),
                visitors=int(clicks * 0.85),
            ))

        products.append(Product(
            item_id=f"ITEM{i+1:04d}",
            title=tmpl["title"],
            price=tmpl["price"],
            category=tmpl["category"],
            daily_metrics=daily_metrics,
        ))

    return products


def generate_campaigns(products: list[Product]) -> list[Campaign]:
    """生成模拟投放计划"""
    campaigns = []
    today = date.today()
    platforms = [Platform.ZHITONGCHE, Platform.YINLIMOFA, Platform.WANXIANGTAI]

    for idx, platform in enumerate(platforms):
        ad_groups = []
        # 每个平台2-3个推广单元
        selected_products = random.sample(products, min(3, len(products)))

        for g_idx, product in enumerate(selected_products):
            category = product.category
            kw_templates = KEYWORD_TEMPLATES.get(category, ["通用关键词"])
            keywords = []

            for kw_text in kw_templates:
                # 模拟关键词数据
                impressions = random.randint(500, 5000)
                ctr = random.uniform(0.02, 0.08)
                clicks = int(impressions * ctr)
                cvr = random.uniform(0.01, 0.06)
                orders = int(clicks * cvr)
                bid = random.uniform(0.5, 3.0)
                cost = clicks * bid * random.uniform(0.8, 1.2)
                gmv = orders * product.price * random.uniform(0.8, 1.0)

                keywords.append(Keyword(
                    keyword=kw_text,
                    match_type=random.choice(["广泛匹配", "精准匹配"]),
                    bid=round(bid, 2),
                    quality_score=random.randint(4, 10),
                    impressions=impressions,
                    clicks=clicks,
                    cost=round(cost, 2),
                    orders=orders,
                    gmv=round(gmv, 2),
                ))

            ad_groups.append(AdGroup(
                group_id=f"AG{idx+1}{g_idx+1:02d}",
                name=f"{product.title[:10]}-单元{g_idx+1}",
                item_id=product.item_id,
                keywords=keywords,
                crowd_ids=[f"CROWD_{random.randint(1, 5):03d}"],
                bid_multiplier=random.uniform(1.0, 1.5),
            ))

        campaign = Campaign(
            campaign_id=f"CAMP{idx+1:03d}",
            name=f"{platform.value}-主推计划{idx+1}",
            platform=platform,
            daily_budget=random.choice([300, 500, 800, 1000]),
            start_date=today - timedelta(days=30),
            ad_groups=ad_groups,
            target_regions=DEFAULT_CONFIG.target_regions[:5],
            schedule_hours=DEFAULT_CONFIG.peak_hours,
        )
        campaigns.append(campaign)

    return campaigns


def generate_creatives(products: list[Product]) -> list[Creative]:
    """生成模拟创意素材数据"""
    creatives = []
    creative_names = {
        CreativeType.MAIN_IMAGE: ["白底主图", "场景图", "卖点主图", "促销主图"],
        CreativeType.VIDEO: ["15秒卖点视频", "30秒使用演示", "开箱视频"],
        CreativeType.LONG_IMAGE: ["详情首图长图", "对比长图"],
        CreativeType.CAROUSEL: ["多角度轮播", "场景轮播"],
    }

    for product in products[:6]:
        for ctype, names in creative_names.items():
            for name in names:
                impressions = random.randint(1000, 8000)
                # 视频类CTR通常更高
                base_ctr = random.uniform(0.04, 0.09) if ctype == CreativeType.VIDEO else random.uniform(0.02, 0.06)
                clicks = int(impressions * base_ctr)
                cvr = random.uniform(0.01, 0.05)
                orders = int(clicks * cvr)
                fav_rate = random.uniform(0.03, 0.08)
                cart_rate = random.uniform(0.04, 0.10)
                cost = clicks * random.uniform(0.5, 2.5)

                landing_views = int(clicks * random.uniform(0.85, 0.98))
                bounce_rate = random.uniform(0.35, 0.80)

                creatives.append(Creative(
                    creative_id=f"CR{len(creatives)+1:04d}",
                    name=f"{product.title[:8]}-{name}",
                    creative_type=ctype,
                    item_id=product.item_id,
                    impressions=impressions,
                    clicks=clicks,
                    favorites=int(clicks * fav_rate),
                    cart_adds=int(clicks * cart_rate),
                    orders=orders,
                    gmv=round(orders * product.price * random.uniform(0.8, 1.0), 2),
                    cost=round(cost, 2),
                    landing_page_views=landing_views,
                    bounce_count=int(landing_views * bounce_rate),
                    avg_stay_seconds=round(random.uniform(15, 120), 1),
                ))

    return creatives


def generate_promotions() -> list[Promotion]:
    """生成模拟促销活动数据"""
    today = date.today()
    promo_configs = [
        {"name": "新品首发5元券", "type": PromotionType.COUPON, "discount": 5, "threshold": 49},
        {"name": "满199减20", "type": PromotionType.FULL_REDUCTION, "discount": 20, "threshold": 199},
        {"name": "满299减50", "type": PromotionType.FULL_REDUCTION, "discount": 50, "threshold": 299},
        {"name": "限时3折秒杀", "type": PromotionType.FLASH_SALE, "discount": 70, "threshold": 0},
        {"name": "买二送一", "type": PromotionType.BUY_GIFT, "discount": 33, "threshold": 0},
        {"name": "三件套装特惠", "type": PromotionType.BUNDLE, "discount": 30, "threshold": 0},
        {"name": "会员日专享8折", "type": PromotionType.MEMBERSHIP, "discount": 20, "threshold": 0},
        {"name": "春季新品预售", "type": PromotionType.PRESALE, "discount": 15, "threshold": 0},
        {"name": "收藏店铺领10元券", "type": PromotionType.COUPON, "discount": 10, "threshold": 79},
        {"name": "老客户满100减15", "type": PromotionType.FULL_REDUCTION, "discount": 15, "threshold": 100},
    ]

    promotions = []
    for i, pc in enumerate(promo_configs):
        impressions = random.randint(5000, 30000)
        participation_rate = random.uniform(0.05, 0.25)
        participants = int(impressions * participation_rate)
        cvr = random.uniform(0.08, 0.35)
        orders = int(participants * cvr)
        avg_price = random.uniform(80, 350)
        gmv = orders * avg_price
        cost = orders * pc["discount"] * random.uniform(0.6, 1.0)
        new_ratio = random.uniform(0.2, 0.7)

        promotions.append(Promotion(
            promo_id=f"PROMO{i+1:03d}",
            name=pc["name"],
            promo_type=pc["type"],
            start_date=today - timedelta(days=random.randint(5, 25)),
            end_date=today + timedelta(days=random.randint(1, 10)),
            discount_value=pc["discount"],
            threshold=pc["threshold"],
            impressions=impressions,
            participants=participants,
            orders=orders,
            gmv=round(gmv, 2),
            cost=round(cost, 2),
            new_customer_orders=int(orders * new_ratio),
            repeat_customer_orders=int(orders * (1 - new_ratio)),
        ))

    return promotions


def generate_all_sample_data() -> dict:
    """生成全套模拟数据"""
    random.seed(42)  # 固定种子保证可复现

    profiles = generate_crowd_profiles(2000)
    products = generate_products(30)
    campaigns = generate_campaigns(products)
    creatives = generate_creatives(products)
    promotions = generate_promotions()

    return {
        "profiles": profiles,
        "products": products,
        "campaigns": campaigns,
        "creatives": creatives,
        "promotions": promotions,
    }
