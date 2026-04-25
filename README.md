# 玩偶商城（Doll Shop）

一个基于 **Vue 3 + Django REST Framework** 的前后端分离电商项目，当前主线已完成 **Iter4（性能优化与架构治理）**。项目已经覆盖从用户认证、商品浏览、购物车、下单支付，到秒杀、优惠券、退款、物流、后台运营的完整交易闭环。

## 当前状态
- 当前发布候选分支：`iter4-main`
- 当前阶段：Iter4 已通过功能回归与性能验收，可准备合入 `main`
- 推荐阅读顺序：
  1. `QUICK_START.md`
  2. `docs/requirements/iter4/第四个迭代性能优化与架构治理.md`
  3. `docs/testing/iter4/Iter3-vs-Iter4-性能与架构优化对比报告.md`
  4. `docs/architecture/架构文档.md`
  5. `docs/architecture/业务功能与接口文档.md`
  6. `docs/architecture/数据库设计文档.md`

## 功能总览

### 用户端
- 注册 / 登录 / 忘记密码（图片验证码 + 邮箱验证码）
- 商品浏览（分类、搜索、热榜轮播、销量排行）
- 购物车（加购、数量调整、移除、清空）
- 订单（下单、列表、详情、取消）
- 支付（支付宝沙箱 / Mock、状态查询、关闭）
- 秒杀专区（活动浏览、预占、秒杀下单、预占记录）
- 优惠券（领取、试算、应用到待支付订单）
- 退款（按订单项数量发起部分退款、查看进度）
- 物流轨迹（订单详情查看物流时间线）
- 商品评价（敏感词过滤、评价回复）

### 管理端
- 仪表盘统计
- 商品管理（含图片上传、库存维护）
- 分类管理
- 用户管理
- 订单管理（发货、物流状态维护）
- 秒杀管理（活动、库存、价格、日志）
- 优惠券模板管理与发券
- 退款审核（同意 / 拒绝 + 审计日志）
- 支付补偿（手工补偿 + 定时补偿任务）

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
- MySQL
- Redis
- Celery + Celery Beat
- python-alipay-sdk

## Iter3 重点成果
- 引入优惠券试算与待支付订单锁券能力
- 引入部分退款与后台审核流
- 引入支付补偿机制（手工 + 每 15 分钟自动补偿）
- 引入物流适配层（Mock / 快递100）

## Iter4 重点成果
- 统一 `top-sales` / `hot-feed` 的 Redis feed 缓存服务
- 增加 feed 缓存命中率统计与统一失效入口
- 对订单、支付、退款、商品、秒杀高频路径补充索引
- 将订单定价、优惠券释放、feed 缓存等复杂逻辑下沉到 service 层
- 修复 `price-preview` 因日志探针导致的性能回退问题

### Iter4 验收结果
- 功能回归：全绿
- 自动化测试：`16/16` 通过
- 性能优化结果：
  - `top-sales` P95：`566.02ms -> 328.51ms`，下降 `41.96%`
  - `hot-feed` P95：`511.33ms -> 272.78ms`，下降 `46.65%`
  - `refund-create` P95：`557.44ms -> 441.51ms`，下降 `20.80%`
  - `logistics-query` P95：`366.26ms -> 348.76ms`，下降 `4.78%`
  - `price-preview` P95：`716.53ms -> 537.94ms`，下降 `24.92%`
- 缓存命中率：
  - `top-sales`：`99.34%`
  - `hot-feed`：`99.67%`

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

详细步骤见 `QUICK_START.md`

### 1) 后端
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

### 2) 前端
```bash
cd ../frontend
npm install
npm run dev
```

### 3) 可选：启动 Celery
```bash
cd backend
venv\Scripts\activate
celery -A dollshop worker -l info
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

## 文档导航
- `docs/requirements/iter3/第三个迭代需求.md`
- `docs/requirements/iter4/第四个迭代性能优化与架构治理.md`
- `docs/testing/iter4/Iter3-vs-Iter4-性能与架构优化对比报告.md`
- `docs/architecture/架构文档.md`
- `docs/architecture/业务功能与接口文档.md`
- `docs/architecture/数据库设计文档.md`
- `docs/guides/测试环境部署手册.md`
- `docs/interview-skill/项目面试问答-迭代沉淀.md`

## 说明
- 所有文档统一使用 UTF-8 编码
- `docs/testing/iter4/results/` 为本地测试结果目录，不纳入正式代码提交
