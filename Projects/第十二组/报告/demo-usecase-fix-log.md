# 演示/使用场景修复日志（demo-usecase-fix-log）

> 对应排查报告：`report\demo-usecase-audit.md`。修复顺序：演示优先（P0）→ 日常使用（P1/P2）→ 打磨（P3）。

## 一、已修项

### FIX-D1 [P2] 消息内容大小上限
- **文件**：`probe\hub-fix\src\policy.mjs`
- **原因**：session/prompt 与 updateQueue edit 的纯文本无长度上限，1MB 消息实测直达上游，重复大消息可致内存/队列膨胀。
- **修改**：纯文本总长上限 64KB（`promptChars > 64*1024` → 「消息过长（单次最多 64KB）」），updateQueue edit 同步约束。
- **回归**：70KB 拒 / 短消息正常 ✅。

### FIX-D2 [P2] 禁用账号主动断开 WS
- **文件**：`probe\hub-fix\src\server.mjs`（`/users/<name>/status` 路由）
- **原因**：禁用只撤销会话，已建立的 WS 要等用户下次发消息才断，被禁成员持续收流。
- **修改**：禁用时遍历 `context.memberStreams`，关闭该用户全部连接（1008），并清空其流表。
- **回归**：audit3/audit5 禁用后 800ms 内 WS close ✅（REST 302 即时生效原有行为不变）。

### FIX-D3 [P3] 重复 requestId 去重（含策略感知）
- **文件**：`probe\hub-fix\src\server.mjs`（handleApiPost + `context.promptReceipts`）
- **原因**：同 requestId 重复提交两次入队（双击/刷新产生重复消息）；初版去重命中缓存直接回放，撤销共享后仍回放旧成功回执（rehearse 8b 击穿）。
- **修改**：按 `用户\0会话\0requestId` 缓存回执 30 秒；**命中缓存前重跑守卫**，权限已变则作废缓存走正常拒绝；缓存上限 500 条简易淘汰。
- **回归**：双击返回同 envelope ✅；rehearse 16/16（撤销后拒发恢复）✅。

## 二、未修项与演示兜底

| 项 | 原因 | 风险 | 兜底 |
|---|---|---|---|
| key 耗尽时前端提示不够直白（B 类） | 改 key 属破坏用户凭据，不能实测 | 演示中身份牌依赖模型回复 | 三张牌（权限/时间线/用量）不需模型；口播"为省 key 测试不调真模型"；到场先跑通一次 |
| 休眠唤醒未验证（B 类） | 沙箱无法真实休眠 | 低 | WS 重连 + 会话 14 天 TTL 兜底；现场重启 start-all 2 分钟 |
| 小时级挂机内存增长未量化（B 类） | 无长挂机条件 | 低 | 演示场景不存在；发布前可做 24h 挂机 |

## 三、回归命令与结果

```
node probe\hub-fix\bin\dsh-team-hub.js selftest   → ✓（42+ sessions / 6 workspaces）
demo\rehearse.ps1（16 断言）                       → ✅ 16/16（FIX-D3 修完后）
演示批次（A2-A5、B2、B3、B5，含 2 次真实模型调用） → ✅ 18/19 → 修复后全绿
D 修复回归（长度上限/去重/禁用断流）                → ✅ 5/5 + audit5 复验通过
```

## 四、交付状态

- 配置已复位：admin/alice/bob/carol 首登强制改密、无测试账号残留、共享/转交清空。
- 备份：`hubhome\backup-demo-audit-20261121\`。
- 修复需随最终安装包重编生效。
