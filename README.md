<div align="center">

<img width="100%" src="https://capsule-render.vercel.app/api?type=waving&color=0:FF512F,45:DD2476,100:7F00FF&height=230&section=header&text=FANQIE%20PUBLISH%20SYNC%20ASSISTANT&fontSize=46&fontColor=ffffff&animation=fadeIn&fontAlignY=38&desc=Fanqie%20Publishing%20%26%20Syncing%20Workflow%20Assistant&descAlignY=58&descSize=18" alt="FANQIE PUBLISH SYNC ASSISTANT" />

<img src="https://readme-typing-svg.demolab.com?font=JetBrains+Mono&weight=700&size=24&duration=2600&pause=700&color=FF6B6B&center=true&vCenter=true&width=900&lines=Fanqie+Publishing+%E2%9C%A6+Fanqie+Syncing;Novel+Processing+%E2%9C%A6+Web+Chapter+Crawler;A+local+desktop+workflow+assistant+for+authors" alt="typing svg" />

<br />
<br />

<img src="https://img.shields.io/badge/Python-Desktop%20App-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
<img src="https://img.shields.io/badge/pywebview-Local%20UI-111827?style=for-the-badge&logo=windowsterminal&logoColor=white" alt="pywebview" />
<img src="https://img.shields.io/badge/Playwright-Browser%20Automation-2EAD33?style=for-the-badge&logo=playwright&logoColor=white" alt="Playwright" />
<img src="https://img.shields.io/badge/FANQIE-Publish%20%26%20Sync-ff4d4f?style=for-the-badge&logo=bookstack&logoColor=white" alt="Fanqie Publish Sync Assistant" />

</div>

---

# Fanqie Publish Sync Assistant  
## 番茄发布同步助手

**Fanqie Publish Sync Assistant** 是一个面向番茄小说作者的本地发布与同步工作台。

> 推荐项目文件夹名：`Fanqie-Publish-Sync-Assistant`。如果需要把项目目录链接到小说资料目录，可以运行根目录下的 `创建文件链接.bat`。


对连载作者而言，真正的麻烦不是偶尔发布一章，而是长期维护作品时，发布和同步极易出错：本地改了哪里、后台是否一致、批量发布有没有漏章错序……人工一章章核对，费时且不稳。

本项目聚焦两个核心场景：

- **番茄发布**：在本地浏览器环境运行。作者登录番茄后台后，选择作品、章节范围和稿件路径，工具按流程进入后台完成发布，并持续输出状态反馈。批量发布时，无需一直盯着后台猜测进度。
- **番茄同步**：读取后台章节信息，与本地稿件逐章校准对比，标记一致、差异或待更新内容。让本地与后台之间，不再仅靠人工记忆，而是有一套可检查、可追踪的流程。

项目采用“左侧配置参数，右侧控制台输出”的界面，操作直观，适合长期使用。

此外还提供辅助能力：

- **小说处理**：文本清理、TXT 分割、批量整理。
- **网页抓取**：辅助章节内容获取与资料收集。

这些能力不是主线，它们主要服务于发布与同步流程。

整体定位上，`Fanqie Publish Sync Assistant` 不是写作软件，也不是爬虫工具。它真正想做的是：把番茄后台那些重复、繁琐、易错的发布与同步操作，变成一套本地可执行、可观察、可追踪的工作流。

让作者把精力留给故事，把机械工作交给工具。

---

## 功能页面

```txt
FANQIE PUBLISH SYNC ASSISTANT | 番茄发布
FANQIE PUBLISH SYNC ASSISTANT | 番茄同步
FANQIE PUBLISH SYNC ASSISTANT | 小说处理
FANQIE PUBLISH SYNC ASSISTANT | 网页抓取
```

---

## 启动方式

```bash
python main.py
```

首次使用前请先安装依赖：

```bash
pip install -r requirements.txt
```

---

## 使用提醒

这是非官方本地辅助工具。  
请正常使用，遵守平台规则。  
工具只是工具，真正重要的还是稳定更新和认真写故事。

---

## 致谢

感谢 [番茄小说全自动发文机器人](https://github.com/hchcx/fanqie_auto_publish) 的界面设计参考。

<div align="center">

<img width="100%" src="https://capsule-render.vercel.app/api?type=waving&color=0:7F00FF,45:DD2476,100:FF512F&height=120&section=footer" alt="footer" />

</div>
