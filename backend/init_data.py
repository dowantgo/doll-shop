"""
Database initialization script
Run: python manage.py shell < init_data.py
"""

from apps.users.models import Address, User


admin_user, created = User.objects.get_or_create(
    username='admin',
    defaults={
        'email': 'admin@example.com',
        'role': 'admin',
        'is_superuser': True,
        'is_staff': True,
    },
)
if created:
    admin_user.set_password('admin123')
    admin_user.save()
    print(f'Admin user created: {admin_user.username}')


user, created = User.objects.get_or_create(
    username='user1',
    defaults={
        'email': 'user1@example.com',
        'phone': '13800138000',
        'role': 'user',
    },
)
if created:
    user.set_password('user123')
    user.save()
    print(f'Regular user created: {user.username}')


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
    },
)

print('\nDatabase initialization complete!')
print('Admin user: admin / admin123')
print('Regular user: user1 / user123')
print('Product/category seed data is managed separately via:')
print('python manage.py reset_meme_products')
