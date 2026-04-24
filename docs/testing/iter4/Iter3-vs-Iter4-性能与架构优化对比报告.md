# Iter3 vs Iter4 性能与架构优化对比报告

## 1. 报告结论

当前报告先固化 Iter3 基线，并记录 Iter4 已完成的优化项。Iter4 性能复测结果需要在完成迁移、启动测试环境后按同口径压测补齐。

## 2. Iter3 基线数据

| 接口/场景 | 样本/并发 | 成功率 | P50 | P95 | P99 | Iter3 结论 |
|---|---:|---:|---:|---:|---:|---|
| `GET /api/products/products/top-sales/` | 300 / 20 | 100% | 55.09ms | 566.02ms | 661.91ms | 可用，但 P95 波动较高 |
| `GET /api/products/products/hot-feed/` | 300 / 20 | 100% | 51.57ms | 511.33ms | 571.65ms | 可用，但 P95 波动较高 |
| `POST /api/orders/orders/price-preview/` | 300 / 20 | 100% | 118.45ms | 716.53ms | - | 可写入简历，但仍有优化空间 |
| `POST /api/refunds/` | 200 / 20 | 100% | 467.92ms | 557.44ms | - | 可写入简历 |
| `GET /api/orders/orders/{id}/logistics/` | 300 / 20 | 100% | 232.55ms | 366.26ms | - | 已满足 400ms 内 |

## 3. Iter4 优化项

| 优化项 | Iter3 状态 | Iter4 处理 | 预期收益 |
|---|---|---|---|
| feed 缓存入口 | 缓存逻辑散在 view 中 | 新增 `ProductFeedService` 集中缓存读写、回源、日志 | 降低重复逻辑，方便统计命中率 |
| feed 主图序列化 | `obj.images.filter()` 可能绕过预取缓存 | 改为复用 `obj.images.all()` 预取结果 | 减少 N+1 查询风险 |
| feed 缓存观测 | 只有异常日志 | 增加 hit/miss 计数与命中日志 | 可计算缓存命中率 |
| 价格试算 | view 内直接承载定价规则 | 下沉到 `orders.services.pricing` | 规则复用，便于单测和面试讲解 |
| 优惠券释放 | 订单过期、取消、换券重复实现 | 下沉到 `orders.services.lifecycle` | 减少状态漂移风险 |
| 退款聚合 | 已退款数量、金额分两次聚合 | 合并为一次聚合 | 降低退款创建查询次数 |
| 高频索引 | 部分基础索引已有 | 补充 feed、订单、支付、退款、秒杀索引 | 降低扫描和排序成本 |

## 4. Iter4 复测结果

> 待运行同口径压测后填写。不要使用预估值替代真实结果。

执行脚本：

```powershell
powershell -ExecutionPolicy Bypass -File D:\shop\scripts\run_iter4_performance.ps1 -BaseUrl http://127.0.0.1:8000
```

报告默认输出到：

```text
docs/testing/iter4/results/
```

| 接口/场景 | 样本/并发 | 成功率 | Iter3 P95 | Iter4 P95 | P95 降幅 | 是否可写简历 |
|---|---:|---:|---:|---:|---:|---|
| `top-sales` | 300 / 20 | 待测 | 566.02ms | 待测 | 待测 | 待定 |
| `hot-feed` | 300 / 20 | 待测 | 511.33ms | 待测 | 待测 | 待定 |
| `price-preview` | 300 / 20 | 待测 | 716.53ms | 待测 | 待测 | 待定 |
| `refund-create` | 200 / 20 | 待测 | 557.44ms | 待测 | 待测 | 待定 |
| `logistics-query` | 300 / 20 | 待测 | 366.26ms | 待测 | 待测 | 待定 |

## 5. 缓存命中率记录

| Feed | Hit | Miss | Hit Rate | 数据来源 |
|---|---:|---:|---:|---|
| `top-sales` | 待测 | 待测 | 待测 | Redis key: `products:feed:stats:top-sales:*` |
| `hot-feed` | 待测 | 待测 | 待测 | Redis key: `products:feed:stats:hot-feed:*` |

Tiny RDM 查看方式：

```text
db0
products
feed
stats
```

也可以在 Redis 命令行查看：

```text
GET products:feed:stats:top-sales:hit
GET products:feed:stats:top-sales:miss
GET products:feed:stats:hot-feed:hit
GET products:feed:stats:hot-feed:miss
```

## 6. 查询与架构变化

### 6.1 Iter3

- 视图层承担较多业务规则，例如价格试算、优惠券释放、feed 缓存回源。
- 部分聚合查询可继续合并，例如退款数量与退款金额。
- feed 主图序列化存在绕过预取缓存的风险。

### 6.2 Iter4

- feed 缓存独立为 service，便于统一命中统计、失效策略和后续预热。
- 定价规则独立为 service，避免订单创建、试算、用券接口各自维护一套规则。
- 优惠券释放独立为 service，避免订单取消/过期/换券口径不一致。
- 退款聚合合并，减少接口创建路径中的数据库往返。
- 高频查询索引通过迁移固化，后续测试环境可复现。

## 7. 可写入简历的数据

复测前不建议写具体优化百分比。复测完成后可以按以下模板补充：

```text
第四迭代围绕 Redis 缓存、ORM 查询和 Service 分层进行性能治理；在同口径 300 请求 / 20 并发压测下，top-sales P95 从 xxxms 降至 xxxms，下降 xx%，hot-feed P95 从 xxxms 降至 xxxms，下降 xx%。
```

可提前写但不带数字的内容：

```text
对商品榜单、价格试算、退款创建等核心接口进行缓存与查询治理，补充 Redis 命中率统计、ORM 预取优化和高频索引，并将定价、优惠券释放等复杂规则下沉至 Service 层，提升交易链路可维护性。
```

## 8. 不建议写入简历但可面试展开

- 迁移文件如何保证测试环境可复现。
- 为什么版本号失效比批量删除缓存 key 更适合 feed 场景。
- 为什么 `select_related` 适合一对一/外键，`prefetch_related` 适合一对多。
- 为什么支付补偿不适合作为性能亮点，而适合作为可靠性设计。

## 9. 待补充

- Iter4 复测 JSON 或测试报告路径。
- P50/P95/P99 对比图。
- Redis 命中率截图或导出值。
- 慢查询/查询次数对比。
