# 玩偶商城（Doll Shop）

一个基于 **Vue 3 + Django REST Framework** 的前后端分离电商项目。  
当前代码主线已进入 **Iter3（交易与履约增强）**，覆盖优惠券、部分退款、支付补偿、物流轨迹等能力。

## 当前版本
- 推荐开发分支：`iter3/main`
- 文档主入口：
  - `docs/requirements/iter3/第三个迭代需求.md`
  - `docs/architecture/架构文档.md`
  - `docs/architecture/业务功能与接口文档.md`
  - `docs/architecture/数据库设计文档.md`

## 功能总览

### 用户端
- 登录/注册/忘记密码（图片验证码 + 邮箱验证码）
- 商品首页（搜索、分类筛选、热榜轮播、销量排行）
- 商品详情（加购、评价、回复）
- 购物车（数量调整、移除、清空）
- 订单（下单、列表、详情、取消）
- 支付（支付宝/Mock、状态查询、关闭）
- 秒杀专区（活动浏览、预占、秒杀下单、预占记录）
- 优惠券（领取、试算、应用到待支付订单）
- 退款（按订单项数量发起部分退款、查看退款进度）
- 物流轨迹（订单详情查看发货轨迹）

### 管理端
- 仪表盘统计
- 商品管理（含图片上传、库存调整）
- 分类管理
- 用户管理
- 订单管理（发货、物流状态维护）
- 秒杀管理（活动、库存、价格、日志）
- 优惠券管理（模板管理、发券）
- 退款审核（同意/拒绝 + 审计日志）
- 支付补偿（手工触发 + 定时任务自动补偿）

## 技术栈

### 前端
- Vue 3
- Vue Router 4
- Pinia
- Element Plus
- Axios
- Vite

### 后端
- Django 4.2
- Django REST Framework
- SimpleJWT
- django-filter
- django-cors-headers
- MySQL
- Redis
- Celery + Celery Beat
- python-alipay-sdk

## 目录结构（核心）

```text
shop/
├─ frontend/
│  ├─ src/
│  ├─ package.json
│  └─ vite.config.js
├─ backend/
│  ├─ apps/
│  │  ├─ users/
│  │  ├─ products/
│  │  ├─ cart/
│  │  ├─ orders/
│  │  ├─ payment/
│  │  ├─ reviews/
│  │  ├─ seckill/
│  │  ├─ coupons/
│  │  └─ refunds/
│  ├─ dollshop/
│  ├─ manage.py
│  ├─ requirements.txt
│  └─ .env.example
├─ deploy/
├─ docs/
├─ QUICK_START.md
└─ README.md
```

## 快速启动

详细步骤见 `QUICK_START.md`。

### 1) 后端

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

### 2) 前端

```bash
cd ../frontend
npm install
npm run dev
```

### 3) 可选：启动补偿任务（Iter3 推荐）

```bash
# 终端A
cd backend
venv\Scripts\activate
celery -A dollshop worker -l info

# 终端B
cd backend
venv\Scripts\activate
celery -A dollshop beat -l info
```

## 关键环境变量

请参考：`backend/.env.example`

重点变量：
- 数据库：`DB_*`
- Redis：`REDIS_URL`
- 邮件：`EMAIL_*`
- 支付宝：`ALIPAY_*`
- 物流：`LOGISTICS_PROVIDER`、`KUAIDI100_API_KEY`、`KUAIDI100_CUSTOMER`
- 补偿任务：`CELERY_BROKER_URL`、`CELERY_RESULT_BACKEND`
- 满减规则：`ORDER_FULL_REDUCTION_RULES`

## 核心接口（摘要）

- 用户：`/api/users/**`
- 商品与分类：`/api/products/**`
- 购物车：`/api/cart/**`
- 订单：`/api/orders/**`
- 支付：`/api/pay/**`
- 秒杀：`/api/seckill/**`
- 评价：`/api/reviews/**`
- 优惠券：`/api/coupons/**`
- 退款：`/api/refunds/**`
- 后台：`/api/admin/**`

## Iter3 新增接口（关键）

- `POST /api/orders/price-preview/`
- `POST /api/orders/{order_id}/apply-coupon/`
- `GET /api/orders/{id}/logistics/`
- `GET /api/refunds/my/`
- `PATCH /api/admin/refunds/{id}/review/`
- `POST /api/pay/reconcile/`

说明：为兼容旧前端，部分历史路径（如 `/api/orders/orders/...`）仍保留别名。

## 文档导航

- `docs/requirements/iter3/第三个迭代需求.md`
- `docs/architecture/架构文档.md`
- `docs/architecture/业务功能与接口文档.md`
- `docs/architecture/数据库设计文档.md`
- `docs/guides/测试环境部署手册.md`
- `docs/interview-skill/项目面试问答-迭代沉淀.md`
- `docs/interview-skill/第三次迭代-交易与履约面试沉淀.md`

## 说明

- 文档统一 UTF-8 编码。
- 若遇 Git 锁文件冲突（`index.lock`），先关闭 Git 占用进程再执行提交。
