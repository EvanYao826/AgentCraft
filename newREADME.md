# AI Knowledge System

**AI Knowledge System** 是一个**企业级智能知识库问答平台**，采用 Java + Python 双服务架构，覆盖了智能对话、文档知识问答、RAG 检索增强生成、多 Agent 协作、工具调用、文档全生命周期管理、运营分析等完整能力。

项目从文档上传开始，到解析切分、向量化存储、语义检索、重排序、证据驱动生成，再到会话记忆管理、Agent 智能路由和知识巡检，**每一个环节都不是简单调个接口就完事的，而是经过工程化设计的完整实现**。

# 为什么需要这个项目

现在 Java 面试，光靠八股文和 CRUD 项目越来越难了。面试官开始问：**RAG 怎么实现的？向量检索用的什么方案？Agent 路由怎么做？会话记忆怎么设计？你的知识库系统和直接调 API 有什么区别？** 这些问题已经从加分项变成了必答题。

但问题是，大多数人学 AI 的方式是跟着教程调一下 API，往向量库里塞点数据，让模型输出一段话——结束了。这顶多算跑通了一个 Demo，面试官一追问就露馅。

而 AI Knowledge System 就是为了解决这个问题：它覆盖了 **RAG 检索增强生成、多 Agent 路由协作、自适应文档切分、双引擎向量检索、重排序精排、双层会话记忆、知识巡检与补库建议、运营分析报表** 这些 AI 应用层的核心技术，每一块都有完整的设计和代码实现。不管是学生还是工作了几年的同学，学完之后面试中都能真正聊得起来。

# 学 RAG 容易踩的坑

很多人觉得自己"会 RAG 了"，但面试一深入就露馅。在正式介绍项目之前，先把几个常见误区理清楚。

## 调个 API 不等于会 RAG

很多教程的套路是：调一下 Embedding 接口，往向量数据库里塞点数据，再用大模型生成答案——完事了。但真正的 RAG 系统要考虑的问题多得多：文档怎么切分效果最好？检索召回率不够怎么办？没有检索到证据怎么办？会话记忆怎么平衡 Token 成本和上下文完整性？这些才是面试官会追问的点。

## 只用向量检索远远不够

用户问一个订单号、一个配置项名，纯向量检索很可能找不到——语义相似度对精确匹配天然弱势。需要关键词检索作为补充，两路结果怎么融合排序，这是工程决策，不是换个更贵的模型就能解决的。

## 检索到了不等于能生成好答案

检索到了相关文档块，但如果只给模型一小段碎片，上下文不完整，生成的答案质量也会很差。检索粒度和回答粒度需要分开设计——检索用小块保精度，回答用大块保完整性。

## 没有证据时不让模型编造

最危险的情况是：知识库里没有相关信息，但模型照样自信地编出一个答案。架构层面必须有"无证据短路"机制——没有检索到足够证据时直接告知用户，从根源上杜绝幻觉。

# 这个项目能学到什么

先直接列出来，心里有数：

- **Java + Python 双服务架构：Java 端负责业务逻辑、认证、会话管理、缓存；Python 端负责文档解析、向量检索、Agent 编排、LLM 调用。通过 REST API 解耦，各司其职**

- **Router Agent 智能路由：不是所有问题都走同一条链路。系统先用关键词权重评分判断任务类型（闲聊 / 知识问答 / 管理助手 / 知识巡检），再分发给对应的专业 Agent 处理**

- **Retrieval Agent 完整检索链路：问题改写 → 向量召回 → 重排序精排 → 引用整合 → LLM 生成。不是"查个向量库 + 让模型回答"这么简单**

- **自适应语义分块器：按段落 → 句子 → 标点符号三级降级切分，保留语义完整性。不是固定长度一刀切**

- **双引擎向量数据库：Milvus 作为主引擎，FAISS 作为本地降级方案。支持自动降级和数据迁移**

- **三种 Reranker 策略：BGE CrossEncoder 精排、Cohere API 重排、Simple 关键词匹配兜底。还有 HybridReranker 混合多种策略加权融合**

- **双层会话记忆：短期记忆用 Redis 滑动窗口（最近 10 条），长期记忆用数据库存储对话摘要 + 重要性评分，每 5 条消息自动生成摘要**

- **Caffeine + Redis 多级缓存：本地缓存毫秒级响应，Redis 分布式缓存兜底。支持缓存击穿防护、热点数据标记、动态 TTL、Redis 不可用时自动降级到本地缓存**

- **知识巡检系统：自动分析未命中问题并聚类高频问题生成补库建议，检测知识库中的重复文档、低质量切片、过期文档、无人访问文档**

- **运营分析报表：热门问题 TOP10、知识库增长趋势、Agent 成功率、工具调用失败排行榜，用 ECharts 可视化展示**

- **Agent 运行可观测：AgentRun / AgentStep / ToolCall 三层记录体系，每次 Agent 运行的输入输出、每个步骤的耗时、每次工具调用的参数和结果全部可追溯**

- **多模态支持：图片通过 Tesseract OCR 提取文字后注入问题上下文，支持中英文混合识别**

- **完整管理后台：仪表盘、用户管理、知识库管理、问答日志、Agent 执行记录、知识巡检、运营报告、公告管理、管理助手对话——不是一个 Demo，是能上线用的系统**

# 系统整体是怎么跑的

用户在输入框里敲了一句话，点了发送。看起来很简单，但在系统内部，这条消息要经过一条复杂的链路：

```
用户提问
   │
   ▼
Java 后端 (Spring Boot :8080)
   │  保存消息 → 更新上下文 → 检查多级缓存
   │
   ▼
Python AI 服务 (FastAPI :8000)
   │
   ▼
Router Agent ── 关键词权重分类 ──┐
                                 │
   ┌─────────────────────────────┼─────────────────────────────┐
   │                             │                             │
   ▼                             ▼                             ▼
ChitChatAgent            KnowledgeQAAgent            AdminCopilotAgent
(闲聊:规则+LLM)               │                        (运营分析)
                              │
                              ▼
                      RetrievalAgent
                   (问题改写 → 向量召回 → 重排序 → 引用整合)
                              │
                              ▼
                      LLM 生成回答
                   (通义千问 qwen-plus)
                              │
                              ▼
                   返回 answer + sources + task_type
```

核心思路是：**不是让所有问题都走同一条链路，而是先做路由判定，再交给最合适的 Agent 处理。** 闲聊走规则匹配，知识问答走 RAG 检索，管理问题走运营分析。

# Router Agent 是怎么设计的

面试中聊 Agent，面试官不想听你说"我用了 Agent"，他想听的是你对这些问题的思考：

- **用户提了一个问题，系统是怎么决定用哪种方式来回答的？** 不是让模型自己选，而是用关键词权重评分做确定性分类。问候闲聊类关键词命中就走 ChitChatAgent，知识类关键词命中就走 KnowledgeQAAgent，管理员身份下管理类关键词命中就走 AdminCopilotAgent

- **为什么不用 LLM 做路由？** 路由判定需要低延迟和高确定性。用 LLM 做路由不仅慢，还可能误判。关键词权重评分虽然简单，但在这个场景下足够可靠，延迟几乎为零

- **路由错了怎么办？** KnowledgeQAAgent 内部有回退机制——如果 RAG 检索失败或结果质量不够，会回退到 Orchestrator 执行模式，用 Agent 自由探索

- **管理员和普通用户看到的回答一样吗？** 不一样。管理员模式下，Router Agent 会优先处理管理相关任务（运营分析、知识巡检），普通用户的管理类关键词不会触发这些 Agent

# 检索链路到底有多细

很多人以为检索就是"查个向量库 + 让模型回答"，但实际中间的环节比想象中多：

## 问题进来之后怎么处理？

- 用户问"那它怎么配置？"这种省略了主语的追问，直接拿去检索什么都找不到。所以要先做**问题改写**，结合前几轮对话上下文把指代补全
- 改写后的问题再交给检索链路，而不是用原始问题直接去查

## 检索是怎么做的？

- 不是只用向量检索。用户问一个配置项名、一个错误码，向量检索很可能找不到。所以用了**双引擎向量数据库**：Milvus 作为主引擎支持过滤查询，FAISS 作为本地降级方案
- 初始检索召回 top_k * 3 个候选文档，给后续重排序留足余量

## 重排序怎么做的？

- 检索回来的候选文档不一定都相关，需要精排。系统支持三种 Reranker：
  - **BGE Reranker**：使用 BAAI/bge-reranker-base CrossEncoder 模型，效果最好
  - **Cohere Reranker**：调用 Cohere API rerank-multilingual-v2.0
  - **Simple Reranker**：基于 Jaccard 相似度的关键词匹配，无外部依赖，兜底方案
- 还有 **HybridReranker**，加权融合多种 Reranker 结果
- 精排后取 top_k 个最相关的文档块

## 检索到了怎么组装回答？

- 通过 CitationIntegrator 为答案添加来源引用编号
- 要求模型在回答中标注证据来源
- 前端渲染时展示参考来源，支持点击跳转查看原文

## 没检索到证据怎么办？

- 如果最终没有任何有效证据，直接告知用户"知识库中未检索到相关信息"，不让模型凭空编造
- 错误响应不缓存，下次请求自动重新检索

# 文档从上传到可检索经历了什么

很多项目的文档处理就是"切成固定长度 → 向量化 → 完事"。但实际上不同文档差异很大，一刀切的效果很难好。

## 第一步：上传和存储

文件上传到七牛云对象存储（或本地存储），在数据库插入记录，状态为 PENDING。支持 PDF、DOC、DOCX、TXT、MD 五种格式。

## 第二步：异步解析

通过 `@Async` 异步调用 Python 服务的 `/api/parse` 端点，不阻塞主业务：

- **PDF**：使用 PyPDFLoader 解析
- **DOCX**：使用 Docx2txtLoader 解析
- **TXT/MD**：使用 TextLoader 解析
- **图片**：使用 Tesseract OCR 提取文字，支持中英文混合识别，带灰度预处理

## 第三步：自适应语义切分

不是固定长度一刀切。自定义的 SemanticChunkerSplitter 按语义边界切分：

| 切分层级 | 切分规则 | 作用 |
| :--- | :--- | :--- |
| 第一层：段落 | 按双换行符 `\n\n` 切分 | 保留段落完整性 |
| 第二层：句子 | 段落过长时按中文句号、感叹号、问号切分 | 保留句子语义 |
| 第三层：标点 | 句子过长时按逗号、分号切分 | 控制块大小 |
| 最小块合并 | 小于 100 字的块合并到相邻块 | 避免碎片化 |

默认参数：chunk_size=500, chunk_overlap=50, min_chunk_size=100。还有 RecursiveCharacterTextSplitter 作为备用方案，分隔符适配中文标点。

## 第四步：向量化与双引擎索引

- **Embedding 模型**：优先使用阿里云 DashScope text-embedding-v1，回退到本地 sentence-transformers/all-MiniLM-L6-v2
- **向量数据库**：优先写入 Milvus，同时写入 MySQL knowledge_chunk 表备份
- 每一步都有状态追踪：PENDING → PROCESSING → COMPLETED / FAILED

# 会话记忆：Token 成本和上下文完整性的博弈

20 轮对话全塞给模型？Token 成本扛不住。只带最近几轮？可能丢掉关键上下文。系统设计了双层记忆机制：

## 短期记忆（Redis 滑动窗口）

- 每个对话的最近消息缓存在 Redis 中
- 默认保留最近 10 条消息，可动态调整 5-20 条
- 读取时先查 Redis，未命中再查数据库
- 适合短期连续追问的场景

## 长期记忆（数据库摘要）

- `ConversationContext` 实体存储对话摘要、embedding、重要性评分、窗口大小
- 每 5 条消息自动生成摘要，提取关键词、决策、用户偏好
- 每 10 条消息保存长期记忆
- 消息重要性评分算法：考虑内容长度、是否有来源、是否用户消息、是否包含关键决策词
- 自动清理低重要性的过期上下文（30 天以上且重要性 < 0.3）

# 多级缓存：不是加个 Redis 就完事

系统实现了 Caffeine + Redis 两级缓存架构，每一层都有不同的设计考量：

| 缓存层级 | 响应时间 | 容量 | 适用场景 |
| :--- | :--- | :--- | :--- |
| Caffeine 本地缓存 | 毫秒级 | 1000 条 | 热点 AI 回答、对话上下文 |
| Redis 分布式缓存 | 秒级 | 无限 | 跨实例共享、会话状态 |
| 数据库 / AI 服务 | 百毫秒级 | 无限 | 兜底数据源 |

5 种缓存命名空间各有不同的 TTL 和容量策略：

| 缓存类型 | TTL | 最大条目 | 特殊策略 |
| :--- | :--- | :--- | :--- |
| ai_answer | 1 小时 | 10000 | userId+question 作键，防止数据泄露 |
| user_session | 24 小时 | 5000 | - |
| doc_metadata | 5 分钟 | 1000 | - |
| conversation_context | 30 分钟 | 2000 | 动态 TTL：读取后延长 2 分钟，更新后延长 5 分钟 |
| vector_search | 10 分钟 | 500 | - |

还有这些防护机制：
- **缓存击穿防护**：synchronized 锁 + 双重检查，防止缓存失效瞬间大量请求穿透到数据库
- **热点数据标记**：标记为永不过期的热点数据
- **降级策略**：Redis 不可用时自动降级到仅使用本地缓存，不影响核心功能
- **错误不缓存**：AI 服务返回的错误响应不缓存，下次请求自动重试

# 知识巡检：不只是能问答，还能自我进化

系统不只是被动回答问题，还能主动发现知识库的问题：

## 未命中问题分析

- 自动记录每次"知识库中未检索到相关信息"的问题
- 聚类分析高频未命中问题
- 生成补库建议：哪些领域需要补充文档

## 知识库质量巡检

- **重复文档检测**：找出内容高度相似的文档组
- **低质量切片检测**：找出过短、过长、或内容异常的切片
- **过期文档检测**：找出长期未更新的文档
- **无人访问文档检测**：找出从未被检索命中的文档

# 管理后台：不是一个 Demo

很多开源项目只做了用户端对话，管理后台要么没有要么很简陋。这个项目有一套完整的运营管理后台：

| 功能模块 | 说明 |
| :--- | :--- |
| 数据仪表盘 | 核心指标卡片（用户数/文档数/提问数/AI命中率）+ ECharts 饼图和 7 日趋势图 |
| 用户管理 | 用户列表分页 + 封禁/解封 |
| 知识库管理 | 文档上传/列表/删除/失败重试/错误信息展示 |
| 问答日志 | 所有问答记录分页查看 + 详情弹窗 + 反馈状态 |
| Agent 执行记录 | Agent 运行列表 + 步骤轨迹详情（意图识别/问题分类/知识检索/答案生成） |
| 知识巡检 | 未命中问题聚类分析 + 知识库质量检测 |
| 运营报表 | 热门问题 TOP10 / 知识库增长趋势 / Agent 成功率 / 工具调用失败排行 |
| 管理助手 | 独立的 AI 对话界面，可执行运营分析、知识巡检等管理操作 |
| 公告管理 | 企业通知的增删改查 |

# 工程质量不是靠嘴说的

## Java-Python 双服务架构

Java 负责业务逻辑、认证、数据管理；Python 负责 AI/RAG 核心。通过 REST API 解耦，各司其职。这种架构的好处是：
- AI 能力可以用 Python 生态的丰富工具（LangChain、FAISS、sentence-transformers）
- 业务逻辑用 Java 的强类型和 Spring 生态保证稳定性
- 两个服务可以独立部署和扩展

## 向量数据库双引擎

Milvus 作为主引擎，支持分布式部署、过滤查询、高效删除。FAISS 作为本地降级方案，Milvus 不可用时自动切换。还提供了 FAISS 到 Milvus 的数据迁移工具。

## Agent 运行可观测

完整的三层记录体系：

| 层级 | 表 | 记录内容 |
| :--- | :--- | :--- |
| 运行层 | agent_run | traceId, goal, status, input, output, 耗时 |
| 步骤层 | agent_step | stepType, stepName, status, durationMs |
| 工具层 | tool_call | toolName, inputParams, output, status, durationMs |

前端 AgentRunManagement 页面可以查看每次 Agent 运行的完整步骤轨迹。

## 安全设计

- **Spring Security 无状态会话** + JWT 认证
- **双重鉴权**：管理端同时使用 Spring Security 角色控制 + AdminInterceptor 拦截器
- **敏感词过滤**：使用 Hutool 的 WordTree DFA 算法
- **密码 BCrypt 加密**，登录时自动迁移明文密码为加密密码（兼容升级）
- **@JsonIgnore** 防止密码序列化泄露
- **错误响应不暴露技术细节**

## 异步处理

文档解析、标题生成、向量删除、问答日志记录都使用 `@Async` 异步执行，不阻塞主业务。用户发完消息可以立即得到响应，后台慢慢处理。

# 和普通的 RAG 项目有什么区别

| 对比维度 | 普通 RAG 项目 | AI Knowledge System |
| :--- | :--- | :--- |
| 技术架构 | 单语言单服务 | Java + Python 双服务，各司其职 |
| 任务路由 | 所有问题走同一条链路 | Router Agent 按任务类型智能分发 |
| 检索方式 | 单路向量检索 | 向量检索 + 三种 Reranker 精排 |
| 向量数据库 | 单引擎 | Milvus + FAISS 双引擎，支持自动降级和迁移 |
| 文档切分 | 固定长度一刀切 | 语义分块器：段落 → 句子 → 标点三级降级 |
| 会话记忆 | 全量塞给模型或不带 | 双层记忆：Redis 滑动窗口 + 数据库摘要 |
| 缓存设计 | 无或只有 Redis | Caffeine + Redis 两级缓存，5 种命名空间各自策略 |
| 证据控制 | 无 | 无检索结果时短路返回，不让模型编造 |
| 知识巡检 | 无 | 未命中问题聚类 + 文档质量检测 + 补库建议 |
| Agent 可观测 | 无 | AgentRun/AgentStep/ToolCall 三层追踪 |
| 管理后台 | 无或简陋 | 仪表盘/用户管理/知识库/日志/巡检/报表/公告 |
| 多模态 | 不支持 | 图片 OCR 提取文字注入上下文 |
| 运营报表 | 无 | 热门问题/增长趋势/Agent成功率/工具失败排行 |

一句话：**每个环节都不是调个 API 就完事的，而是有完整的工程设计。**

# 适合什么人

## 在校生 / 校招同学：

- 简历上已经有了商城、外卖等常规项目，需要一个有区分度的项目来拉开差距。AI Knowledge System 能让你在面试中聊 RAG + Agent + 工程化，而不是千篇一律的 CRUD
- 项目用的是 Java + Python 双语言，能证明你的技术栈广度
- 大厂校招越来越看重候选人对新技术的敏感度，简历上有 AI 项目经验，能直接证明学习能力和技术视野

## 社招同学：

- 1-3 年经验：日常写业务代码，想往 AI 方向转型但不知道从哪下手。Java 技术栈你都熟悉，Python 端也不复杂，上手快
- 3-5 年经验：技术能力不差，但面试被问到 AI 相关问题答不上来。通过项目补上 RAG、Agent、向量检索这些知识点，面试时能聊得有深度
- 想跳槽到 AI 团队：越来越多的 JD 要求有 AI 相关经验，项目能帮你快速建立 RAG 系统的全局认知

**一句话：学完 AI Knowledge System，你既能跟面试官聊 RAG、Agent、向量检索的技术深度，也能证明自己的项目工程化水平。**

# 用到的技术一览

| 技术 | 说明 | 官网 |
| :--- | :--- | :--- |
| Java 17 | 编译和运行版本 | https://openjdk.org |
| Spring Boot 3.2.3 | Java 后端框架 | https://spring.io/projects/spring-boot |
| Spring Security 6.2 | 安全框架 | https://spring.io/projects/spring-security |
| MyBatis-Plus 3.5.5 | ORM 框架 | https://baomidou.com |
| MySQL 8.0 | 关系型数据库 | https://www.mysql.com |
| Redis | 分布式缓存 | https://redis.io |
| Caffeine | 本地缓存 | https://github.com/ben-manes/caffeine |
| FastAPI | Python Web 框架 | https://fastapi.tiangolo.com |
| LangChain | AI 应用框架 | https://www.langchain.com |
| Milvus | 向量数据库（主引擎） | https://milvus.io |
| FAISS | 向量检索（降级方案） | https://github.com/facebookresearch/faiss |
| DashScope | 阿里云大模型服务（通义千问 qwen-plus） | https://dashscope.aliyun.com |
| BGE Reranker | 语义重排序模型 | https://huggingface.co/BAAI/bge-reranker-base |
| Cohere | Rerank API 服务 | https://cohere.com |
| Tesseract OCR | 图片文字识别 | https://github.com/tesseract-ocr/tesseract |
| React 18 | 前端框架 | https://reactjs.org |
| Vite 5 | 前端构建工具 | https://vitejs.dev |
| ECharts | 数据可视化 | https://echarts.apache.org |
| JWT | 登录认证 | https://github.com/jwtk/jjwt |
| 七牛云 Kodo | 对象存储 | https://www.qiniu.com |
| Hutool | Java 工具类库 | https://hutool.cn |
| Lombok | Java 语言增强 | https://projectlombok.org |
| SpringDoc OpenAPI | Swagger API 文档 | https://springdoc.org |

# 如何启动项目

## 环境要求

- **JDK**：17 或更高版本
- **Python**：3.10+
- **Node.js**：18+
- **MySQL**：8.0+
- **Redis**：7.0+
- **Milvus**：2.4+（可选，不安装会自动降级到 FAISS）

## 1. 启动 Python AI 服务

```bash
cd python-service
pip install -r requirements.txt
# 配置 .env 文件（参考 .env.example）
python main.py
```

服务运行在 http://127.0.0.1:8000

## 2. 启动 Java 后端

```bash
# 配置 application.yml 中的数据库和 Redis 连接
mvn clean package -DskipTests
java -jar target/*.jar
```

服务运行在 http://localhost:8080

## 3. 启动前端

```bash
cd frontend
npm install
npm run dev
```

服务运行在 http://localhost:5173

## 4. 初始化数据库

```bash
mysql -u root -p < sql/init.sql
# 按顺序执行升级脚本
mysql -u root -p ai_knowledge_db < sql/update_v2.sql
mysql -u root -p ai_knowledge_db < sql/update_admin.sql
# ... 其他 upgrade 脚本
```
