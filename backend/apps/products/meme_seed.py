from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
import random

from PIL import Image, ImageDraw


DEFAULT_SEED = 20260430


@dataclass(frozen=True)
class CategorySpec:
    key: str
    name: str
    sort_order: int
    price_min: Decimal
    price_max: Decimal
    stock_min: int
    stock_max: int
    palette: tuple[str, str, str]
    scenes: tuple[str, ...]
    props: tuple[str, ...]
    style_hint: str


CATEGORY_SPECS: tuple[CategorySpec, ...] = (
    CategorySpec(
        key='nailong',
        name='奶龙',
        sort_order=1,
        price_min=Decimal('29.90'),
        price_max=Decimal('59.90'),
        stock_min=80,
        stock_max=180,
        palette=('#FFE08A', '#FF9B73', '#FFF8DD'),
        scenes=(
            '躺平发呆',
            '加班摸鱼',
            '午睡翻滚',
            '早八打卡',
            '奶凶眨眼',
            '元气比耶',
            '委屈抱抱',
            '早餐冲刺',
            '下班开摆',
            '开心转圈',
        ),
        props=('奶瓶', '云朵', '小蛋糕', '抱枕', '星星'),
        style_hint='软萌暖色、表情夸张、适合聊天整活',
    ),
    CategorySpec(
        key='mamba',
        name='曼巴',
        sort_order=2,
        price_min=Decimal('49.90'),
        price_max=Decimal('89.90'),
        stock_min=40,
        stock_max=120,
        palette=('#111111', '#2D7E62', '#E7C76B'),
        scenes=(
            '冷脸出场',
            '绝杀凝视',
            '训练拉满',
            '背影压场',
            '凌晨开练',
            '低头系鞋带',
            '最后一投',
            '战术沉思',
            '胜负欲点满',
            '单挑预热',
        ),
        props=('黑金线条', '球馆灯光', '蛇纹光影', '记分牌', '冠军丝带'),
        style_hint='黑曼巴梗风、酷感强、黑绿黑金配色',
    ),
    CategorySpec(
        key='hajimi',
        name='哈吉米',
        sort_order=3,
        price_min=Decimal('39.90'),
        price_max=Decimal('69.90'),
        stock_min=60,
        stock_max=160,
        palette=('#87D9FF', '#FF85B7', '#FFF4FB'),
        scenes=(
            '嫌弃看人',
            '干饭冲刺',
            'emo望天',
            '早八灵魂',
            '学习发呆',
            '自拍摆拍',
            '加班破防',
            '通宵发疯',
            '奶茶陪伴',
            '考试祈祷',
        ),
        props=('猫爪', '爱心贴纸', '奶茶杯', '键盘', '波浪线'),
        style_hint='猫猫哈吉米梗、生活化场景、搞笑表情',
    ),
    CategorySpec(
        key='cxk',
        name='蔡徐坤中国流行表情包',
        sort_order=4,
        price_min=Decimal('59.90'),
        price_max=Decimal('99.90'),
        stock_min=30,
        stock_max=100,
        palette=('#CFE0FF', '#5A6BF6', '#F8FAFF'),
        scenes=(
            '打球起势',
            '全场聚光',
            '练习室开摆',
            '舞台回眸',
            '顶流出招',
            '热梗接力',
            '唱跳预备',
            '控场挑眉',
            '全网刷屏',
            '篮球转场',
        ),
        props=('篮球', '聚光灯', '音浪', '蓝银光效', '舞台烟雾'),
        style_hint='弱人像联想、流行梗氛围、舞台感强',
    ),
)


def _price_point(rng: random.Random, minimum: Decimal, maximum: Decimal) -> Decimal:
    low = int(minimum * 10)
    high = int(maximum * 10)
    return Decimal(rng.randint(low, high)) / Decimal('10')


def _sales_score(spec: CategorySpec, index: int, rng: random.Random) -> int:
    base = max(20, 160 - index * 8 - spec.sort_order * 5)
    wobble = rng.randint(0, 22)
    return max(1, base - wobble)


def build_catalog(seed: int = DEFAULT_SEED, batch_name: str = 'meme_replace_20260430') -> list[dict[str, object]]:
    rng = random.Random(seed)
    catalog: list[dict[str, object]] = []

    for spec in CATEGORY_SPECS:
        for index, scene in enumerate(spec.scenes, start=1):
            prop = spec.props[(index - 1) % len(spec.props)]
            price = _price_point(rng, spec.price_min, spec.price_max).quantize(Decimal('0.00'))
            stock = rng.randint(spec.stock_min, spec.stock_max)
            sales = _sales_score(spec, index, rng)
            filename = f'{batch_name}_{spec.key}_{index:02d}.png'

            catalog.append(
                {
                    'category_key': spec.key,
                    'category_name': spec.name,
                    'category_sort_order': spec.sort_order,
                    'name': f'{spec.name}{scene}表情包周边',
                    'description': f'{spec.name}主题商品图，主打“{scene}”场景，搭配{prop}元素，适合收藏、整活和聊天使用。',
                    'price': price,
                    'cost': (price * Decimal('0.35')).quantize(Decimal('0.00')),
                    'stock': stock,
                    'sales': sales,
                    'is_hot': index <= 2,
                    'hot_sort_order': (spec.sort_order - 1) * 10 + index,
                    'status': True,
                    'scene': scene,
                    'prop': prop,
                    'palette': spec.palette,
                    'style_hint': spec.style_hint,
                    'image_filename': filename,
                }
            )

    return catalog


def render_catalog_images(catalog: list[dict[str, object]], output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []

    for index, item in enumerate(catalog, start=1):
        bg, accent, panel = item['palette']
        image = Image.new('RGB', (1024, 1024), bg)
        draw = ImageDraw.Draw(image)

        draw.rounded_rectangle((56, 56, 968, 968), radius=56, fill=panel, outline=accent, width=12)
        draw.rounded_rectangle((90, 90, 934, 208), radius=30, fill=accent)
        draw.rounded_rectangle((90, 250, 934, 900), radius=44, fill='white')

        for offset in range(4):
            x = 160 + offset * 180
            draw.ellipse((x, 700, x + 120, 820), fill=accent)
            draw.ellipse((x + 36, 650, x + 84, 698), fill=accent)

        draw.rounded_rectangle((120, 116, 336, 166), radius=20, fill='#111111')
        draw.rounded_rectangle((370, 116, 550, 166), radius=20, fill=accent)
        draw.rounded_rectangle((580, 116, 760, 166), radius=20, fill='#FFFFFF')
        draw.rounded_rectangle((790, 116, 904, 166), radius=20, fill='#111111')

        draw.rounded_rectangle((120, 316, 430, 404), radius=26, fill=accent)
        draw.rounded_rectangle((120, 438, 820, 504), radius=22, fill='#ECECEC')
        draw.rounded_rectangle((120, 538, 720, 594), radius=18, fill='#F5F5F5')

        progress_width = 120 + int(min(1, item['stock'] / 200) * 560)
        draw.rounded_rectangle((120, 690, 700, 738), radius=16, fill='#EDEDED')
        draw.rounded_rectangle((120, 690, progress_width, 738), radius=16, fill=accent)

        sales_width = 120 + int(min(1, item['sales'] / 180) * 560)
        draw.rounded_rectangle((120, 772, 700, 820), radius=16, fill='#EDEDED')
        draw.rounded_rectangle((120, 772, sales_width, 820), radius=16, fill='#111111')

        if item['is_hot']:
            draw.polygon([(820, 300), (900, 340), (860, 420), (780, 380)], fill=accent)

        for stripe in range(6):
            y1 = 868 + stripe * 10
            draw.rounded_rectangle((120 + stripe * 18, y1, 880 - stripe * 18, y1 + 6), radius=3, fill=accent)

        path = output_dir / str(item['image_filename'])
        image.save(path, format='PNG')
        paths.append(path)

    return paths
