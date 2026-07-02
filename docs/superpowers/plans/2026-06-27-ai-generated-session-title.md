# AI 自动生成会话标题 — 实施计划

## 任务拆分
1. ✅ 新增 `title_generator.py` 服务
   - 接入现有 DeepSeek client
   - 实现 `generate_title(text: str, db: Session) -> str | None`
   - 输出清洗：去标点、去引号、限制 20 字以内

2. ✅ 修改 `api/summary.py`
   - 第一次总结成功后调用 `generate_title`
   - 仅当此前没有 Summary 时才更新标题（保护手动重命名）
   - 更新 `session.title` 并 commit

3. ✅ 后端测试
   - 单元测试：标题清洗逻辑
   - 单元测试：mock DeepSeek 返回
   - 集成测试：首次总结更新标题，重新总结保留手动标题

4. 前端验证
   - 上传文件后等待总结完成，观察会话列表标题变化
   - 手动重命名后不应被 AI 覆盖

## 状态
已完成实现与测试，等待真机 API 联调。

## 依赖
- DeepSeek API 可用
- 当前总结 pipeline 稳定
