# Store POS 🧾 v2.6.2

店家端收费系统 — 一个小型零售/POS 收银管理 Web 应用。

适用于咖啡馆、奶茶店、小餐馆等场景，在手机/平板上即可完成收银、商品管理、订单查询和营收统计。

> **最新**: v2.6.2 — 优惠券自定义商品 + 双模式折扣 + 选项组多选 + 订单完成交付

## ✨ 功能一览

| 模块 | 功能 |
|------|------|
| 🧾 **收银台** | 搜索商品 → 选择选项（**多选/单选**）→ 加入购物车 → **选择支付方式**（纸币/微信/支付宝）→ **扫码/找零** → 收款出单 → **打印凭条**，自动扣减库存 |
| 📦 **商品管理** | 增删改商品（名称、价格、分类、库存、**双模式折扣**）；配置商品选项组（如尺寸、甜度、小料），**支持多选**（如同时加珍珠+椰果） |
| 📋 **订单管理** | 历史订单列表、**完整状态流转**（待支付→已支付→已完成）、详情查看、**编辑备注**、**删除订单**、退款/完成交付 |
| 📊 **今日统计** | 今日营收、**支付方式分布**、订单数、售出件数、热销商品排行 |
| 📈 **每周收益明细** | 每日营收柱状图、时段分布图、每日明细表、订单时间线、**图表导出 PNG** |

## 🚀 快速开始

### 环境要求

- Python 3.10+
- pip

### 安装与运行

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动服务
cd store-pos
python3 app.py
```

服务默认运行在 **http://127.0.0.1:5000**。

### 生成示例数据

启动后访问 `/api/seed` 即可生成本周的模拟商品和订单数据：

```bash
curl http://127.0.0.1:5000/api/seed
```

## 📦 部署到 Vercel

```bash
# 安装 Vercel CLI
npm i -g vercel

# 部署
vercel deploy
```

或直接使用已配置的 `vercel.json` + `api/index.py` 进行一键部署。

## 📁 项目结构

```
store-pos/
├── app.py              # Flask 应用入口（路由 + API）
├── models.py           # 数据库模型与初始化
├── requirements.txt    # Python 依赖清单
├── vercel.json         # Vercel 部署配置
├── api/
│   └── index.py        # Vercel serverless 入口
├── store.db            # SQLite 数据库（自动生成，已 gitignore）
├── .gitignore
├── LICENSE             # MIT 许可证
├── README.md
├── static/
│   ├── style.css       # 全局样式
│   ├── alipay-logo.png # 支付宝 Logo
│   ├── wechat-logo.png # 微信 Logo
│   └── qr/             # 收款二维码（需替换为实际收款码）
└── templates/
    ├── index.html      # 收银台主页
    ├── products.html   # 商品管理
    ├── orders.html     # 订单管理
    ├── stats.html      # 今日统计
    └── weekly.html     # 每周收益明细
```

## 🛠 API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/products` | 商品列表（支持 `?search=`） |
| POST | `/api/products` | 新增商品 |
| PUT | `/api/products/<id>` | 更新商品 |
| DELETE | `/api/products/<id>` | 删除商品 |
| GET | `/api/products/<id>/options` | 商品选项（含 `multi_select`） |
| POST | `/api/products/<id>/options` | 保存商品选项 |
| POST | `/api/orders` | 创建订单（未支付，暂不扣库存） |
| GET | `/api/orders` | 订单列表（支持 `?page=`、`?status=`） |
| GET | `/api/orders/<id>` | 订单详情（含商品明细和支付信息） |
| POST | `/api/orders/<id>/pay` | 💳 支付订单（选择方式、实收金额→找零） |
| POST | `/api/orders/<id>/complete` | ✅ 完成交付 |
| POST | `/api/orders/<id>/cancel` | 取消未支付订单 |
| POST | `/api/orders/<id>/refund` | 退款 |
| GET | `/api/stats/today` | 今日统计 |
| GET | `/api/stats/weekly` | 本周统计（每日+时段+订单明细） |
| GET | `/api/export/products.csv` | 📥 导出商品 CSV |
| GET | `/api/export/orders.csv` | 📥 导出全部订单 CSV（含明细） |
| GET | `/api/export/weekly.csv` | 📥 导出本周数据 CSV |
| GET | `/api/stats/weekly/chart.png` | 🖼️ 导出本周营收柱状图 PNG |
| GET | `/api/seed` | 生成示例数据 |

## 📱 技术栈

- **后端**: Python / Flask
- **数据库**: SQLite
- **前端**: 原生 HTML + CSS + JavaScript
- **部署**: Vercel Serverless Functions
- **UI 设计**: 移动端优先，底部 Tab 导航，毛玻璃效果，深紫渐变主题

## 📄 许可证

MIT License — 自由使用、修改、分发。
