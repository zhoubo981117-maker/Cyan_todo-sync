# Xiaomi MiMo Orbit 投稿材料

> 用途：用于 Xiaomi MiMo Orbit 百万亿 Token 创造者激励计划申请表。官方评估重点包括：AI 工具、底层模型、项目描述、证明材料。以下内容按表单可复制格式整理。

## 申请项目名称

Cyan Todo Sync

## 项目一句话简介

一个面向个人和小团队的自托管双端同步代办系统，支持账号私有、多设备同步、子任务、重复任务、提醒、日历视图、番茄钟、密码重置和自动部署更新。

## 项目地址

- GitHub 仓库：https://github.com/zhoubo981117-maker/Cyan_todo-sync
- 在线演示：https://www.cyancola.xin/
- 当前部署方式：阿里云 ECS + Ubuntu + systemd + Caddy HTTPS + GitHub 自动同步

## 使用的 AI 工具

- OpenAI Codex：用于需求拆解、代码实现、调试、服务器部署指导、自动化发布流程梳理。
- GitHub CLI / GitHub API：用于代码提交、远端同步和发布验证。
- 浏览器与命令行验证：用于检查前端页面、接口健康状态、systemd 服务状态和自动同步日志。

## 使用的底层模型

- 主要使用 Codex 编程助手完成项目迭代。
- 项目后续计划接入 Xiaomi MiMo API，用于自然语言创建任务、任务拆解、优先级建议、日程总结和番茄钟复盘。

## 项目背景

我希望做一个自己可控的代办事项系统，核心诉求是 Android 手机和 Windows 电脑都能使用同一个账号查看同一份清单，同时支持公网访问和离线优先的 App 方案。

现阶段先完成了 Web/PWA 与服务端能力，用于验证产品流程和同步逻辑；后续会继续推进 Flutter Android + Windows 客户端打包。

## 已完成功能

- 账号系统：注册、登录、账号私有隔离。
- 密码安全：修改密码、登录态下重置密码、忘记密码验证码/重置链接流程。
- 代办任务：新增、完成、删除、优先级、备注、完成时间。
- 子任务：主任务可展开子任务，子任务可单独完成；连续勾选子任务时抽屉不会关闭。
- 重复任务：支持每天、每周、每月重复；完成一个重复任务后自动生成下一期任务。
- 提醒通知：支持不提醒、到点提醒、提前 10 分钟、提前 30 分钟、提前 1 小时。
- 日历视图：按完成日期展示当月任务分布。
- 番茄钟：任务栏上方横条展示，支持专注/休息时间配置。
- 部署能力：公网 HTTPS 访问，Caddy 反代，systemd 开机自启。
- 自动同步部署：服务器定时检查 GitHub main 分支，发现新提交后自动拉取并重启服务。
- 版本可验证：`/api/version` 返回当前运行 Git 提交，页面显示短提交版本号，方便判断服务器是否是最新版本。
- 缓存更新：Service Worker 根据服务器 Git 版本生成缓存名，减少前端更新后仍显示旧页面的问题。

## 技术架构

- 前端：原生 HTML/CSS/JavaScript，无构建步骤，方便小服务器部署和快速迭代。
- 后端：Python 标准库 HTTP Server + SQLite。
- 数据库：SQLite，存储用户、任务、子任务、密码重置 token。
- 部署：Ubuntu + systemd + Caddy。
- 自动更新：systemd timer 每分钟触发 `deploy/update-from-github.sh`，执行 `git fetch`、`git merge --ff-only`、重启服务。
- 未来客户端：Flutter，目标 Android APK + Windows 桌面程序，离线优先后再同步服务端。

## AI 在项目中的具体作用

AI 不是只写了一段示例代码，而是参与了完整产品迭代：

1. 需求拆解：从“双端可用代办清单”拆解到账户、同步、任务模型、部署、域名、HTTPS、自动更新。
2. 架构选择：先用轻量自托管 Web/PWA 快速验证，再保留 Flutter 客户端路径。
3. 编码实现：实现 Python 后端、SQLite 数据模型、前端交互、PWA 缓存、密码重置、提醒、日历、番茄钟等功能。
4. 部署排障：处理阿里云 ECS、安全组、Caddy、HTTPS、systemd、GitHub 自动同步和浏览器缓存问题。
5. 发布流程：形成“每次迭代提交 Commit、推送 GitHub、服务器自动同步”的开发闭环。

## 当前项目亮点

- 面向真实个人使用场景，不是一次性 Demo。
- 已经公网部署，可直接访问验证。
- 每个账号数据私有隔离，适合个人长期使用。
- 迭代流程完整：需求、开发、提交、部署、验证都有闭环。
- 自动更新和版本可观测性已经实现，能判断线上服务器是否跑最新代码。
- 后续接入 MiMo 后有明确 AI 场景，不是为了活动临时堆概念。

## 后续计划

- 接入 Xiaomi MiMo API，实现自然语言创建任务，例如“下周一提醒我准备考试材料”自动解析为任务、日期、提醒。
- 接入 MiMo 做任务拆解，例如输入“准备面试”，自动生成子任务清单。
- 用 MiMo 根据截止时间、任务内容和历史完成情况建议优先级。
- 做每日/每周总结，自动生成已完成事项、延期事项和明日建议。
- 完成 Flutter Android APK 和 Windows 桌面端打包。
- 加强离线优先同步冲突处理。

## 证明材料

- GitHub 仓库提交记录：https://github.com/zhoubo981117-maker/Cyan_todo-sync/commits/main
- 在线演示：https://www.cyancola.xin/
- 版本接口：https://www.cyancola.xin/api/version
- 自动部署脚本：`deploy/update-from-github.sh`
- systemd timer 配置：`deploy/todo-sync-update.timer`
- 服务端入口：`server.py`
- 前端入口：`web/index.html`、`web/app.js`、`web/styles.css`

## 表单用精简版项目描述

Cyan Todo Sync 是我用 AI 辅助从 0 到 1 开发的自托管双端同步代办系统，目标是让 Android 和 Windows 使用同一个账号管理同一份任务清单。项目已公网部署，支持注册登录、账号私有隔离、代办、子任务、优先级、完成时间、重复任务、提醒通知、日历视图、番茄钟、忘记密码、HTTPS 访问、systemd 开机自启、GitHub 自动同步部署和线上版本验证。

项目开发过程中，AI 参与了需求拆解、架构设计、代码实现、部署排障和迭代发布。后续计划接入 Xiaomi MiMo API，实现自然语言创建任务、自动拆解子任务、优先级建议、每日总结和番茄钟复盘，让这个项目从传统代办工具升级为 AI 工作助手。

## 表单用证明材料链接

```text
GitHub: https://github.com/zhoubo981117-maker/Cyan_todo-sync
Demo: https://www.cyancola.xin/
Version API: https://www.cyancola.xin/api/version
Commits: https://github.com/zhoubo981117-maker/Cyan_todo-sync/commits/main
```
