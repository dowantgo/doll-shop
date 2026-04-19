# 玩偶商城 (Doll Shop)

一个基于 **Vue 3 + Django REST Framework** 的全栈电商示例项目，包含用户端商城、购物车、订单、支付（支付宝扫码）和后台管理能力。

## 目录
- [项目特性](#项目特性)
- [技术栈](#技术栈)
- [项目结构](#项目结构)
- [项目文档](#项目文档)
- [环境要求](#环境要求)
- [快速开始](#快速开始)
- [环境变量](#环境变量)
- [运行方式](#运行方式)
- [核心接口总览](#核心接口总览)
- [常见问题](#常见问题)

## 项目特性

### 用户端
- 用户注册 / 登录（图片验证码 + 邮箱验证码）
- 商品首页：热销商品、分类筛选、关键词搜索
- 商品详情：多图展示、加入购物车
- 购物车：增减数量、移除、清空
- 订单：从购物车创建订单、订单列表/详情、取消待支付订单
- 账户中心：个人信息、收货地址 CRUD

### 支付
- 创建支付单：`/api/pay/create_payment/`
- 支持支付方式：`alipay` / `wechat(mock)` / `mock`
- 支付二维码图片返回：`qr_code_image`（Base64 Data URL）
- 支付状态查询 + 支付宝异步通知处理

### 管理端
- 仪表盘统计
- 商品管理（含图片上传、主图设置、图片删除）
- 分类管理（含分类商品数查询）
- 订单管理（发货 / 取消 / 完成）
- 用户管理（设为管理员、禁用/启用）

## 技术栈

### 前端
- Vue 3
- Vue Router 4
- Pinia
- Element Plus
- Axios
- Vite 4

### 后端
- Django 4.2
- Django REST Framework
- SimpleJWT
- django-filter
- django-cors-headers
- django-redis
- MySQL（主库）
- Redis（缓存/验证码）
- python-alipay-sdk（支付宝）

## 项目结构

```text
shop/
├─ frontend/
│  ├─ src/
│  │  ├─ views/
│  │  ├─ components/
│  │  ├─ api/
│  │  ├─ router/
│  │  ├─ stores/
│  │  └─ utils/
│  ├─ package.json
│  └─ vite.config.js
├─ backend/
│  ├─ apps/
│  │  ├─ users/
│  │  ├─ products/
│  │  ├─ cart/
│  │  ├─ orders/
│  │  └─ payment/
│  ├─ dollshop/
│  │  ├─ settings.py
│  │  └─ urls.py
│  ├─ manage.py
│  ├─ requirements.txt
│  └─ .env.example
├─ scripts/
│  ├─ startup.bat
│  └─ startup.sh
└─ docs/
```

## 项目文档

- [架构文档](docs/架构文档.md)
- [数据库设计文档](docs/数据库设计文档.md)
- [第一迭代可测试需求 v2](demand/第一次迭代-重构版-v2.md)
- [Skill 速查手册](docs/skill-速查手册.md)

## 环境要求
- Python 3.10+
- Node.js 18+
- MySQL 8+
- Redis 6+

## 快速开始

### 1) 克隆项目
```bash
git clone <your-repo-url>
cd shop
```

### 2) 后端启动
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

### 3) 前端启动
```bash
cd ../frontend
npm install
npm run dev
```

### 4) 访问地址
- 前端：`http://localhost:5173`
- 后端 API 根路径：`http://localhost:8000/api/`
- Django Admin：`http://localhost:8000/admin/`

## 环境变量
参考 [`backend/.env.example`](backend/.env.example)，关键项如下：

```env
# Django
SECRET_KEY=your-secret-key
DEBUG=True

# MySQL
DB_NAME=shop
DB_USER=root
DB_PASSWORD=root
DB_HOST=127.0.0.1
DB_PORT=3306

# Redis
REDIS_URL=redis://127.0.0.1:6379/0

# Email
EMAIL_HOST=smtp.qq.com
EMAIL_PORT=465
EMAIL_USE_SSL=True
EMAIL_USE_TLS=False
EMAIL_HOST_USER=your@qq.com
EMAIL_HOST_PASSWORD=your-smtp-auth-code
DEFAULT_FROM_EMAIL=your@qq.com

# Alipay
ALIPAY_APP_ID=
ALIPAY_PRIVATE_KEY=
ALIPAY_PUBLIC_KEY=
ALIPAY_NOTIFY_URL=http://localhost:8000/api/pay/notify/alipay/
ALIPAY_RETURN_URL=http://localhost:5173/orders
ALIPAY_DEBUG=True
```

## 运行方式

### 本地开发（推荐）
- 后端：`python manage.py runserver 0.0.0.0:8000`
- 前端：`npm run dev`

### 一键脚本
- Windows：`scripts\startup.bat`
- macOS/Linux：`./scripts/startup.sh`

> 说明：当前项目默认通过前端 Vite 代理转发 `/api` 到 `localhost:8000`。

## 核心接口总览

### 用户与地址
- `POST /api/users/users/register/`
- `POST /api/users/users/login/`
- `GET /api/users/users/captcha/`
- `POST /api/users/users/send_email_code/`
- `POST /api/users/users/forgot_password/`
- `GET /api/users/users/me/`
- `GET/POST/PUT/DELETE /api/users/addresses/`

### 商品
- `GET /api/products/categories/`
- `GET /api/products/products/`
- `GET /api/products/products/{id}/`
- `GET /api/products/products/hot_products/`
- `POST /api/products/products/{id}/upload-image/`

### 购物车
- `GET /api/cart/`
- `POST /api/cart/add/`
- `POST /api/cart/update_quantity/`
- `POST /api/cart/remove/`
- `POST /api/cart/clear/`

### 订单
- `GET /api/orders/orders/`
- `POST /api/orders/orders/create_from_cart/`
- `POST /api/orders/orders/{id}/cancel/`
- `POST /api/orders/orders/{id}/confirm_delivery/`
- `PATCH /api/orders/orders/{id}/update_shipping/`（管理员）

### 支付
- `POST /api/pay/create_payment/`
- `GET /api/pay/{out_trade_no}/status/`
- `POST /api/pay/{out_trade_no}/close/`
- `POST /api/pay/{out_trade_no}/mock_pay/`
- `GET /api/pay/query/?out_trade_no=...`
- `POST /api/pay/notify/alipay/`

### 管理端
- `/api/admin/stats/`
- `/api/admin/products/`
- `/api/admin/categories/`
- `/api/admin/orders/`
- `/api/admin/users/`

## 常见问题

### 1) `select_for_update cannot be used outside of a transaction`
支付创建时必须在事务中执行行级锁。当前代码已在 `CreatePaymentView` 使用 `transaction.atomic()` 处理。

### 2) 支付宝回调未生效
- `ALIPAY_NOTIFY_URL` 不能是 `localhost`（真实支付回调无法访问本地）
- 本地联调建议使用 ngrok 暴露后端回调地址

### 3) 验证码显示方框
确保 Pillow 可用且后端已升级到当前验证码绘制实现（默认字体 + 放大绘制）。

---
如需快速上手版命令，请看 [`QUICK_START.md`](QUICK_START.md)。
