# 玩偶商城（Doll Shop）

一个基于 **Vue 3 + Django REST Framework** 的全栈电商项目。

当前主线能力已覆盖：账号体系、商品浏览、购物车、订单、支付、评价互动、秒杀专区、后台管理与测试文档沉淀。

## 当前版本
- 分支建议：`iter2/main`
- 文档口径：第二次迭代（Iter2）

## 功能总览

### 用户端
- 登录/注册/忘记密码（图片验证码 + 邮箱验证码）
- 商品首页：搜索、分类筛选、热榜轮播、销量排行
- 商品详情：查看详情、加购、查看/发布评价、评价回复
- 购物车：数量调整、移除、清空
- 订单：下单、查看列表/详情、取消待支付
- 支付：支付宝/Mock 创建支付，查询状态，关闭支付单
- 秒杀：秒杀专区、预占、基于预占下单、我的预占记录
- 个人中心：用户信息与收货地址管理

### 管理端
- 仪表盘统计
- 商品管理（含图片上传、库存调整）
- 分类管理
- 订单管理（发货、状态流转）
- 用户管理（启用/禁用、角色切换）
- 秒杀管理：
  - 活动管理（支持同组多商品）
  - 状态管理（draft/preheating/online/ended/offline）
  - 秒杀价格/库存调整
  - 预占记录与操作日志

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
- Redis（缓存/验证码/排行榜等场景）
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
│  │  └─ seckill/
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

详细步骤见 [QUICK_START.md](QUICK_START.md)。

最小启动流程：

### 1) 启动后端
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

### 2) 启动前端
```bash
cd ../frontend
npm install
npm run dev
```

### 3) 访问
- 前端：<http://localhost:5173>
- 后端 API 根：<http://localhost:8000/api/>
- Django Admin：<http://localhost:8000/admin/>

## 关键环境变量

请参考：[`backend/.env.example`](backend/.env.example)

重点包含：
- MySQL：`DB_*`
- Redis：`REDIS_URL`
- 邮件：`EMAIL_*`
- 支付宝：`ALIPAY_*`

## 核心接口（摘要）

- 用户：`/api/users/**`
- 商品与分类：`/api/products/**`
- 评价：`/api/reviews/**`
- 购物车：`/api/cart/**`
- 订单：`/api/orders/**`
- 支付：`/api/pay/**`
- 秒杀：`/api/seckill/**`
- 后台：`/api/admin/**`

## 文档导航

- 架构文档：[`docs/architecture/架构文档.md`](docs/architecture/架构文档.md)
- 数据库设计：[`docs/architecture/数据库设计文档.md`](docs/architecture/数据库设计文档.md)
- 业务与接口：[`docs/architecture/业务功能与接口文档.md`](docs/architecture/业务功能与接口文档.md)
- 测试环境部署：[`docs/guides/测试环境部署手册.md`](docs/guides/测试环境部署手册.md)
- 第二次迭代需求：[`docs/requirements/iter2/第二个迭代需求.md`](docs/requirements/iter2/第二个迭代需求.md)

## 说明
- 本项目文档统一使用 UTF-8 编码。
- 如遇 Git 锁文件冲突（`index.lock`），请先结束后台 Git 进程后再提交。
