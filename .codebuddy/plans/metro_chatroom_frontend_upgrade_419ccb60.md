---
name: metro_chatroom_frontend_upgrade
overview: 升级聊天室前端界面以支持多行文本输入、Ctrl+Enter 发送、自动时间戳显示，并优化 Metro 设计风格。
design:
  architecture:
    framework: html
  styleKeywords:
    - Metro 设计风格
    - 简洁现代
    - 清晰对比
    - 圆角气泡
    - 微交互动画
    - 响应式适配
  fontSystem:
    fontFamily: Segoe UI
    heading:
      size: 18px
      weight: 600
    subheading:
      size: 14px
      weight: 500
    body:
      size: 12px
      weight: 400
  colorSystem:
    primary:
      - "#0078D4"
      - "#00BCD4"
      - "#4CAF50"
    background:
      - "#FFFFFF"
      - "#f0f0f0"
      - "#e3f2fd"
      - "#e8f5e9"
    text:
      - "#212121"
      - "#555555"
      - "#999999"
    functional:
      - "#F44336"
      - "#4CAF50"
      - "#FFC107"
todos:
  - id: update-html-structure
    content: 更新 HTML 结构：将 input#input 改为 textarea，调整 inputArea 布局，优化消息容器 DOM 结构
    status: completed
  - id: enhance-css-styles
    content: 增强 CSS 样式：添加 textarea 样式、新增消息气泡样式(圆角、阴影、分离布局)、优化响应式媒体查询
    status: completed
    dependencies:
      - update-html-structure
  - id: implement-keyboard-handler
    content: 实现 Ctrl+Enter 键盘事件处理：监听 textarea keydown、检测组合键、阻止默认行为、支持跨浏览器
    status: completed
    dependencies:
      - update-html-structure
  - id: add-timestamp-frontend
    content: 前端实现时间戳生成与显示：创建 formatTime 函数、修改消息接收处理逻辑、解析新消息格式
    status: completed
    dependencies:
      - implement-keyboard-handler
  - id: update-backend-message-format
    content: 后端更新消息格式：修改 broadcast_message() 方法，生成 timestamp 字段、返回 JSON 包含 username 和 timestamp
    status: completed
  - id: test-integration
    content: 测试集成：验证 Ctrl+Enter 发送、Enter 换行、消息显示时间戳、响应式布局、跨浏览器兼容性
    status: completed
    dependencies:
      - add-timestamp-frontend
      - update-backend-message-format
---

## 用户需求

### 功能需求

1. **多行文本输入**：将单行文本输入框替换为文本区域(textarea)，支持多行消息输入
2. **Ctrl+Enter发送**：修改键盘事件处理，使用 Ctrl+Enter 组合键发送消息，普通 Enter 键仅用于换行
3. **消息时间戳**：每条消息自动添加时间戳显示，格式为24小时制 HH:mm:ss
4. **消息气泡优化**：改进消息显示样式，包括圆角、阴影、适当间距、背景色区分(自己的消息与他人消息)

### 设计需求

- 保持 Metro 设计风格的简洁现代特征
- 清晰的视觉层次，区分自己发送的消息和接收的消息
- 响应式布局，在不同设备尺寸上(桌面、平板、手机)都能良好显示
- textarea 组件美观且易用

### 消息格式规范

- 前端自动生成时间戳，不依赖后端
- 消息显示结构：用户名、时间戳、消息内容分离显示
- 后端可选升级：添加 timestamp 字段到消息 JSON 中，前端优先使用后端时间戳

## 技术栈

- **前端框架**：HTML5 + Vanilla JavaScript(无框架)
- **样式系统**：CSS3(已有 metro.css，保持现有设计语言)
- **后端框架**：FastAPI + WebSocket(已有)
- **实时通信**：WebSocket(已有)

## 实现方案

### 核心设计决策

#### 1. Textarea 多行输入

- 将 `<input type="text" id="input">` 改为 `<textarea id="input">`
- 设置合理的行高和最大高度，支持滚动
- 保持 Metro 设计的清洁外观

#### 2. Ctrl+Enter 快捷键

- 监听 `keydown` 事件(而非 keyup)，检测 `event.ctrlKey && event.key === 'Enter'`
- 普通 Enter 允许默认行为(换行)，使用 `event.preventDefault()` 仅在 Ctrl+Enter 时发送
- 确保跨浏览器兼容性

#### 3. 时间戳实现策略

- **前端时间生成**：优先实现。使用 JavaScript `Date` 对象生成当前时间，格式化为 HH:mm:ss
- **后端时间戳**：消息格式改为 `{type: 'message', username: 'xxx', text: 'yyy', timestamp: 'HH:mm:ss'}`，但前端可不依赖
- 时间戳显示在消息气泡中，独立的元素便于样式控制

#### 4. 消息 DOM 结构优化

- 原结构：`<div class="message-item">username: message</div>`
- 新结构：`<div class="message-item"><span class="msg-user">username</span><span class="msg-time">HH:mm:ss</span><span class="msg-text">message</span></div>`
- 分离结构使样式更灵活，支持网格/弹性布局

#### 5. 消息气泡样式

- 添加圆角(border-radius)、轻微阴影(box-shadow)、内边距
- 自己的消息和他人消息使用不同背景色(green vs blue)和不同对齐
- 避免过度装饰，保持 Metro 风格的简洁

### 实现细节

#### 键盘事件处理

```
监听 textarea keydown 事件：
- 检测 Ctrl+Enter：调用发送逻辑，阻止默认行为
- 其他情况：允许默认行为(Enter 换行)
- 考虑 macOS Command 键兼容性(可选)
```

#### 后端改动(可选/兼容)

- `broadcast_message()` 方法：将格式从 `{type:'message', text:'username: message'}` 改为 `{type:'message', username:'xxx', text:'yyy', timestamp:'HH:mm:ss'}`
- 后端生成时间戳(Python datetime)，与前端时间戳同步
- 前端接收新格式消息时解析 username 和 timestamp 字段

#### 前端时间戳生成函数

```
function formatTime(date = new Date()) {
  const h = String(date.getHours()).padStart(2, '0');
  const m = String(date.getMinutes()).padStart(2, '0');
  const s = String(date.getSeconds()).padStart(2, '0');
  return `${h}:${m}:${s}`;
}
```

### 性能与兼容性

- **性能**：时间戳生成O(1)，无额外网络开销。消息 DOM 插入仍为O(1)平均
- **兼容性**：Textarea、keydown 事件、Date API 均为广泛支持的标准API
- **响应式**：现有 CSS 已支持响应式，textarea 宽度继承 #input 样式即可

## 设计方案

### 整体设计风格

保持现有 Metro 设计语言，强化以下要素：

- **简洁现代**：清晰的排版、充分的留白、直观的视觉信息
- **对比感**：通过颜色、大小、排列方向区分自己与他人的消息
- **微交互**：淡入动画(fadeIn)、hover 效果、focus 状态清晰
- **响应式**：从桌面(1200px+) 到手机(480px)的平滑适配

### 核心视觉变化

#### 1. Textarea 输入框

- **样式**：保持 Metro 风格的边框、阴影、hover 效果
- **尺寸**：多行显示，建议最小高度 60px，最大高度 150px(含滚动条)
- **提示文本**：更新为 "按 Ctrl+Enter 发送，Enter 换行..."
- **对焦效果**：边框变蓝(primary-color)，阴影增强

#### 2. 消息气泡重设计

- **气泡容器**：圆角 8px、阴影 0 2px 8px rgba(0,0,0,0.1)、内边距 12px 16px
- **用户名标签**：字体加粗(600 weight)、大小 13px、颜色 #555
- **时间戳标签**：字体较小(11px)、颜色 #999、右对齐或紧跟用户名
- **消息文本**：字体 14px、行高 1.5、支持多行自然换行
- **自己消息**：背景 #e8f5e9(淡绿)、左对齐、箭头指向右方(可选)
- **他人消息**：背景 #e3f2fd(淡蓝)、左对齐、正常排列
- **动画**：fadeIn 0.3s 淡入效果

#### 3. 消息区域布局

- **消息流**：从上到下排列，新消息自动滚动到底部
- **间距**：消息间竖直间距 8px、消息与容器边距 16px
- **背景**：保持白色，便于长时间阅读

#### 4. 输入区域

- **布局**：响应式二行(桌面)→ 多行(手机)
- **按钮**：Send 按钮保持 Metro 蓝色，Upload 按钮保持 Metro 青色
- **状态提示**：上传状态、错误信息在输入框下方居中显示

#### 5. 响应式适配

**桌面(1200px+)**

- 左侧栏 280px、消息区占满剩余宽度
- Textarea 与按钮水平排列
- 消息气泡宽度 60-80% 左边界

**平板(768px-1199px)**

- 左侧栏宽度减少到 220px
- Textarea 与按钮改为竖排(flex-direction: column)
- 消息气泡宽度 70% 左边界

**手机(480px-767px)**

- 左侧栏改为顶部导航条，高度 150px
- Textarea、Send、Upload 竖排排列，宽度 100%
- 消息气泡宽度 85% 左边界

**超小屏(<480px)**

- 左侧栏高度 120px，用户名竖排显示
- 所有输入控件全宽
- 消息气泡宽度 100%，内边距减小到 10px 14px

## 推荐使用的扩展

### SubAgent：code-explorer

- **用途**：探索现有代码库结构，理解 WebSocket 消息流、命令系统交互、CSS 响应式设计的当前实现
- **预期成果**：快速定位需要修改的关键文件、理解消息格式转换的影响范围、识别样式覆盖风险