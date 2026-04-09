# QUICK START

## 1. 启动后端
```bash
cd backend
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
# source venv/bin/activate

pip install -r requirements.txt
copy .env.example .env   # macOS/Linux 用 cp
python manage.py migrate
python init_data_runner.py
python manage.py runserver 0.0.0.0:8000
```

## 2. 启动前端
```bash
cd frontend
npm install
npm run dev
```

## 3. 打开页面
- 商城首页: http://localhost:5173/
- 购物车: http://localhost:5173/cart
- 订单页: http://localhost:5173/orders
- 个人中心: http://localhost:5173/account
- 管理后台入口: http://localhost:5173/admin

## 4. 常用本地接口
- API 根路径: http://localhost:8000/api/
- Django Admin: http://localhost:8000/admin/
- 支付创建: POST http://localhost:8000/api/pay/create_payment/
- 支付宝回调: POST http://localhost:8000/api/pay/notify/alipay/

## 5. 一键脚本
- Windows: `scripts\startup.bat`
- macOS/Linux: `./scripts/startup.sh`

## 6. 支付联调提醒
- 本地真实支付回调需要公网可访问 `ALIPAY_NOTIFY_URL`
- 建议使用 ngrok 将后端端口映射出去
- 仅本地演示可用 `mock` 支付方式
