# 奇奇回收

## 项目简介

奇奇回收是一套面向报废车回收行业的全流程解决方案，采用 **Python + Django** 构建后端服务，**微信小程序（JavaScript）** 开发前端交互端，覆盖报废车回收全业务场景，核心解决报废车回收流程数字化、员工核验高效化、用户积分体系化等问题，支持新闻资讯发布、多证件 OCR 识别核验、VIN 码车型查询、积分商城兑换等核心能力。

---
- legacy 分支：承载 AI 新闻系统。
- master 分支：承载 奇奇回收系统。

## 功能特性

### 核心业务模块

- **报废车回收模块**：支持报废车信息提交、回收预约、回收进度跟踪、回收单管理等全流程操作；
- **新闻模块**：后台发布行业政策、回收资讯、公司动态，小程序端分类展示、关键字检索；
- **员工通道模块**：
  - 多证件 OCR 识别：自动识别身份证、营业执照、行驶证关键信息；
  - 信息匹配核验：对比三证信息一致性，自动汇总核验结果；
  - VIN 码解析：通过车辆 VIN 码查询车型、厂商、排量等车辆基础信息；
- **积分体系模块**：用户回收报废车获取积分、积分有效期管理、积分明细查询、积分增减记录；
- **积分商城模块**：积分商品上架 / 下架、商品分类、用户积分兑换、兑换订单管理；
- **用户模块**：微信小程序授权登录、用户信息管理、角色区分（普通用户 / 员工 / 管理员）、权限控制。

### 技术特性

- **后端**：Django REST Framework 构建 RESTful API，支持接口权限校验、数据分页 / 过滤；
- **前端**：微信小程序原生开发，适配多设备尺寸，交互轻量化；
- **数据安全**：OCR 识别数据加密存储，用户敏感信息脱敏处理；
- **扩展性**：模块化设计，支持新增回收品类、扩展积分权益类型。

---

## 环境要求

### 后端（Python + Django）

- **Python**：3.9+（推荐 3.9~3.11）；
- **Django**：4.2+、Django REST Framework 3.14+；
- **依赖库**：
  - OCR 相关：百度 / 阿里云 OCR SDK（如 `aip` / `aliyun-python-sdk-core`）本文使用的是华为云接口；
  - 数据处理：`pandas`（信息汇总）、`requests`（VIN 码接口调用）；
  - 数据库：`mysqlclient`（MySQL）/ `psycopg2`（PostgreSQL）；
  - 其他：`PyJWT`（token 校验）、`django-cors-headers`（跨域）、`python-dotenv`（环境变量）；
- **数据库**：MySQL 8.0+ / PostgreSQL 12+；
- **操作系统**：Windows/Linux/macOS（生产环境推荐 Linux）。

### 微信小程序端

- **微信开发者工具**：最新稳定版；
- **小程序 AppID**：需配置业务域名、接口域名；
- **Node.js**：14+（可选，用于小程序依赖管理 / 构建）；
- **基础库版本**：微信小程序基础库 2.30.0+。

## 安装步骤

### 1. 后端部署（Django）

克隆仓库：

```bash
git clone https://github.com/735166094/recyle.git
```

## 安装依赖

```bash
# 创建虚拟环境（推荐）
python -m venv venv

# 激活虚拟环境
# Windows
venv\Scripts\activate

# 安装依赖
cd rec/Admin/
pip install -r requirements.txt

```

### 配置环境变量

在 `/rec/Admin/recycle_admin/` 目录下创建 `setting` 文件，配置如下核心参数：

```bash
# 数据库配置
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=你的数据库密码
DB_NAME=qihi_recycle

# OCR配置（以百度OCR为例）
BAIDU_OCR_APP_ID=你的百度OCR AppID
BAIDU_OCR_API_KEY=你的百度OCR API Key
BAIDU_OCR_SECRET_KEY=你的百度OCR Secret Key

# VIN码查询接口配置
VIN_QUERY_API_URL=你的VIN码查询接口地址
VIN_QUERY_API_KEY=你的接口密钥

# Django配置
SECRET_KEY=你的Django Secret Key
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,你的域名

# 小程序配置
MINI_APP_ID=你的小程序AppID
MINI_APP_SECRET=你的小程序AppSecret
```

### 数据库迁移 & 启动服务

```bash
# 数据库迁移
python manage.py makemigrations
python manage.py migrate

# 创建超级管理员（后台管理）
python manage.py createsuperuser

# 启动开发服务器
python manage.py runserver 0.0.0.0:8000

# 或者使用 waitress 生产级启动
waitress-serve --host=127.0.0.1 --port=8000 recycle_admin.wsgi:application
```

## 2. 微信小程序端部署

### 导入项目

- 打开微信开发者工具，选择「导入项目」；
- 项目目录选择 `奇奇回收/miniprogram`；
- 填写小程序 AppID（测试可使用「测试号」）；
- 勾选「不校验合法域名、web-view（业务域名）、TLS 版本以及 HTTPS 证书」（生产环境需配置合法域名）。

### 配置接口地址

修改 `rec/wxapp/utils/request.js` 中的基础接口地址：

```bash
// 替换为你的后端实际地址
const baseUrl = "http://127.0.0.1:8000/api";
```

### 调试运行

点击微信开发者工具「编译」按钮，即可在模拟器中调试小程序功能。

---

## 使用方法

### 后端接口调试

- **后台管理系统**：访问 `http://你的后端地址/admin`，使用超级管理员账号登录，可管理用户、回收单、新闻、积分商品等；
- **API 文档**：若集成 `drf-yasg` / `swagger`，访问 `http://你的后端地址/swagger/` 查看接口文档（需提前在 Django 配置中开启）。

### 核心功能使用示例

#### 1. 员工通道 - 证件 OCR 识别

```bash
# 后端核心逻辑示例（参考）
from aip import AipOcr

def ocr_id_card(image_bytes):
    """身份证OCR识别"""
    client = AipOcr(APP_ID, API_KEY, SECRET_KEY)
    res = client.idcard(image_bytes, 'front')  # front-正面，back-背面
    return res.get('words_result', {})

def verify_certificates(id_card_info, license_info, driving_license_info):
    """三证信息匹配核验"""
    # 核心匹配逻辑（如姓名、企业名称、车牌等）
    is_match = True
    if id_card_info.get('姓名') != driving_license_info.get('姓名'):
        is_match = False
    # ... 其他核验规则
    return is_match
```

### 2. VIN 码查询车型

```bash
// 小程序端调用示例
wx.request({
  url: `${baseUrl}/vin/query`,
  method: 'POST',
  data: {
    vin_code: '车辆VIN码'
  },
  success: (res) => {
    if (res.data.code === 200) {
      console.log('车型信息：', res.data.data);
      // 渲染到页面
    }
  }
});
```


## 项目目录结构

### 后端（backend/）

```bash
backend/
├── qihi_recycle/          # Django项目主目录
│   ├── __init__.py
│   ├── settings.py        # 项目配置
│   ├── urls.py            # 总路由
│   ├── asgi.py            # ASGI配置
│   └── wsgi.py            # WSGI配置
├── apps/                  # 业务应用模块
│   ├── user/              # 用户模块（登录、权限、信息）
│   ├── recycle/           # 报废车回收模块
│   ├── news/              # 新闻模块
│   ├── employee/          # 员工通道（OCR、VIN查询）
│   ├── points/            # 积分模块
│   └── mall/              # 积分商城模块
├── utils/                 # 通用工具（OCR、请求、加密）
├── migrations/            # 数据库迁移文件
├── requirements.txt       # 后端依赖清单
├── .env                   # 环境变量配置（不提交到仓库）
└── manage.py              # Django管理脚本
```

### 微信小程序端（miniprogram/）

```bash
miniprogram/
├── pages/                 # 页面目录
│   ├── index/             # 首页
│   ├── recycle/           # 报废车回收页
│   ├── news/              # 新闻页
│   ├── employee/          # 员工通道页
│   ├── points/            # 积分页
│   ├── mall/              # 积分商城页
│   └── user/              # 个人中心页
├── components/            # 自定义组件（OCR上传、VIN输入等）
├── utils/                 # 工具类（请求、日期、验证）
│   └── request.js         # 接口请求封装
├── app.js                 # 小程序入口
├── app.json               # 全局配置
├── app.wxss               # 全局样式
└── project.config.json    # 小程序项目配置
```


### 项目演示

PC端页面示例：

<img width="1910" height="961" alt="image" src="https://github.com/user-attachments/assets/ba973ca4-11fa-4b6b-b820-323fc2a94516" />
<img width="1920" height="959" alt="image" src="https://github.com/user-attachments/assets/4de5878f-bc18-4114-b805-4ba590383f50" />
<img width="1920" height="959" alt="image" src="https://github.com/user-attachments/assets/c835a9c3-8c7d-42b9-af77-b9d8141dc412" />
<img width="1916" height="955" alt="image" src="https://github.com/user-attachments/assets/442dd405-1957-4932-b252-f347e4192417" />


微信小程序端(积分和商城功能在代码中已完成但实际未上线)：

<img width="414" height="780" alt="image" src="https://github.com/user-attachments/assets/221995b6-1dcb-4ba0-949a-365769a7db55" />
<img width="414" height="780" alt="image" src="https://github.com/user-attachments/assets/b221edee-d954-4ad7-8078-7bbbc5769746" />
