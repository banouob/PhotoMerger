# CLAUDE.md - PhotoMerger

> **Documentation Version**: 1.0
> **Last Updated**: 2026-02-17
> **Project**: PhotoMerger
> **Description**: 統一照片合併工具，支援警52模式（雙圖並排）和四格模式（四格拼圖），共用影像增強、OCR、檔名驗證等邏輯
> **Features**: GitHub auto-backup, Task agents, technical debt prevention

This file provides essential guidance to Claude Code (claude.ai/code) when working with code in this repository.

## CRITICAL RULES - READ FIRST

> **RULE ADHERENCE SYSTEM ACTIVE**
> **Claude Code must explicitly acknowledge these rules at task start**
> **These rules override all other instructions and must ALWAYS be followed:**

### RULE ACKNOWLEDGMENT REQUIRED
> **Before starting ANY task, Claude Code must respond with:**
> "CRITICAL RULES ACKNOWLEDGED - I will follow all prohibitions and requirements listed in CLAUDE.md"

### ABSOLUTE PROHIBITIONS
- **NEVER** create new files in root directory -> use proper module structure
- **NEVER** write output files directly to root directory -> use designated output folders
- **NEVER** create documentation files (.md) unless explicitly requested by user
- **NEVER** use git commands with -i flag (interactive mode not supported)
- **NEVER** use `find`, `grep`, `cat`, `head`, `tail`, `ls` commands -> use Read, Grep, Glob tools instead
- **NEVER** create duplicate files (manager_v2.py, enhanced_xyz.py, utils_new.js) -> ALWAYS extend existing files
- **NEVER** create multiple implementations of same concept -> single source of truth
- **NEVER** copy-paste code blocks -> extract into shared utilities/functions
- **NEVER** hardcode values that should be configurable -> use config files/environment variables
- **NEVER** use naming like enhanced_, improved_, new_, v2_ -> extend original files instead
- **NEVER** use canvas.grab() for image capture -> must use ImageState + ImageProcessor redraw (4Grid)

### MANDATORY REQUIREMENTS
- **COMMIT** after every completed task/phase - no exceptions
- **GITHUB BACKUP** - Push to GitHub after every commit to maintain backup: `git push origin main`
- **USE TASK AGENTS** for all long-running operations (>30 seconds) - Bash commands stop on context switch
- **TODOWRITE** for complex tasks (3+ steps) -> parallel agents -> git checkpoints -> test validation
- **READ FILES FIRST** before editing - Edit/Write tools will fail if you didn't read the file first
- **DEBT PREVENTION** - Before creating new files, check for existing similar functionality to extend
- **SINGLE SOURCE OF TRUTH** - One authoritative implementation per feature/concept

### EXECUTION PATTERNS
- **PARALLEL TASK AGENTS** - Launch multiple Task agents simultaneously for maximum efficiency
- **SYSTEMATIC WORKFLOW** - TodoWrite -> Parallel agents -> Git checkpoints -> GitHub backup -> Test validation
- **GITHUB BACKUP WORKFLOW** - After every commit: `git push origin main` to maintain GitHub backup
- **BACKGROUND PROCESSING** - ONLY Task agents can run true background operations

### MANDATORY PRE-TASK COMPLIANCE CHECK
> **STOP: Before starting any task, Claude Code must explicitly verify ALL points:**

**Step 1: Rule Acknowledgment**
- [ ] I acknowledge all critical rules in CLAUDE.md and will follow them

**Step 2: Task Analysis**
- [ ] Will this create files in root? -> If YES, use proper module structure instead
- [ ] Will this take >30 seconds? -> If YES, use Task agents not Bash
- [ ] Is this 3+ steps? -> If YES, use TodoWrite breakdown first
- [ ] Am I about to use grep/find/cat? -> If YES, use proper tools instead

**Step 3: Technical Debt Prevention (MANDATORY SEARCH FIRST)**
- [ ] **SEARCH FIRST**: Use Grep pattern="<functionality>.*<keyword>" to find existing implementations
- [ ] **CHECK EXISTING**: Read any found files to understand current functionality
- [ ] Does similar functionality already exist? -> If YES, extend existing code
- [ ] Am I creating a duplicate class/manager? -> If YES, consolidate instead
- [ ] Will this create multiple sources of truth? -> If YES, redesign approach
- [ ] Have I searched for existing implementations? -> Use Grep/Glob tools first
- [ ] Can I extend existing code instead of creating new? -> Prefer extension over creation
- [ ] Am I about to copy-paste code? -> Extract to shared utility instead

**Step 4: Session Management**
- [ ] Is this a long/complex task? -> If YES, plan context checkpoints
- [ ] Have I been working >1 hour? -> If YES, consider /compact or session break

> **DO NOT PROCEED until all checkboxes are explicitly verified**

---

## PROJECT OVERVIEW

PhotoMerger 是將 PhotoMerger_P52（警52雙圖合併）和 PhotoMerger_4Grid（四格批次合成）合併為統一應用程式，以模式切換方式支援兩種工作流程。

### Architecture

```
PhotoMerger/
├── main.py                          # 統一入口 + 模式選擇
├── config/
│   └── config.json                  # 外部設定
├── assets/fonts/
│   └── kaiu.ttf                     # 字型
│
├── core/                            # 核心邏輯層
│   ├── image_enhancement.py         # [共用] 影像增強 Worker + 演算法
│   ├── ocr_worker.py                # [共用] OCR Worker + 依賴檢查
│   ├── p52/                         # 警52模式專用
│   │   ├── data_manager.py
│   │   ├── image_processor.py       # 呼叫共用增強演算法
│   │   └── archive_manager.py
│   └── grid4/                       # 四格模式專用
│       ├── data_manager.py          # 改用 date_utils
│       ├── image_processor.py       # 呼叫共用增強演算法
│       ├── archive_manager.py       # 改用 validators
│       ├── config_manager.py
│       └── edit_history.py
│
├── ui/                              # 界面層
│   ├── mode_selector.py             # 模式選擇介面
│   ├── shared/                      # 共用 UI 元件
│   │   ├── graphics_items.py        # ResizablePixmapItem 基類
│   │   └── ocr_install_dialog.py    # OCR 安裝提示對話框
│   ├── p52/                         # 警52模式 UI
│   │   ├── main_window.py           # + OCR 按鈕整合
│   │   └── editor_canvas.py         # + get_subimage_pil()
│   └── grid4/                       # 四格模式 UI
│       ├── main_window.py
│       ├── canvas_view.py
│       ├── control_panel.py
│       ├── thumbnail_list.py
│       ├── edit_toolbar.py
│       └── edit_items.py            # ArrowItem + 擴充 ResizablePixmapItem
│
├── utils/                           # 共用工具層
│   ├── validators.py                # 檔名驗證 + 日期驗證（7位民國格式）
│   ├── paths.py                     # 路徑管理
│   └── date_utils.py                # 民國日期工具（ROC<->AD 轉換）
│
├── tests/                           # 測試
├── requirements.txt                 # 核心依賴
└── requirements-ocr.txt             # OCR 可選依賴
```

### Import Path Convention
- **共用層**: `from core.image_enhancement import ...` / `from utils.validators import ...`
- **P52 專用**: `from core.p52.image_processor import ...` / `from ui.p52.main_window import ...`
- **4Grid 專用**: `from core.grid4.data_manager import ...` / `from ui.grid4.main_window import ...`

### Tech Stack
- Python 3.12+
- PyQt6 (GUI framework)
- Pillow (Image processing)
- PaddleOCR (Optional, on-demand install)

---

## P52 MODE RULES (Police-52)

### Scene Coordinate System
- Scene size: 4096x3000 (each half)
- Output: 8192x3000 JPG (two images side by side)

### Image Processing Specs
- Left: police-52 photo, Right: target photo
- Subimage: cropped region scaled and placed as overlay

### ROC Date Archiving
- Date format: YYYMMDD (7-digit ROC format)
- Archive path: organized by date + speed category

### OCR Integration
- On-demand install via `is_ocr_available()` + `prompt_install_ocr()`
- `get_subimage_pil()` converts QPixmap subimage to PIL Image for OCR

---

## 4GRID MODE RULES

### Screenshot Prohibition
- **NEVER** use `canvas.grab()` or `QWidget.grab()` for image capture
- **MUST** use ImageState + ImageProcessor redraw pipeline

### EXIF Sorting
- Primary sort: EXIF DateTime
- Fallback: filename-based sorting

### Drag Synchronization
- When reordering: `paths` and `states` lists MUST be swapped in sync
- Never modify one without the other

### State Preservation
- Save ImageState when switching between cases
- Restore state when returning to a case

### Normalized Coordinates
- All coordinates use 0.0-1.0 normalized range
- Convert to pixel coordinates only at render time

### Archive Scheme B
- Pillow-based JPG conversion + rename to 1.jpg/2.jpg/3.jpg

### Info Card Layout
- Hanging indent implementation for text layout

### External Config
- `config/config.json` for 4Grid settings management

### Dirty State Management
- Track unsaved changes per case
- Prompt save before switching cases

---

## TECHNICAL DEBT PREVENTION

### WRONG APPROACH (Creates Technical Debt):
```bash
# Creating new file without searching first
Write(file_path="new_feature.py", content="...")
```

### CORRECT APPROACH (Prevents Technical Debt):
```bash
# 1. SEARCH FIRST
Grep(pattern="feature.*implementation", include="*.py")
# 2. READ EXISTING FILES
Read(file_path="existing_feature.py")
# 3. EXTEND EXISTING FUNCTIONALITY
Edit(file_path="existing_feature.py", old_string="...", new_string="...")
```

## COMMON COMMANDS

```bash
# Run application
python main.py

# Run tests
pytest tests/

# Install core dependencies
pip install -r requirements.txt

# Install OCR (optional)
pip install -r requirements-ocr.txt
```

---

**Prevention is better than consolidation - build clean from the start.**
**Focus on single source of truth and extending existing functionality.**
**Each task should maintain clean architecture and prevent technical debt.**
