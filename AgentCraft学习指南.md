# AgentCraft 学习指南

> 配合 [README.md](../ai-knowledge-system/README.md) 使用
> README 告诉你"这个项目是什么"，本指南告诉你"怎么学、怎么用、怎么讲"

---

## 目录

1. [本指南的定位](#1-本指南的定位)
2. [项目核心亮点](#2-项目核心亮点)
3. [前置知识清单](#3-前置知识清单)
4. [和 LangGraph 的区别与迁移能力](#4-和-langgraph-的区别与迁移能力)
5. [分阶段学习路线](#5-分阶段学习路线)
6. [核心代码逐行解读](#6-核心代码逐行解读)
7. [如何验证执行流程](#7-如何验证执行流程)
8. [面试高频问题与回答模板](#8-面试高频问题与回答模板)
9. [踩坑与经验教训](#9-踩坑与经验教训)
10. [学后收获与扩展建议](#10-学后收获与扩展建议)

---

## 1. 本指南的定位

README 已经说明了：
- 项目是什么、技术栈是什么
- 五层架构、多 Agent 协作、Tool Registry、全链路追踪的亮点描述
- 架构图（mermaid）、效果截图、快速启动方法
- 简历写法参考

**本指南聚焦 README 没有的内容：**
- 每个模块的代码怎么读、核心逻辑是什么
- 学习路线：先学什么、后学什么、每步花多久
- 面试怎么答：高频问题 + 回答模板
- 真实踩坑：项目迭代中遇到的问题和解决方案
- 迁移能力：学完后能在任何项目中从零构建 Agent

---

## 2. 项目核心亮点

> **关于本项目的学习方式**：本项目的重点不在于跑通所有功能，而在于**源码阅读和架构理解**。即使项目无法完整运行，只要你能读懂每一层的代码、理解每个设计决策的原因、讲清楚模块之间的协作关系，面试时就能展现出真正的技术深度。跑通项目只是辅助理解的手段，吃透架构才是目的。

以下是 AgentCraft 的六个核心亮点。README 中有简要描述，这里展开讲解每个亮点的设计动机、核心机制和面试要点。

---

**【亮点一】设计五层可编排 Agent 架构**

将 AI 服务拆分为 Interface、Orchestrator、Tool、Memory、Evaluation 五层，每层职责单一、可独立扩展。

```
五层职责：

  Interface Layer（接口层）
  ├── FastAPI 路由、HTTP/SSE 协议、参数校验
  ├── 文件：api/routes.py, api/agent_routes.py
  └── 职责：只做协议转换，不包含任何 AI 逻辑

  Orchestrator Layer（编排层）
  ├── Planner 规划步骤、Executor 执行、State 状态管理
  ├── 文件：agent/orchestrator.py, agent/planner.py, agent/executor.py
  └── 职责：流程编排，不直接调用 LLM，不直接操作存储

  Tool Layer（工具层）
  ├── ToolRegistry 统一注册、超时重试、执行追踪
  ├── 文件：tools/registry.py, tools/base.py, tools/*.py
  └── 职责：每个 Tool 只做一件事，不相互依赖

  Memory Layer（记忆层）
  ├── 短期记忆(AgentState) · 会话记忆(Redis) · 用户记忆(MySQL) · 知识记忆(向量库)
  ├── 文件：tools/memory_read.py, tools/memory_write.py
  └── 职责：只提供数据，不参与推理

  Evaluation Layer（评估层）
  ├── 检索充分性判断、答案质量评估
  ├── 文件：agent/planner.py (check_sufficiency)
  └── 职责：只做判断，不修改数据
```

**设计动机**：Agent 的核心流程就是"规划→执行→工具→记忆→评估"，每层对应一个独立的关注点。分层后可以独立测试、独立替换（比如换向量数据库只改 Tool 层，不影响其他层）。

**面试要点**：
- 为什么分五层？→ 因为 Agent 的核心流程恰好是五个关注点
- 层与层之间怎么通信？→ 通过接口，上层依赖下层，不能反向
- 某一层出问题怎么处理？→ 比如 LLM 超时只影响 Tool 层，通过重试策略处理

---

**【亮点二】实现多 Agent 协作机制**

Router Agent 负责任务分发，各专业 Agent 独立工作，共享状态协同。

```
Agent 类型与职责：

  Router Agent（路由 Agent）
  ├── 意图识别：LLM 优先 + 关键词 Fallback
  ├── 复杂度判断：L1 简化 / L2 标准 / L3 推理
  └── 任务分发：根据意图和复杂度路由到对应 Agent

  Knowledge QA Agent（知识问答）
  ├── L1 简化链路（80% 请求，~2-3s）：直接检索 + 生成
  ├── L2 标准链路（15% 请求，~5-8s）：改写 + 检索 + 重排 + 生成
  └── L3 推理链路（5% 请求，~10-15s）：分解 + 逐个推理 + 汇总

  ChitChat Agent（闲聊）
  └── 直接 LLM 回复，不走检索

  Admin Copilot Agent（管理副驾）
  ├── 热门问题日报/周报
  ├── 问答趋势分析
  └── 运营报告生成

  Ops Agent（运营分析）
  ├── Agent 成功率分析
  ├── 工具调用失败排行
  └── 知识库增长趋势

  Inspection Agent（知识巡检）
  ├── 重复检测、质量检测、过期检测
  └── 知识缺口发现

  Reasoning Agent（推理）
  ├── 问题分解
  ├── 逐步推理
  └── 结果汇总
```

**设计动机**：不同任务的处理逻辑差异很大（闲聊 2 秒，推理 15 秒），如果放一个 Agent 里会互相干扰。分开后每个 Agent 只做一件事，可以独立优化。

**面试要点**：
- 为什么不把所有逻辑放一个 Agent 里？→ 职责分离，降低复杂度，独立优化
- Agent 之间怎么协作？→ 通过 ToolRegistry 共享工具，通过 EventBus 事件总线追踪
- 新增 Agent 难吗？→ 不难，实现接口并注册即可

---

**【亮点三】构建统一 Tool Registry 工具体系**

将知识检索、OCR、文档摘要、对话记忆等 AI 能力抽象为标准 Tool，统一管理。

```
Tool 体系设计：

  Tool 基类（tools/base.py）
  ├── name: str              → 工具名称
  ├── input_schema           → 输入参数 Schema
  ├── output_schema          → 输出结果 Schema
  ├── metadata: ToolMetadata → 超时、重试次数、权限
  ├── validate_input()       → 输入参数校验
  └── execute()              → 执行逻辑

  ToolRegistry（tools/registry.py，单例）
  ├── register_tool(tool)    → 注册工具
  ├── invoke_tool(name, params) → 调用（带超时 + 重试 + 追踪）
  └── get_all_tools()        → 列出所有工具

  已注册工具：
  ├── knowledge_search  → 向量相似度检索（30s 超时，3 次重试）
  ├── question_rewrite  → 问题改写（LLM 语义改写 + 关键词 Fallback）
  ├── rerank            → 结果重排序
  ├── citation          → 引用来源生成
  ├── doc_summary       → 文档摘要
  ├── memory_read       → 读取会话记忆
  ├── memory_write      → 写入会话记忆
  └── ocr_extract       → OCR 文档解析
```

**设计动机**：AI 能力越来越多（检索、OCR、摘要、记忆...），如果没有统一管理，每个 Agent 自己调用会很混乱。Tool Registry 把所有能力标准化，新增工具只需要继承基类并注册。

**面试要点**：
- 为什么要抽象 Tool 层？→ 统一接口、可插拔、可监控、可复用
- 超时怎么做的？→ ThreadPoolExecutor 强制超时，防止一个卡住的请求阻塞整个 Agent
- 执行追踪有什么用？→ 管理端可以看到每个工具的调用详情（参数、结果、耗时、是否重试）

---

**【亮点四】单 Agent 端到端闭环**

以知识问答为例，单个 Agent 实现完整的端到端闭环。

```
端到端执行流程：

  用户提问
    │
    ▼
  ① 意图识别（IntentClassifier）
    ├── 知识问答 → 继续
    ├── 闲聊 → 跳转 ChitChat Agent
    └── 管理操作 → 跳转 Admin Copilot Agent
    │
    ▼
  ② 问题改写（Planner.rewrite_question）
    ├── LLM 语义改写（优先）
    └── 关键词 Fallback（降级）
    │
    ▼
  ③ 知识检索（KnowledgeSearchTool）
    ├── 向量相似度搜索（FAISS/Milvus）
    └── 返回 Top-K 结果
    │
    ▼
  ④ 充分性判断（Planner.check_sufficiency）
    ├── 充分 → 继续生成
    └── 不充分 → 追问用户补充信息 → 回到 ①
    │
    ▼
  ⑤ 答案生成（LLM.generate）
    ├── 基于检索结果生成回答
    └── 附带引用来源
    │
    ▼
  ⑥ 记忆写入（MemoryWriteTool）
    └── 保存对话上下文到 Redis
```

**设计动机**：端到端闭环意味着用户一次提问就能得到完整回答，中间的意图识别、问题改写、充分性判断都是自动的。追问机制（步骤④）确保检索结果不够时不会胡说。

**面试要点**：
- 充分性判断怎么做的？→ 覆盖率 + 置信度，不充分时追问用户
- 问题改写有什么用？→ "数据库索引" → "请解释数据库索引的定义、分类和常见应用场景"，提高检索准确率
- 全链路追踪怎么实现？→ runId/traceId/stepId 贯穿，EventBus 事件驱动

---

**【亮点五】四级记忆体系**

短期记忆、会话记忆、用户记忆、知识记忆分层管理。

```
四级记忆设计：

  Layer 1: 短期记忆（AgentState）
  ├── 内容：当前对话的临时状态
  ├── 存储：进程内存（Python dataclass）
  ├── 生命周期：单次请求
  ├── 读写速度：零网络开销
  └── 用途：步骤列表、中间结果、状态机

  Layer 2: 会话记忆（Redis）
  ├── 内容：最近 N 轮对话历史
  ├── 存储：Redis（TTL 24 小时）
  ├── 生命周期：会话级别
  ├── 读写速度：毫秒级
  ├── 核心机制：对话压缩（超长时 LLM 自动摘要）
  └── 用途：上下文连续性、多轮对话

  Layer 3: 用户记忆（MySQL）
  ├── 内容：用户偏好、历史问答、未回答问题
  ├── 存储：MySQL 持久化
  ├── 生命周期：永久
  └── 用途：个性化推荐、用户画像

  Layer 4: 知识记忆（向量库）
  ├── 内容：知识库文档的向量表示
  ├── 存储：FAISS（本地）/ Milvus（生产）
  ├── 生命周期：随知识库更新
  └── 用途：语义相似度检索

记忆注入方式：
  Agent 执行时，Planner 自动在流程开始时插入 memory_read 步骤，
  在流程结束时插入 memory_write 步骤。读取的记忆拼接到 Prompt
  的 context 中，LLM 基于上下文生成更准确的回答。
```

**设计动机**：不同层级的读写速度和生命周期不同。短期记忆是进程内的零开销，会话记忆是 Redis 的毫秒级，用户记忆是 MySQL 的持久化，知识记忆是向量库的语义检索。分层后可以按需选择。

**面试要点**：
- 为什么分四级而不是只用 Redis？→ 不同层级的读写速度和生命周期不同
- 对话压缩怎么做的？→ LLM 摘要，保留关键信息，避免 Token 超限
- 记忆怎么注入 Prompt？→ 拼接到 context 中，LLM 基于上下文生成

---

**【亮点六】全链路可观测性设计**

系统内置 runId/traceId 全链路追踪，通过 EventBus 事件驱动机制实现完整可观测性。

```
事件驱动追踪（agent/events.py）：

  事件类型：
  ├── RunStartedEvent    → Agent 开始执行
  ├── StepStartedEvent   → 步骤开始
  ├── StepCompletedEvent → 步骤完成（含耗时、输出）
  ├── StepFailedEvent    → 步骤失败（含错误信息）
  ├── RunCompletedEvent  → Agent 执行完成
  └── RunFailedEvent     → Agent 执行失败

  每个事件携带：
  ├── run_id: 唯一标识一次 Agent 执行
  ├── trace_id: 跨服务追踪（Java 后端 → Python AI 服务）
  ├── step_id: 步骤标识
  ├── step_type: 步骤类型（intent_recognition / knowledge_search / ...）
  ├── duration_ms: 执行耗时
  └── output/error: 输出或错误信息

  管理端展示（Agent 执行记录页面）：
  ├── 执行列表：所有 Agent 运行记录（runId、状态、耗时）
  ├── 步骤详情：每个步骤的输入/输出/耗时
  ├── 工具调用：每次 Tool 调用的参数和结果
  └── 时间线：从用户提问到最终回答的完整时间线
```

**设计动机**：Agent 的执行是多步骤的，如果没有追踪机制，出了问题很难定位。EventBus 事件驱动让每个步骤都有记录，管理端可以回溯整个执行过程。

**面试要点**：
- 为什么用 EventBus 而不是直接记录日志？→ 解耦事件产生者和消费者，支持多种监听方式
- runId 和 traceId 的区别？→ runId 标识一次 Agent 执行，traceId 跨服务追踪
- 管理端能看到什么？→ 每个步骤的详情、工具调用详情、全链路时间线

---

## 3. 前置知识清单

### 必须掌握（不学看不懂代码）

```
Java 基础
├── 面向对象（继承、多态、接口）
├── 集合框架（List、Map、Set）
├── 异常处理（try-catch、自定义异常）
└── Spring Boot 基础（Controller、Service、依赖注入）

Python 基础
├── 基本语法（函数、类、装饰器）
├── 类型注解（typing 模块）
├── dataclass 数据类
└── 异步编程基础（async/await 了解即可）

数据库基础
├── MySQL 基本 CRUD
├── Redis 缓存基本概念
└── 了解向量数据库是什么（不需要会用）
```

### 建议掌握（学了更好理解）

```
设计模式
├── 单例模式（ToolRegistry 用了）
├── 策略模式（检索策略、缓存策略）
├── 观察者模式（EventBus 事件总线）
├── 注册器模式（Tool 注册机制）
└── 建造者模式（AgentState 构建）

AI 基础
├── LLM 是什么（大语言模型基本概念）
├── RAG 是什么（检索增强生成）
├── Embedding 是什么（向量化）
├── Prompt Engineering 基础
└── 了解 Agent = LLM + Tools + Memory + Planning
```

### 不需要掌握（项目里用到了但可以跳过）

```
├── Milvus 向量数据库（项目默认用 FAISS，零依赖）
├── Docker 部署（学习阶段本地跑就行）
├── 前端 React（只做展示，不影响理解 Agent 架构）
└── LangChain 内部实现（项目只用了很小一部分）
```

---

## 4. 和 LangGraph 的区别与迁移能力

> **面试时的策略**：不需要主动介绍和 LangGraph 的区别，这会显得你在刻意比较。正确的做法是：先讲清楚自己项目的架构设计和亮点，如果面试官主动问到 LangGraph 或者提到"你为什么不用框架"，再展开讲解区别，突出本项目的设计思想和你自己的理解。主动讲 = 刻意，被动答 = 有深度。

### 区别

一句话：**AgentCraft 的核心设计思想和 LangGraph 相似（状态图 + 节点编排 + 条件路由），但没有用 LangGraph，全部手写实现。**

- 用 LangGraph → 你会调 API（`StateGraph`、`add_node`、`add_edge`）
- 用 AgentCraft → 你会造 API（自己实现状态机、编排器、工具注册）

**概念对照表：**

```
LangGraph 的概念              AgentCraft 的对应实现               文件位置
────────────────────────────────────────────────────────────────────────────
State Graph（状态图）      →  AgentState + StepType 状态机        agent/state.py
Node（节点）               →  Executor.execute_step()             agent/executor.py
Edge（边/条件路由）        →  Planner.plan_steps() +              agent/planner.py
                              should_terminate()
Tool Node（工具节点）      →  ToolRegistry.invoke_tool()          tools/registry.py
Memory（记忆）             →  四层记忆体系                         tools/memory_read.py
                              AgentState/Redis/MySQL/向量库        tools/memory_write.py
Checkpoint（检查点）       →  EventBus 事件追踪 + runId/traceId   agent/events.py
Multi-Agent（多智能体）    →  Router Agent + 6 个专业 Agent        workflows/*.py
Command（节点返回值）      →  step.output_data                     agent/state.py
Conditional Edge           →  Planner.should_terminate()           agent/planner.py
                              返回 (bool, reason)
```

### 迁移能力——学完后你能做什么

这是项目最核心的价值：**学完后，你可以在任何项目中从零构建适合的 Agent，而不是只会调框架。**

```
框架使用者的能力边界：
  会用 LangGraph → 只能在 LangGraph 的 API 范围内工作
  会用 AutoGen  → 只能在 AutoGen 的框架下工作
  遇到新框架    → 重新学 API

AgentCraft 学习者的能力边界：
  理解状态机原理     → 任何需要状态管理的场景都能设计
  理解任务编排原理   → 任何需要流程编排的场景都能实现
  理解工具注册原理   → 任何需要能力扩展的场景都能抽象
  理解事件驱动原理   → 任何需要追踪监控的场景都能设计
  理解记忆分层原理   → 任何需要上下文管理的场景都能分层
  遇到新框架         → 看源码就知道它怎么实现的，因为原理你都懂
```

**面试时这样说：**
> "我这个项目最大的价值不是实现了一个知识库系统，而是通过自己手写 Agent 的底层原理，获得了在任何项目中从零构建 Agent 的能力。我不依赖任何 Agent 框架，我理解框架背后的设计原理——状态机怎么管理、任务怎么编排、工具怎么注册、事件怎么驱动、记忆怎么分层。这意味着不管未来出现什么新的 Agent 框架，我都能快速看懂它的源码，因为原理是相通的。"

---

## 5. 分阶段学习路线

### 第一阶段：跑通项目（1-2 天）

```
目标：把项目跑起来，理解用户看到的是什么

步骤：
1. 按 README 的"快速启动"跑通项目
2. 用户端：问一个问题，看回答和引用来源
3. 管理端：看仪表盘、Agent 执行记录
4. 试试闲聊和知识问答的区别

验证：能用浏览器访问前端，问一个问题得到回答
```

### 第二阶段：理解数据流（3-5 天）

```
目标：一个请求从前端到后端到 AI 服务的完整链路

读代码顺序（跟着请求走）：
1. 前端发请求     → frontend/src/pages/Chat.jsx
2. Java 后端处理  → controller/ChatController.java
                   → service/ChatService.java
                   → service/AiService.java（调用 Python 服务）
3. Python AI 处理 → api/agent_routes.py
                   → agent/orchestrator.py（编排器入口）
                   → agent/planner.py（规划步骤）
                   → agent/executor.py（执行步骤）
4. 数据返回       → AI 服务 → Java 后端 → SSE 流式 → 前端渲染

验证：能在代码中找到一个请求从发起到返回的完整路径
```

### 第三阶段：吃透 Agent 核心（5-7 天）⭐ 重点

```
目标：理解 Agent 的五个核心组件

Day 1-2: Orchestrator（编排器）         → agent/orchestrator.py
  重点：create_state()、run()、重试机制、事件发布

Day 3: Planner（规划器）                → agent/planner.py
  重点：plan_steps()、recognize_intent()、rewrite_question()、check_sufficiency()

Day 4: Executor（执行器）               → agent/executor.py
  重点：execute_step()、步骤类型分发、工具调用

Day 5: ToolRegistry（工具注册器）       → tools/registry.py + tools/base.py
  重点：单例模式、注册机制、超时重试、执行追踪

Day 6-7: Memory（记忆系统）             → tools/memory_read.py + tools/memory_write.py
  重点：四层记忆、对话压缩、上下文注入

验证：能不看代码画出 Agent 执行流程图
```

### 第四阶段：理解多 Agent 协作（3-5 天）⭐ 重点

```
Day 1: Router Agent        → workflows/router_agent.py
Day 2: Knowledge QA Agent  → workflows/knowledge_qa_agent.py
Day 3: 其他 Agent          → workflows/chitchat_agent.py
                             workflows/ops_agent.py
                             workflows/inspection_agent.py
                             workflows/reasoning_agent.py
Day 4-5: EventBus          → agent/events.py

验证：能画出完整的多 Agent 协作流程图
```

### 第五阶段：理解工程实践（2-3 天）

```
Day 1: 安全与认证  → config/SecurityConfig.java, common/JwtUtil.java
Day 2: 缓存策略    → service/CacheService.java, MultiLevelCacheServiceImpl.java
Day 3: 数据库设计  → sql/init.sql

验证：能解释项目的缓存策略和安全机制
```

---

## 6. 核心代码逐行解读

### 5.1 Orchestrator — Agent 的大脑

```python
# agent/orchestrator.py 核心流程（简化版）

class Orchestrator:
    def run(self, input_text, ...):
        # ① 创建状态（包含 runId、traceId）
        state = self.create_state(input_text, ...)

        # ② 输入验证（策略引擎）
        if not self.policies.validate_input(input_text):
            return error_response

        # ③ 规划步骤（Planner 决定做什么）
        planned_steps = self.planner.plan_steps(state)

        # ④ 逐步执行（Executor 执行每一步）
        for step_name in planned_steps:
            step = state.add_step(step_type, step_name)
            self.event_bus.publish(StepStartedEvent(...))

            # ⑤ 带重试的执行
            while not step_done:
                try:
                    self.executor.execute_step(state, step)
                    step_done = True
                except Exception as e:
                    if self.policies.should_retry(retry_count, e):
                        retry_count += 1
                    else:
                        state.fail(str(e))

            # ⑥ 检查是否终止
            should_terminate, reason = self.planner.should_terminate(state)
```

**面试要点**：
- 为什么用 Orchestrator 模式？→ 解耦规划和执行
- 重试策略怎么设计的？→ policies 决定，支持配置
- 事件发布有什么用？→ 全链路追踪、监控、调试

### 5.2 Planner — Agent 的规划师

```python
# agent/planner.py 核心逻辑

class Planner:
    def plan_steps(self, state):
        intent = self.recognize_intent(state)  # 意图识别

        if intent == IntentType.CHITCHAT:
            return ["memory_read", "answer_generation", "memory_write"]
        elif intent == IntentType.KNOWLEDGE_QA:
            return ["memory_read", "question_rewrite", "knowledge_search",
                    "sufficiency_check", "answer_generation", "memory_write"]
        elif intent == IntentType.ADMIN_OPERATION:
            return ["admin_tool_call"]

    def rewrite_question(self, question, context):
        # LLM 语义改写，失败时 fallback 到简单替换
        try:
            return self._rewrite_with_llm(question, context)
        except:
            return self._rewrite_simple(question)
```

**面试要点**：
- 意图识别怎么做的？→ LLM + 关键词 Fallback
- 问题改写有什么用？→ 提高检索准确率

### 5.3 ToolRegistry — 能力管理中心

```python
# tools/registry.py（简化版）

class ToolRegistry:  # 单例模式
    def invoke_tool(self, tool_name, parameters, run_id):
        tool.validate_input(parameters)           # ① 验证参数
        tool_call_id = tracker.start_tool_call()  # ② 执行追踪

        with ThreadPoolExecutor() as executor:    # ③ 超时控制
            future = executor.submit(tool.execute, parameters)
            result = future.result(timeout=tool.metadata.timeout_ms)

        tracker.end_tool_call(tool_call_id)       # ④ 记录日志
```

**面试要点**：
- 为什么用单例？→ 全局只需要一个注册器
- 超时怎么做的？→ ThreadPoolExecutor 强制超时

### 5.4 四层记忆体系

```
Layer 1: 短期记忆（AgentState）    → 进程内存，零网络开销
Layer 2: 会话记忆（Redis）         → 毫秒级读写，24h TTL
Layer 3: 用户记忆（MySQL）         → 持久化存储，永久保留
Layer 4: 知识记忆（向量库）        → 语义检索，FAISS/Milvus
```

**面试要点**：
- 为什么分四层？→ 不同层级的读写速度和生命周期不同
- 对话压缩怎么做的？→ LLM 摘要，保留关键信息

---

## 7. 如何验证执行流程

### 方式一：看管理端 Agent 执行记录（最直观）

```
1. 启动项目
2. 用户端问一个问题，比如"什么是数据库索引"
3. 打开管理端 → Agent 执行记录页面
4. 你会看到每个步骤的详情：意图识别、问题改写、检索结果、
   充分性判断、答案生成、记忆写入，以及每个步骤的耗时
```

### 方式二：看 Python AI 服务日志（最详细）

```
启动 Python AI 服务后，问一个问题，终端会输出：

  [Orchestrator] run_id=abc123, input=什么是数据库索引
  [Planner] intent=knowledge_qa, complexity=L1
  [Executor] executing step: memory_read
  [ToolRegistry] invoking tool: memory_read, completed in 12ms
  [Executor] executing step: knowledge_search
  [VectorStore] found 5 chunks, scores=[0.92, 0.87, 0.85, 0.81, 0.78]
  [ToolRegistry] tool knowledge_search completed in 156ms
  [Executor] executing step: answer_generation
  [LLM] generating answer with context (3 chunks)
  [ToolRegistry] tool answer_generation completed in 2341ms
  [Orchestrator] run_id=abc123 completed in 2517ms
```

### 方式三：写测试验证（最严谨）

```python
# tests/test_agent_flow.py

def test_knowledge_qa_flow():
    """验证知识问答的完整执行流程"""
    from agent.orchestrator import Orchestrator
    orch = Orchestrator()
    result = orch.run(input_text="什么是数据库索引",
                      conversation_id="test-001", user_id="test-user")

    assert result["status"] == "success"
    assert "answer" in result
    assert "sources" in result          # 有引用来源
    steps = result["steps"]
    step_names = [s["step_name"] for s in steps]
    assert "knowledge_search" in step_names
    assert "answer_generation" in step_names

def test_chitchat_flow():
    """验证闲聊不走知识检索"""
    from agent.orchestrator import Orchestrator
    orch = Orchestrator()
    result = orch.run(input_text="你好", user_id="test-user")
    step_names = [s["step_name"] for s in result["steps"]]
    assert "knowledge_search" not in step_names  # 闲聊不检索
    assert "answer_generation" in step_names

def test_tool_registry():
    """验证工具注册和调用"""
    from tools.registry import tool_registry
    assert tool_registry.has_tool("knowledge_search")
    assert tool_registry.has_tool("memory_read")
    result = tool_registry.invoke_tool("knowledge_search",
                                       {"query": "数据库索引", "top_k": 3})
    assert "chunks" in result
```

### 方式四：用 curl 直接调用 API

```bash
curl -X POST http://localhost:8000/api/agent/run \
  -H "Content-Type: application/json" \
  -d '{"input": "什么是数据库索引", "conversation_id": "test-001", "user_id": "test-user"}'

# 返回包含完整的执行信息：status、answer、sources、run_id、steps、total_duration_ms
```

---

## 8. 面试高频问题与回答模板

### Q1: 介绍一下你的项目

```
AgentCraft 是一个多 Agent 协作的智能知识库系统。
和市面上用框架搭建的项目不同，我自己实现了 Agent 的底层工作原理，
包括编排器、规划器、执行器、工具注册器、事件总线、四层记忆体系等核心组件。

架构上分为三层：React 前端、Spring Boot 后端、Python AI 微服务。
AI 服务内部采用五层架构：Interface → Orchestrator → Tool → Memory → Evaluation。

系统支持多 Agent 协作，Router Agent 根据意图识别将请求分发到知识问答、
闲聊、运营分析等不同 Agent。知识问答还设计了三级链路，
80% 的简单问题走简化流程 3 秒内返回，只有 5% 的复杂问题走推理链路。
```

### Q2: Agent 的执行流程是怎样的

```
以知识问答为例：

1. 用户提问进入 Orchestrator
2. Planner 进行意图识别（LLM + 关键词 Fallback）
3. 根据意图规划步骤：记忆读取 → 问题改写 → 知识检索
   → 充分性判断 → 答案生成 → 记忆写入
4. Executor 逐步执行，每步通过 ToolRegistry 调用工具
5. 每个步骤执行时，EventBus 发布事件用于全链路追踪
6. 如果步骤失败，根据 policies 决定是否重试
7. 充分性判断：如果检索结果不够，追问用户补充信息

关键设计决策：
- 规划和执行分离 → Planner 只负责规划，Executor 只负责执行
- 工具统一注册 → 新增工具只需要继承 Tool 基类并注册
- 事件驱动 → 支持全链路追踪和监控
```

### Q3: 为什么自己实现而不直接用框架

```
核心原因：获得迁移能力。

1. 用框架你会调 API，自己实现你会造 API
   用 LangGraph 你会 StateGraph、add_node、add_edge
   自己实现你会状态机、编排器、工具注册、事件驱动
   前者只能在框架内工作，后者可以在任何项目中构建 Agent

2. 原理是相通的，框架会变但原理不变
   LangGraph 用状态图，AutoGen 用消息传递，CrewAI 用角色扮演
   但底层都是：状态管理 + 任务编排 + 工具调用 + 记忆管理
   理解了原理，任何新框架都能快速上手

3. 实际工作中经常需要定制
   框架做不了的事，你得自己做
   比如：特殊的重试策略、自定义的充分性判断、特定的缓存策略
   有了底层原理的理解，你可以根据业务需求定制任何 Agent 行为
```

### Q4: 遇到了什么困难，怎么解决的

```
1. 缓存键跨用户泄露（P0 安全问题）
   问题：缓存键没有包含 userId，导致用户 A 的缓存返回给用户 B
   解决：缓存键加入 userId，做了安全审查

2. 工具执行无限等待
   问题：Tool 调用 LLM 时没有超时，一个卡住的请求阻塞整个 Agent
   解决：引入 ThreadPoolExecutor 强制超时控制

3. 意图识别逻辑分散
   问题：意图识别散落在多个文件，逻辑不一致
   解决：抽取独立的 IntentClassifier 模块，统一 LLM + 关键词 Fallback 策略

4. 对话上下文被错误信息污染
   问题：AI 回答失败后，错误信息留在上下文中
   解决：实现对话上下文清理功能，过滤错误关键词
```

### Q5: 项目有什么亮点

```
六大亮点：

【亮点一】设计五层可编排 Agent 架构
  将 AI 服务拆分为 Interface、Orchestrator、Tool、Memory、Evaluation 五层，
  实现意图识别→问题改写→检索→充分性判断→答案生成的工作流，
  支持任务动态编排与独立扩展。

【亮点二】实现多 Agent 协作机制
  Router Agent 负责任务分发，Retrieval Agent 专精查询改写+多路召回+重排序，
  Reasoning Agent 负责归纳生成，Memory Agent 管理记忆压缩，
  多 Agent 共享状态协同工作。

【亮点三】构建统一 Tool Registry 工具体系
  将知识检索、OCR、文档摘要、对话记忆等 AI 能力抽象为标准 Tool，
  定义输入/输出 Schema、超时、重试与权限元数据，
  支持单工具执行与多工具链编排。

【亮点四】单 Agent 端到端闭环
  意图识别→追问→检索→充分性判断→生成，
  通过 runId/traceId 实现全链路追踪。

【亮点五】四级记忆体系
  短期记忆（AgentState）、会话记忆（Redis）、用户记忆（MySQL）、
  知识记忆（向量库）分层管理，支持主动读写与个性化推理。

【亮点六】全链路可观测性设计
  EventBus 事件驱动，runId/traceId 贯穿，管理端可以查看每个
  Agent 的执行步骤、耗时、工具调用详情。

核心卖点：
  不是"会用框架"，而是"会造框架"。
  学完这个项目，你获得了在任何项目中从零构建 Agent 的迁移能力。
```

### Q6: 为什么不直接用 LangGraph

```
设计思想和 LangGraph 相似——都是状态图 + 节点编排 + 条件路由。
但区别在于：

用 LangGraph：你会 StateGraph.add_node()、add_edge()
自己实现：你会状态机怎么管理、节点怎么执行、边怎么路由

LangGraph 的抽象不一定适合所有场景。比如我的三级链路（L1/L2/L3）
在 LangGraph 里要嵌套子图，自己写可以直接在 Planner 里根据复杂度切换步骤。

最重要的是：原理是相通的，框架会变但原理不变。
理解了状态机 + 节点编排 + 条件路由，任何新框架都能快速上手。
```

---

## 9. 踩坑与经验教训

以下是项目从 2026-03-08 至今 121 次提交中提炼出的真实问题。

### 安全性踩坑

```
P0 缓存键跨用户泄露 (commit a84b57b)
  问题：缓存键没有包含 userId，用户 A 的缓存返回给用户 B
  教训：Vibe Coding 生成的缓存代码默认不考虑多租户

P0 URL 判断正则误判 (commit a84b57b)
  问题：正则不够严格，本地文件路径被误判为 URL
  教训：AI 生成的正则往往"够用就行"，边界情况需要人工审查

密码明文存储 (commit c2266d6)
  问题：初期密码明文存储在数据库
  教训：安全功能不能"以后再加"，必须从第一天就做
```

### AI 服务质量踩坑

```
闲聊返回文档引用 (commit 0840d9e)
  问题：用户问"你好"，系统返回了知识库文档引用
  教训：意图识别是 AI 系统最关键的一环，分类不准 = 用户体验灾难

AI 异常信息暴露给用户 (commit 1431182)
  问题：Python 服务异常时，技术细节直接返回给前端
  教训：AI 生成的错误处理默认是"抛出异常"，你需要要求"友好降级"

对话上下文被错误信息污染 (commit 6eda749)
  问题：AI 回答失败后，错误信息留在上下文中
  教训：对话状态管理比想象中复杂，错误恢复机制必须提前设计
```

### 架构演进踩坑

```
意图识别逻辑分散 (commit 44a1b8e)
  问题：意图识别散落在多个文件，逻辑不一致
  教训：Vibe Coding 容易把同一逻辑复制到多个文件，发现重复时必须立即抽取

工具执行无限等待 (commit 9a977a5)
  问题：Tool 调用 LLM 时没有超时，一个卡住的请求阻塞整个 Agent
  教训：AI 系统中"等待"是最危险的，所有外部调用必须有超时

步骤执行失败无重试 (commit 7d56878)
  问题：Agent 步骤执行失败后直接终止
  教训：AI 调用天然不稳定（网络、限流、模型抖动），重试是必须的
```

### Vibe Coding 的 8 条铁律

| # | 铁律 |
|---|------|
| 1 | 安全审查必须人工做 — AI 不会主动考虑缓存键隔离、SQL 注入 |
| 2 | 异常处理必须明确要求 — AI 默认"抛出异常"，你需要"友好降级" |
| 3 | 发现重复立即抽取 — AI 喜欢复制代码到多个文件 |
| 4 | 所有外部调用必须有超时 — LLM 调用天然不稳定 |
| 5 | 记忆系统提前规划 — Agent 记忆比你想象的复杂 |
| 6 | 外部依赖必须有降级 — Milvus 挂了不能整个系统不可用 |
| 7 | 配置文件不能硬编码 — 密钥用环境变量 |
| 8 | 意图识别是命脉 — 分类不准 = 用户体验灾难 |

---

## 10. 学后收获与扩展建议

### 技术能力收获

```
✅ 理解 Agent 底层原理 — 不是"会用框架"，而是"会造框架"
✅ 掌握设计模式实战 — 单例、策略、观察者、注册器、建造者
✅ 理解 RAG 完整流程 — 意图识别→改写→检索→重排序→生成
✅ 掌握全栈开发能力 — React + Spring Boot + FastAPI
✅ 理解工程最佳实践 — 安全、缓存、监控、部署
```

### 面试能力收获

```
✅ 能讲清楚项目架构 — 三层架构、五层 Agent、多 Agent 协作
✅ 能回答深挖问题 — 设计决策、踩坑经历、优化方案
✅ 能展示迁移能力 — "我在任何项目中都能从零构建 Agent"
```

### 扩展学习建议

```
1. 对比学习其他 Agent 框架
   - LangChain Agent / AutoGen / CrewAI
   - 有了 AgentCraft 的基础，学这些框架会非常快

2. 阅读 Dify 源码
   - Dify 是生产级的 Agent 平台
   - 对比 Dify 的实现和 AgentCraft 的实现

3. 阅读 Claude Code 源码
   - 本项目部分设计借鉴了 Claude Code 的实现方式
   - 重点阅读：
     ├── 工具注册与调用机制 → 对比 AgentCraft 的 ToolRegistry
     ├── 执行状态管理 → 对比 AgentCraft 的 AgentState
     ├── 事件驱动架构 → 对比 AgentCraft 的 EventBus
     ├── 错误处理与重试策略 → 对比 AgentCraft 的 policies
     └── 上下文管理 → 对比 AgentCraft 的四级记忆体系
   - Claude Code 的源码质量很高，是学习 Agent 工程化的优秀参考

4. 给开源项目贡献 PR
   - Dify、Sentinel、dubbo 等项目都有 good first issues

5. 自己动手扩展功能
   - 新增一个 Agent 类型（比如代码生成 Agent）
   - 新增一个 Tool（比如网页搜索工具）
```

### 推荐阅读

```
书籍：
├──《Designing Data-Intensive Applications》— 数据密集型系统设计
├──《Designing Machine Learning Systems》— ML 系统设计
└──《Building LLM Powered Applications》— 构建 LLM 应用

论文：
├── ReAct: Synergizing Reasoning and Acting in Language Models
├── Toolformer: Language Models Can Teach Themselves to Use Tools
└── Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks

博客：
├── Lilian Weng 的 Agent 博客 — 理论基础
└── LangChain 官方博客 — 行业实践
```

---

> **文档版本**：v2.1
> **更新日期**：2026-05-16
> **配合使用**：README.md（项目说明） + 本指南（学习路线）
