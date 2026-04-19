# Iter2 RC1 缺陷清单

- 基线分支：`test/iter2-rc1`
- 执行日期：`2026-04-19`
- 整理口径：按根因合并，便于直接提交 GitHub Issues

## BUG-ITER2-001 后台评价审核接口整组缺失

- 基线版本：`iter2-rc1`
- 严重程度：高
- 发布影响：阻塞二迭代 RC1 发布
- 建议 GitHub issue 标题：`[iter2-rc1] 后台评价审核接口整组缺失，GET /api/admin/reviews/ 返回 404`
- 影响范围：
  - 评价审核列表
  - 状态筛选
  - 商品/用户组合筛选
  - 审核通过/驳回
  - 重复审核终态校验
- 关联用例：
  - `TC-I2-ARV-001`
  - `TC-I2-ARV-002`
  - `TC-I2-ARV-003`
  - `TC-I2-ARV-004`
  - `TC-I2-ARV-005`
  - `TC-I2-ARV-006`
  - `TC-I2-ARV-007`
  - `TC-I2-ARV-008`
- 复现步骤：
  1. 管理员访问 `GET /api/admin/reviews/`
  2. 或调用 `PATCH /api/admin/reviews/{id}/audit/`
  3. 观察响应结果
- 实际结果：
  - 返回 `404`
  - 后台评价审核整组接口不可用
- 期望结果：
  - 审核列表和审核动作路由正常注册
  - 管理员可查询和审核评价
- 根因说明：
  - `AdminReviewViewSet` 已存在，但 `apps.users.admin_urls` 未注册 `reviews` 路由
- 相关文档：
  - [iter2-rc1-测试报告.md](D:/shop-test/doll-shop/docs/testing/iter2/iter2-rc1-测试报告.md)
  - [iter2-rc1-缺陷清单.md](D:/shop-test/doll-shop/docs/testing/iter2/iter2-rc1-缺陷清单.md)

## BUG-ITER2-002 已取消待支付订单仍可继续 mock_pay

- 基线版本：`iter2-rc1`
- 严重程度：高
- 发布影响：阻塞二迭代 RC1 发布
- 建议 GitHub issue 标题：`[iter2-rc1] 已取消待支付订单仍可继续 mock_pay`
- 影响范围：
  - 订单状态一致性
  - 支付状态一致性
  - 支付补偿与回归场景
- 关联用例：
  - `TC-I2-PY-006`
- 复现步骤：
  1. 创建一笔待支付订单并生成支付单
  2. 调用订单取消接口，订单取消成功
  3. 再调用 `POST /api/pay/{payment_id}/mock_pay/`
  4. 观察订单与支付状态
- 实际结果：
  - `mock_pay` 仍返回成功
  - 已取消订单被标记为已支付，状态发生漂移
- 期望结果：
  - 已取消订单关联的支付单不允许继续支付
  - 接口应返回关闭/失效错误
- 相关文档：
  - [iter2-rc1-测试报告.md](D:/shop-test/doll-shop/docs/testing/iter2/iter2-rc1-测试报告.md)
  - [iter2-rc1-缺陷清单.md](D:/shop-test/doll-shop/docs/testing/iter2/iter2-rc1-缺陷清单.md)

## BUG-ITER2-003 普通用户可读取其他用户详情

- 基线版本：`iter2-rc1`
- 严重程度：高
- 发布影响：阻塞二迭代 RC1 发布
- 建议 GitHub issue 标题：`[iter2-rc1] 普通用户可读取其他用户详情`
- 影响范围：
  - 用户资料对象级隔离
  - 账户与权限回归
- 关联用例：
  - `TC-I2-RG-003`
- 复现步骤：
  1. 使用普通用户 A 登录
  2. 访问另一个普通用户 B 的详情接口 `/api/users/users/{id}/`
  3. 观察响应结果
- 实际结果：
  - 返回 `200`
  - 可读取其他用户资料
- 期望结果：
  - 非本人应返回 `404` 或等价的对象级拒绝结果
- 相关文档：
  - [iter2-rc1-测试报告.md](D:/shop-test/doll-shop/docs/testing/iter2/iter2-rc1-测试报告.md)
  - [iter2-rc1-缺陷清单.md](D:/shop-test/doll-shop/docs/testing/iter2/iter2-rc1-缺陷清单.md)

## BUG-ITER2-004 后台商品更新后 feed 缓存不失效

- 基线版本：`iter2-rc1`
- 严重程度：中
- 发布影响：非阻塞，但影响数据一致性与后续缓存回归
- 建议 GitHub issue 标题：`[iter2-rc1] 后台商品更新后 feed 缓存未失效`
- 影响范围：
  - `hot-feed`
  - feed 缓存恢复稳定性
  - 首页热榜展示一致性
- 关联用例：
  - `TC-I2-PF-005`
  - `TC-I2-PF-006`
- 复现步骤：
  1. 先访问 `hot-feed` 预热缓存
  2. 通过后台商品接口修改商品价格
  3. 再次请求 `hot-feed`
  4. 对比返回价格与最新商品数据
- 实际结果：
  - 返回的仍是旧价格
  - feed 版本号未更新
- 期望结果：
  - 后台商品更新后应触发 feed 缓存失效
  - 后续读取应返回新数据
- 相关文档：
  - [iter2-rc1-测试报告.md](D:/shop-test/doll-shop/docs/testing/iter2/iter2-rc1-测试报告.md)
  - [iter2-rc1-缺陷清单.md](D:/shop-test/doll-shop/docs/testing/iter2/iter2-rc1-缺陷清单.md)

## GitHub 提交建议

建议按 4 条独立 Issue 提交，每条 Issue 在正文里带上：

- 基线：`iter2-rc1`
- 关联用例编号
- 复现步骤
- 实际结果
- 期望结果
- 引用本清单和测试报告
