# FastAPI Chatroom

一个基于 FastAPI 的实时聊天室应用，支持 WebSocket 通信、AI 智能助手、语音通话等功能。

## 功能特性

- 实时 WebSocket 通信
- HTTPS/WSS 安全连接
- AI 智能助手集成
- 语音通话
- 图片上传
- 聊天历史记录
- 命令系统

## 环境要求

- Python 3.8+
- fastapi
- uvicorn[standard]
- cryptography (用于生成 SSL 证书)

## 安装

```bash
# 克隆项目
git clone <repository-url>
cd Chatroom

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

## SSL 证书配置

本应用使用 HTTPS 安全连接。首次运行前需要生成 SSL 证书：

### 生成证书

```bash
# 使用默认配置（IP: 81.68.133.63）
python generate_cert.py

# 指定自定义 IP
python generate_cert.py --ip 192.168.1.100

# 指定多个 IP 和域名
python generate_cert.py --ips 127.0.0.1,192.168.1.100,81.68.133.63 --domains localhost,example.com

# 查看帮助
python generate_cert.py --help
```

### 证书参数说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--ip` | 81.68.133.63 | 主要 IP 地址 |
| `--ips` | - | 多个 IP 地址（逗号分隔） |
| `--domains` | localhost | 域名列表（逗号分隔） |
| `--output` | . | 输出目录 |
| `--days` | 365 | 证书有效期（天） |
| `--key-size` | 2048 | RSA 密钥长度 |

### 浏览器信任证书

由于使用自签名证书，浏览器会显示安全警告。解决方法：

1. **临时访问**：点击 "Advanced" → "Proceed to site (unsafe)"
2. **永久信任**：将 `cert.pem` 导入系统受信任的根证书颁发机构

## 运行服务器

```bash
# 启动服务器（HTTPS 模式）
python main.py

# 或使用 uvicorn
uvicorn main:app --host 0.0.0.0 --port 8000 --ssl-keyfile key.pem --ssl-certfile cert.pem
```

服务器启动后：
- HTTPS 服务：`https://81.68.133.63:8000`
- HTTP 重定向：`http://81.68.133.63` → `https://81.68.133.63:8000`

### 端口说明

| 端口 | 用途 |
|------|------|
| 80 | HTTP 重定向服务（自动跳转到 HTTPS） |
| 8000 | HTTPS 主服务 |

> **注意**：在 Linux 上使用端口 80 需要 root 权限（`sudo python main.py`）

## 环境变量配置

创建 `.env` 文件配置 AI 功能：

```env
OPENAI_API_KEY=your-api-key
OPENAI_MODEL=gpt-3.5-turbo
OPENAI_TEMPERATURE=0.7
OPENAI_MAX_TOKENS=500
```

## API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 主页 |
| `/ws` | WebSocket | 聊天 WebSocket |
| `/ws/voip` | WebSocket | 语音通话 WebSocket |
| `/api/history` | GET | 获取聊天历史 |
| `/api/users` | GET | 获取在线用户 |
| `/upload` | POST | 上传图片 |

## 图片上传

使用 curl 上传图片：

```bash
curl -X POST https://localhost:8000/upload \
  -F "file=@/path/to/your/image.png"
```

## 项目结构

```
Chatroom/
├── main.py              # 主应用入口
├── generate_cert.py     # SSL 证书生成工具
├── requirements.txt     # 依赖列表
├── .env                 # 环境变量配置
├── static/              # 静态文件
│   ├── index.html       # 前端页面
│   ├── voip.js          # 语音通话模块
│   └── uploads/         # 上传文件目录
├── command/             # 命令系统
├── voip/                # 语音通话模块
├── db/                  # 数据库模块
└── utils/               # 工具模块
```

## 安全说明

- SSL 证书为自签名证书，仅适用于开发和测试环境
- 生产环境建议使用 Let's Encrypt 等权威证书
- 私钥文件（`key.pem`）不应提交到版本控制

## License

MIT
