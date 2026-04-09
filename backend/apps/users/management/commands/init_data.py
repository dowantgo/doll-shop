"""
Database initialization command
Run: python manage.py init_data
"""

from django.core.management.base import BaseCommand
from apps.users.models import User, Address
from apps.products.models import Category, Product


class Command(BaseCommand):
    help = 'Initialize database with sample data'

    def handle(self, *args, **kwargs):
        self.stdout.write('Starting database initialization...')
        
        # Create admin user
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@example.com',
                'role': 'admin',
                'is_superuser': True,
                'is_staff': True,
            }
        )
        if created:
            admin_user.set_password('admin123')
            admin_user.save()
            self.stdout.write(self.style.SUCCESS(f'Admin user created: {admin_user.username}'))
        else:
            self.stdout.write(f'Admin user already exists: {admin_user.username}')

        # Create regular user
        user, created = User.objects.get_or_create(
            username='user1',
            defaults={
                'email': 'user1@example.com',
                'phone': '13800138000',
                'role': 'user',
            }
        )
        if created:
            user.set_password('user123')
            user.save()
            self.stdout.write(self.style.SUCCESS(f'Regular user created: {user.username}'))
        else:
            self.stdout.write(f'Regular user already exists: {user.username}')

        # Create address for user
        Address.objects.get_or_create(
            user=user,
            name='张三',
            defaults={
                'phone': '13800138000',
                'province': '北京',
                'city': '北京',
                'district': '朝阳区',
                'address': '朝阳区某街道123号',
                'is_default': True,
            }
        )
        self.stdout.write(self.style.SUCCESS('Address created for user1'))

        # Create categories
        categories_data = [
            {'name': '毛绒玩偶', 'description': '各种可爱的毛绒玩偶'},
            {'name': '手办模型', 'description': '精美的手办模型收藏'},
            {'name': '玩偶礼盒', 'description': '适合送礼的玩偶礼盒'},
            {'name': '周边产品', 'description': '各种玩偶周边产品'},
        ]

        for i, cat_data in enumerate(categories_data):
            category, created = Category.objects.get_or_create(
                name=cat_data['name'],
                defaults={
                    'description': cat_data['description'],
                    'sort_order': i,
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Category created: {category.name}'))

        # Create sample products
        categories = list(Category.objects.all())
        products_data = [
            {
                'name': '可爱小熊玩偶',
                'description': '一个软萌可爱的小熊玩偶，适合所有年龄段',
                'price': 49.99,
                'stock': 100,
                'is_hot': True,
                'hot_sort_order': 1,
            },
            {
                'name': '兔子毛绒玩具',
                'description': '柔软的兔子毛绒玩具，手感超舒服',
                'price': 39.99,
                'stock': 150,
                'is_hot': True,
                'hot_sort_order': 2,
            },
            {
                'name': '狐狸毛绒娃娃',
                'description': '精致的狐狸毛绒娃娃，设计独特',
                'price': 59.99,
                'stock': 80,
                'is_hot': True,
                'hot_sort_order': 3,
            },
            {
                'name': '企鹅玩偶套装',
                'description': '可爱企鹅一家的玩偶套装，包装精美',
                'price': 89.99,
                'stock': 50,
                'is_hot': False,
            },
            {
                'name': '猫咪毛绒玩具',
                'description': '三种颜色可选的猫咪毛绒玩具',
                'price': 44.99,
                'stock': 120,
                'is_hot': False,
            },
            {
                'name': '狗狗抱枕玩偶',
                'description': '可用作抱枕的软萌狗狗玩偶',
                'price': 69.99,
                'stock': 75,
                'is_hot': True,
                'hot_sort_order': 4,
            },
            {
                'name': '恐龙毛绒玩具',
                'description': '可爱的恐龙毛绒玩具，小孩很喜欢',
                'price': 34.99,
                'stock': 200,
                'is_hot': False,
            },
            {
                'name': '羊驼毛绒玩偶',
                'description': '创意设计的羊驼毛绒玩偶',
                'price': 54.99,
                'stock': 90,
                'is_hot': False,
            },
            {
                'name': '海豚玩偶',
                'description': '蓝色可爱的海豚玩偶',
                'price': 44.99,
                'stock': 110,
                'is_hot': True,
                'hot_sort_order': 5,
            },
            {
                'name': '长颈鹿毛绒玩具',
                'description': '黄色斑纹的长颈鹿毛绒玩具',
                'price': 49.99,
                'stock': 95,
                'is_hot': False,
            },
        ]

        created_count = 0
        for i, prod_data in enumerate(products_data):
            category = categories[i % len(categories)]
            product, created = Product.objects.get_or_create(
                name=prod_data['name'],
                defaults={
                    'description': prod_data['description'],
                    'price': prod_data['price'],
                    'stock': prod_data['stock'],
                    'is_hot': prod_data.get('is_hot', False),
                    'hot_sort_order': prod_data.get('hot_sort_order', 0),
                    'category': category,
                    'cost': prod_data['price'] * 0.4,
                }
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'Product created: {product.name}'))

        self.stdout.write(self.style.SUCCESS(f'\n✅ Database initialization complete!'))
        self.stdout.write(f'Admin user: admin / admin123')
        self.stdout.write(f'Regular user: user1 / user123')
        self.stdout.write(f'Products created: {created_count}')
