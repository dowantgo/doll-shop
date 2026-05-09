from __future__ import annotations

import json
from pathlib import Path

from django.conf import settings
from django.core.cache import cache
from django.core.files import File
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.products.cache_utils import bump_feed_version
from apps.products.meme_seed import DEFAULT_SEED, build_catalog, render_catalog_images
from apps.products.models import Category, InventoryLog, Product, ProductImage


class Command(BaseCommand):
    help = 'Replace all current categories and products with 40 meme products.'

    def add_arguments(self, parser):
        parser.add_argument('--seed', type=int, default=DEFAULT_SEED)
        parser.add_argument('--batch-name', type=str, default='meme_replace_20260430')

    def handle(self, *args, **options):
        seed = options['seed']
        batch_name = options['batch_name']
        catalog = build_catalog(seed=seed, batch_name=batch_name)

        media_root = Path(settings.MEDIA_ROOT)
        image_dir = media_root / 'products' / 'generated' / batch_name
        manifest_dir = media_root / 'product_text_import'
        manifest_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = manifest_dir / f'{batch_name}.json'

        image_paths = render_catalog_images(catalog, image_dir)
        manifest_path.write_text(
            json.dumps(catalog, ensure_ascii=False, indent=2, default=str),
            encoding='utf-8',
        )

        counts_before = {
            'categories': Category.objects.count(),
            'products': Product.objects.count(),
            'images': ProductImage.objects.count(),
            'inventory_logs': InventoryLog.objects.count(),
        }

        with transaction.atomic():
            Product.objects.all().delete()
            Category.objects.all().delete()

            category_map: dict[str, Category] = {}
            for item in catalog:
                category_name = str(item['category_name'])
                if category_name in category_map:
                    continue
                category_map[category_name] = Category.objects.create(
                    name=category_name,
                    description=f'{category_name}主题表情包商品分类',
                    sort_order=item['category_sort_order'],
                )

            created_products = 0
            created_images = 0
            for item, image_path in zip(catalog, image_paths):
                product = Product.objects.create(
                    name=item['name'],
                    description=item['description'],
                    category=category_map[str(item['category_name'])],
                    price=item['price'],
                    cost=item['cost'],
                    stock=item['stock'],
                    sales=item['sales'],
                    is_hot=item['is_hot'],
                    hot_sort_order=item['hot_sort_order'],
                    status=item['status'],
                )
                created_products += 1

                product_image = ProductImage(product=product, is_main=True, sort_order=1)
                with image_path.open('rb') as fh:
                    product_image.image.save(image_path.name, File(fh), save=False)
                product_image.save()
                created_images += 1

        for key in (
            'products:feed:stats:top-sales:hit',
            'products:feed:stats:top-sales:miss',
            'products:feed:stats:hot-feed:hit',
            'products:feed:stats:hot-feed:miss',
        ):
            cache.delete(key)
        bump_feed_version()

        self.stdout.write(self.style.SUCCESS('商品目录替换完成'))
        self.stdout.write(
            f"已删除旧分类 {counts_before['categories']} 个，"
            f"旧商品 {counts_before['products']} 个，"
            f"旧商品图 {counts_before['images']} 个，"
            f"旧库存日志 {counts_before['inventory_logs']} 条。"
        )
        self.stdout.write(
            f'已创建新分类 {len(category_map)} 个，新商品 {created_products} 个，绑定主图 {created_images} 张。'
        )
        self.stdout.write(f'图片目录：{image_dir}')
        self.stdout.write(f'清单文件：{manifest_path}')

