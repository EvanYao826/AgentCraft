# AI Knowledge System — RAG vs Agent 架构对比分析

> 本文档对比本项目从 **RAG 知识库问答系统** 演进到 **多 Agent 协作系统** 前后的架构差异、优缺点和面试要点。

---

## 一、架构总览对比

### 1.1 原始 RAG 架构（单链路）

```
用户提问
  │
  ▼
Embedding（DashScope API / HuggingFace）
  │
  ▼
FAISS 向量检索（Top-K）
  │
  ▼
LLM 生成回答（Tongyi / DashScope）
  │
  ▼
组装引用来源 → 返回前端
```

**特点**：一条直线走到底，没有分支、没有判断、没有多轮决策。

### 1.2 当前 Agent 架构（多层协作）

```
用户提问
  │
  ▼
┌─────────────────────────────────┐
│        Router Agent             │
│  关键词权重分类 → 任务分发       │
└──────┬──────┬──────┬────────────┘
       │      │      │
       ▼      ▼      ▼
   闲聊    知识问答   管理/巡检
   Agent    Agent     Agent
       │      │
       ▼      ▼
   规则匹配  ┌──────────────────┐
   (<1ms)   │  VectorStore      │
            │  .search()        │
            └────────┬─────────┘
                     ▼
            ┌──────────────────┐
            │  LLM 生成回答     │
            │  get_answer()     │
            └────────┬─────────┘
                     ▼
              组装引用 → 返回
```

**特点**：先判断意图，再走不同链路，每条链路可以独立优化。

---

## 二、核心组件对比

| 维度 | RAG 版本 | Agent 版本 |
|------|---------|-----------|
| **入口** | 单一 API `/chat/messages` | Router Agent 统一路由 |
| **意图识别** | 无 | `classify_task()` 关键词权重分类 |
| **闲聊处理** | 也走检索+LLM（浪费资源） | ChitChatAgent 规则匹配，<1ms 响应 |
| **知识问答** | 直接检索 → LLM | KnowledgeQAAgent（优化后也走直接检索） |
| **检索链路** | FAISS search → LLM | 可选 Query Rewrite / Rerank（当前关闭） |
| **管理能力** | 无 | AdminCopilotAgent + OpsAgent |
| **知识巡检** | 无 | InspectionAgent |
| **编排层** | 无 | Orchestrator（Plan → Execute → Observe） |
| **事件系统** | 无 | EventBus 发布/订阅 |
| **工具抽象** | 硬编码在业务逻辑中 | Tool Registry（knowledge_search, rerank 等） |
| **状态管理** | 无 | AgentState（run_id, trace_id, steps） |
| **向量库** | FAISS | FAISS + Milvus 双支持 |
| **Embedding** | DashScope API（远程 ~42s） | 同（待优化为本地模型） |

---

## 三、请求链路详细对比

### 3.1 知识问答链路

**RAG 版本**（3 步）：
```
Question → FAISS.search(k=5) → LLM.get_answer(docs) → Response
耗时：Embedding ~42s + Search <1s + LLM ~5s ≈ 47s
```

**Agent 版本（优化前）**（7+ 步）：
```
Question → Router.classify()
  → KnowledgeQAAgent.ask()
    → Orchestrator.run()
      → Planner.plan_steps()
      → Executor.execute_step("knowledge_search")
        → RetrievalAgent.retrieve()
          → QuestionRewriteTool.execute()     # LLM 调用 #1
          → KnowledgeSearchTool.execute()      # Embedding + Search
          → RerankTool.execute()               # 重排序
          → CitationIntegrator.integrate()
      → Executor.execute_step("answer_generate")
        → LLM.get_answer()                    # LLM 调用 #2
  → Response
耗时：Classify <1s + Rewrite ~5s + Embedding ~42s + Search <1s
      + Rerank ~2s + LLM ~5s ≈ 55s+
```

**Agent 版本（优化后）**（3 步，与 RAG 基本一致）：
```
Question → Router.classify() <1s
  → KnowledgeQAAgent.ask()
    → VectorStore.search(k=5)                  # Embedding + Search
    → LLM.get_answer(docs)                     # LLM 生成
  → Response
耗时：Classify <1s + Embedding ~42s + Search <1s + LLM ~5s ≈ 48s
```

### 3.2 闲聊链路

**RAG 版本**：
```
"你好" → FAISS.search() → LLM.get_answer(无关文档) → 返回不相关回答
耗时：~47s（浪费大量资源）
```

**Agent 版本（优化后）**：
```
"你好" → Router.classify() → ChitChatAgent → 关键词匹配 "你好" → 返回预设回答
耗时：<1ms
```

### 3.3 管理端问答（Agent 独有）

**RAG 版本**：不支持

**Agent 版本**：
```
"最近有什么知识缺口？" → Router → AdminCopilotAgent → OpsAgent
  → 查询 QA 日志 → 分析未命中问题 → 生成运营报告
```

---

## 四、技术栈对比

### 4.1 后端 Python 服务

| 模块 | RAG 版本 | Agent 版本 |
|------|---------|-----------|
| Web 框架 | FastAPI | FastAPI（不变） |
| LLM | LangChain Tongyi | LangChain Tongyi（不变） |
| 向量库 | FAISS | FAISS + Milvus |
| Embedding | DashScope API | DashScope API（待优化为本地） |
| 工作流 | 无 | `workflows/` 目录（Router, QA, ChitChat, Ops） |
| Agent 框架 | 无 | `agent/` 目录（Orchestrator, Planner, Executor, State） |
| 工具层 | 硬编码 | `tools/` 目录（knowledge_search, rerank, citation 等） |
| 事件系统 | 无 | EventBus 发布/订阅模式 |

### 4.2 后端 Java 服务

| 模块 | RAG 版本 | Agent 版本 |
|------|---------|-----------|
| 框架 | Spring Boot 3.2.3 | Spring Boot 3.2.3（不变） |
| 超时配置 | 30s | 180s（优化后） |
| 缓存 | Redis + Caffeine | Redis + Caffeine（不变） |
| 认证 | JWT | JWT（不变） |

### 4.3 前端

| 模块 | RAG 版本 | Agent 版本 |
|------|---------|-----------|
| 框架 | React + Vite | React + Vite（不变） |
| 超时配置 | 30s | 180s（优化后） |
| 流式输出 | SSE | SSE（不变） |
| 管理端 | 仪表盘 + 知识库管理 | 新增 AI 助手对话界面 |

---

## 五、优缺点对比

### 5.1 RAG 版本

**优点**：
- **架构简单**：一条链路走到底，容易理解和调试
- **响应快**：没有额外的分类、编排开销
- **资源消耗少**：没有多层 Agent 的初始化成本
- **部署简单**：组件少，依赖少
- **确定性强**：每次请求走同一条路径，行为可预测

**缺点**：
- **无法区分意图**：闲聊也走检索+LLM，浪费资源且效果差
- **无管理能力**：不能做知识巡检、运营分析
- **无工具编排**：无法灵活组合多种工具
- **扩展性差**：新增功能需要改主链路代码
- **无可观测性**：没有 trace_id、step 记录，难以排查问题
- **检索质量固定**：不能按场景选择是否 Rewrite / Rerank

### 5.2 Agent 版本

**优点**：
- **意图识别**：Router Agent 区分闲聊/问答/管理，闲聊 <1ms 响应
- **多 Agent 协作**：不同任务走不同 Agent，职责清晰
- **工具可编排**：Tool Registry 支持灵活组合
- **可扩展性强**：新增 Agent 只需注册到 Router，不改主链路
- **可观测性**：run_id + trace_id + step 记录，完整执行链路可追踪
- **管理端能力**：Ops Agent 提供知识缺口分析、运营建议
- **灵活检索策略**：可按需开启 Query Rewrite / Rerank

**缺点**：
- **架构复杂**：多层抽象（Router → Agent → Orchestrator → Executor → Tool），理解和调试成本高
- **冷启动慢**：Agent 初始化需要加载多个组件
- **冗余调用（优化前）**：Orchestrator → Planner → Executor 引入额外 LLM 调用
- **分类不准确**：关键词权重方案存在误分类（如 "你是谁？" 被分为知识问答）
- **资源消耗大**：每个 Agent 都初始化自己的 VectorStore、LLM 等
- **过度工程化**：对于简单问答场景，Agent 链路是"杀鸡用牛刀"
- **Embedding 瓶颈未解**：DashScope API 42s 延迟是共同问题，Agent 架构没有解决

---

## 六、性能数据对比

| 指标 | RAG 版本 | Agent 版本（优化前） | Agent 版本（优化后） |
|------|---------|-------------------|-------------------|
| 闲聊响应 | ~47s（走检索） | ~5s（走 LLM） | <1ms（规则匹配） |
| 知识问答 | ~47s | ~55s+（多层开销） | ~48s（接近 RAG） |
| 管理端问答 | 不支持 | ~60s+ | 支持（独立链路） |
| 首次加载 | 快 | 慢（多 Agent 初始化） | 慢（同上） |
| 内存占用 | 低 | 高（多组件） | 高（同上） |

> **关键发现**：优化后的 Agent 版本在知识问答场景下性能接近 RAG 版本，但闲聊场景大幅提升（从 47s 降到 <1ms）。

---

## 七、优化过程中的关键问题与解决

### 7.1 已解决的问题

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| Python 超时 | DashScope API 延迟 + Orchestrator 多层调用 | 简化 KnowledgeQAAgent，去掉 Orchestrator fallback |
| Java SocketTimeout | RestTemplate readTimeout=30s | 提升到 180s |
| 前端超时 | axios timeout=30s | 提升到 180s |
| `page_content` AttributeError | `doc` 有时是 `str` 而非 `Document` | 添加 `hasattr` 检查 |
| 闲聊走检索浪费资源 | 无意图识别 | ChitChatAgent 规则匹配 |

### 7.2 待解决的问题

| 问题 | 影响 | 建议方案 |
|------|------|---------|
| DashScope Embedding 42s | 每次检索都要等 42s | 切换到本地 `BAAI/bge-small-zh-v1.5` |
| Router 误分类 | "你是谁？" 被分为知识问答 | 分类前去除标点符号 |
| 前端 setTimeout(500) | 响应有时不渲染 | 移除延迟或改用事件驱动 |
| Agent 组件重复初始化 | 每个 Agent 各自创建 VectorStore | 共享单例 |

---

## 八、面试讲解要点

### 8.1 项目演进故事线

> "这个项目最初是一个标准的 RAG 知识库问答系统，后来我将它升级为多 Agent 协作系统。升级的动机是：RAG 版本无法区分用户意图，闲聊也走检索+LLM，既浪费资源效果又差；同时也缺乏管理端的智能分析能力。"

### 8.2 技术选型理由

> "我选择在 Python 侧做 Agent 编排，因为 LangChain 生态更适合快速迭代 Agent 能力；Java 继续承担业务系统、鉴权、缓存等稳定底座；前端保持 React 不变。"

### 8.3 遇到的挑战

> "升级后最大的挑战是性能问题。Orchestrator 的 Plan-Execute 模式引入了额外的 LLM 调用，加上 DashScope Embedding API 的 42s 延迟，导致整体响应时间变长。我的解决方案是：对知识问答链路做'瘦身'，去掉不必要的 Orchestrator 层，让 KnowledgeQAAgent 直接走向量检索 → LLM 生成；对闲聊走规则匹配，完全不调 LLM。"

### 8.4 架构权衡

> "这里有一个重要的架构权衡：Agent 的 Orchestrator 模式（Plan → Execute → Observe）适合复杂多步任务，但对于单轮知识问答是过度工程化。我的做法是保留 Orchestrator 代码作为回退方案，但默认走精简 RAG 链路。这样既保证了核心场景的性能，又保留了 Agent 的扩展能力。"

### 8.5 未来优化方向

> "接下来的优化方向有两个：一是把 DashScope 远程 Embedding 切换为本地 `BAAI/bge-small-zh-v1.5` 模型，可以将检索延迟从 42s 降到 1-2s；二是修复 Router 的误分类问题，通过去除标点符号和优化关键词权重来提升分类准确率。"

### 8.6 RAG vs Agent 的本质区别

> **RAG** = 检索增强生成，本质是"找到相关文档 → 让 LLM 基于文档回答"。单轮、无状态、无决策。
>
> **Agent** = 具备感知-决策-执行-观察闭环的智能体。能判断任务类型、选择工具、拆解步骤、根据中间结果调整策略。
>
> 本项目的核心价值在于：**在同一个系统中，根据用户意图自动选择最合适的处理路径** —— 闲聊走规则、问答走 RAG、管理走 Agent。

---

## 九、项目代码结构对比

### RAG 版本代码结构
```
python-service/
├── api/
│   └── routes.py              # 单一入口，直接调检索+LLM
├── core/
│   ├── llm.py                 # LLM 调用
│   ├── vector_store.py        # FAISS 检索
│   ├── parser.py              # 文档解析
│   └── config.py              # 配置
└── requirements.txt
```

### Agent 版本代码结构
```
python-service/
├── api/
│   └── routes.py              # 入口，调 RouterAgent
├── agent/                     # Agent 框架层（新增）
│   ├── orchestrator.py        # 编排器：Plan → Execute → Observe
│   ├── planner.py             # 任务规划
│   ├── executor.py            # 步骤执行
│   ├── state.py               # Agent 状态管理
│   ├── events.py              # 事件总线
│   └── policies.py            # 执行策略
├── workflows/                 # 工作流层（新增）
│   ├── router_agent.py        # 路由 Agent：意图分类 → 分发
│   ├── knowledge_qa_agent.py  # 知识问答 Agent
│   ├── chitchat_agent.py      # 闲聊 Agent
│   ├── retrieval_agent.py     # 检索 Agent（完整 RAG 链路）
│   ├── admin_copilot_agent.py # 管理助手 Agent
│   ├── inspection_agent.py    # 知识巡检 Agent
│   └── ops_agent.py           # 运营分析 Agent
├── tools/                     # 工具层（新增）
│   ├── knowledge_search.py    # 知识检索工具
│   ├── question_rewrite.py    # 问题改写工具
│   ├── rerank.py              # 重排序工具
│   └── citation.py            # 引用整合工具
├── core/                      # 核心层（保留）
│   ├── llm.py
│   ├── vector_store.py
│   ├── parser.py
│   └── config.py
└── requirements.txt
```

---

## 十、总结

| | RAG 版本 | Agent 版本 |
|--|---------|-----------|
| **定位** | 知识库问答系统 | 智能知识管理平台 |
| **核心能力** | 检索 + 生成 | 意图识别 + 多 Agent 协作 + 工具编排 |
| **适用场景** | 纯问答 | 问答 + 闲聊 + 管理 + 巡检 |
| **复杂度** | 低 | 中高 |
| **性能** | 稳定但单一 | 需要优化但更灵活 |
| **扩展性** | 差 | 好 |
| **面试亮点** | RAG 链路实现 | Agent 架构设计 + 性能优化决策 |

**核心认知**：RAG 和 Agent 不是对立关系，而是包含关系 —— Agent 架构中包含了 RAG 作为核心工具之一。项目的演进不是"抛弃 RAG 换 Agent"，而是"在 RAG 基础上叠加 Agent 能力"。
