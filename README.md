# Store POS 🧾

店家端收费系统 — 一个小型零售/POS 收银管理 Web 应用。

适用于咖啡馆、奶茶店、小餐馆等场景，在手机/平板上即可完成收银、商品管理、订单查询和营收统计。

## ✨ 功能一览

| 模块 | 功能 |
|------|------|
| 🧾 **收银台** | 搜索商品 → 选择选项（尺寸/甜度等）→ 加入购物车 → **选择支付方式**（纸币/微信/支付宝）→ **扫码/找零** → 收款出单 → **打印凭条**，自动扣减库存 |
| 📦 **商品管理** | 增删改商品（名称、价格、分类、库存、**折扣**）；配置商品选项组（如尺寸、甜度）每个选项可加价 |
| 📋 **订单管理** | 历史订单列表、**支付状态**（未支付/已支付/已退款）、详情查看、**编辑备注**、**删除订单**、退款（自动恢复库存） |
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

### Make 常用命令

项目提供了 `Makefile`，方便日常操作：

```bash
make run       # 启动服务
make seed     # 生成示例数据
make export   # 导出 CSV 到 exports/ 目录
make clean    # 清理缓存和数据库（⚠️ 删除所有数据）
make archive  # 创建发布包 store-pos-v1.0.0.tar.gz
```

## 📁 项目结构

```
store-pos/
├── app.py              # Flask 应用入口（路由 + API）
├── models.py           # 数据库模型与初始化
├── requirements.txt    # Python 依赖清单
├── pyproject.toml      # Python 项目元数据
├── Makefile            # 常用命令（run/seed/export/archive）
├── store.db            # SQLite 数据库（自动生成，已 gitignore）
├── .gitignore
├── LICENSE             # MIT 许可证
├── README.md
├── static/
│   └── style.css       # 全局样式
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
| POST | `/api/orders` | 创建订单（未支付，暂不扣库存） |
| GET | `/api/orders` | 订单列表（支持 `?page=`、`?filter=`） |
| GET | `/api/orders/<id>` | 订单详情（含商品明细和支付信息） |
| POST | `/api/orders/<id>/pay` | 💳 支付订单（选择方式、实收金额→找零） |
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
- **UI 设计**: 移动端优先，底部 Tab 导航，触控友好

## 📄 许可证

MIT License — 自由使用、修改、分发。

## 📦 下载发布包

从 GitHub Releases 下载最新版：

```bash
# 或自行打包
make archive
```
  - Thu Jun 11 18:40:49 LCL 2026
