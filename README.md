# 玩偶商城

这是我自己做的一个前后端分离电商项目，前端用 Vue 3，后端用 Django REST Framework。
这个项目主要是拿来完整练一遍商城核心业务，所以把用户、商品、购物车、订单、支付、秒杀、优惠券、退款、物流、后台管理这些模块都补起来了。

## 技术栈

### 前端
- Vue 3
- Vue Router
- Pinia
- Element Plus
- Axios
- Vite

### 后端
- Django
- Django REST Framework
- SimpleJWT
- MySQL
- Redis
- Celery
- python-alipay-sdk

## 目前做了什么

### 用户端
- 注册、登录、找回密码
- 图片验证码、邮箱验证码
- 商品列表、分类筛选、关键词搜索
- 热榜轮播、销量排行
- 购物车增删改查
- 下单、订单列表、订单详情、取消订单
- 支付创建、支付状态查询、支付关闭
- 秒杀专区、秒杀预占、秒杀下单
- 优惠券领取、价格试算、订单用券
- 按订单项数量发起部分退款
- 物流轨迹查询
- 商品评价、评价回复

### 管理端
- 商品管理
- 分类管理
- 用户管理
- 订单管理
- 发货与物流状态维护
- 秒杀活动管理
- 优惠券模板管理与发放
- 退款审核
- 支付补偿

## 项目结构

```text
shop/
├─ backend/
│  ├─ apps/
│  ├─ dollshop/
│  ├─ manage.py
│  ├─ requirements.txt
│  └─ .env.example
├─ frontend/
│  ├─ src/
│  ├─ package.json
│  └─ vite.config.js
├─ README.md
└─ .gitignore
```

## 本地怎么跑

### 1. 启动后端

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python init_data_runner.py
python manage.py runserver 0.0.0.0:8000
```

### 2. 启动前端

```bash
cd frontend
npm install
npm run dev
```

### 3. 可选：启动 Celery

```bash
cd backend
venv\Scripts\activate
celery -A dollshop worker -l info
celery -A dollshop beat -l info
```

## 配置文件

后端配置直接参考：

- `backend/.env.example`

主要会用到这些：
- MySQL
- Redis
- 邮箱验证码
- 支付配置
- 物流 provider
- Celery broker / backend

## 初始化数据

初始化脚本会生成基础分类、商品和测试数据。
如果要直接测支付、秒杀、优惠券、退款这些功能，可以先执行：

```bash
python init_data_runner.py
```

## 补充

- 这个仓库我主要保留代码和最基本的运行说明。
- 测试文档、需求文档、复盘文档、辅助脚本这些内容我放在本地维护，不跟着仓库一起提交。
