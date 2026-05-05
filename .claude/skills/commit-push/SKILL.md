---
name: commit-push
description: 提交所有變更並推送至 origin main。僅由使用者手動觸發。
disable-model-invocation: true
---

## 提交並推送變更

依照專案慣例，每完成一個任務後提交變更並推送至 `origin main`。

### 參數

`$ARGUMENTS` — commit 訊息（必填）

### 步驟

1. 執行 `git status` 確認有待提交的變更
2. 執行 `git diff` 與 `git diff --cached` 檢視變更內容
3. 將所有變更加入暫存：`git add -A`
4. 提交：`git commit -m "$ARGUMENTS"`
5. 推送：`git push origin main`
6. 執行 `git status` 確認推送成功

### 注意

- commit 訊息請使用繁體中文
- 遵循現有 commit 慣例：`type(scope): 簡短描述`（例如 `feat(p52): 新增警員資訊輸入`）
