# 📌 书签收藏夹

## 安装依赖

```bash
pip install flask "requests[socks]" beautifulsoup4
```

## 运行

```bash
python app.py
```

然后打开 http://localhost:5000

## 配置 SOCKS5 代理（可选）

在启动前设置环境变量：

```bash
# 无认证
export SOCKS5_PROXY="socks5://127.0.0.1:1080"

# 有认证
export SOCKS5_PROXY="socks5://user:password@127.0.0.1:1080"

python app.py
```

## 功能说明

| 功能 | 说明 |
|---|---|
| 添加书签 | 粘贴 URL → 失去焦点自动获取标题和 favicon → 回车/点击添加 |
| Dark Mode | 右上角切换，保存在 LocalStorage，下次自动恢复 |
| 标签侧边栏 | 左侧显示所有标签，点击过滤书签列表 |
| 书签列表 | 显示标题/icon/URL/标签/时间，支持编辑和删除 |
| 图标代理 | 所有第三方 favicon 通过 `/api/proxy-icon` 服务端代理，无跨域 |

## 文件结构

```
bookmark_app/
├── app.py              # Flask 后端
├── bookmarks.db        # SQLite 数据库（自动创建）
├── requirements.txt
└── templates/
    └── index.html      # 前端页面（Tailwind CDN）
```