from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Union
from enum import Enum
import uuid
import time


class AgentStatus(Enum):
    """Agent 运行状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    INTERRUPTED = "interrupted"
    WAITING = "waiting"


class StepStatus(Enum):
    """步骤状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class StepType(Enum):
    """步骤类型"""
    INTENT_RECOGNITION = "intent_recognition"
    QUESTION_CLASSIFICATION = "question_classification"
    CLARIFICATION = "clarification"
    QUESTION_REWRITE = "question_rewrite"
    KNOWLEDGE_SEARCH = "knowledge_search"
    RESULT_EVALUATION = "result_evaluation"
    ANSWER_GENERATION = "answer_generation"
    MEMORY_READ = "memory_read"
    MEMORY_WRITE = "memory_write"
    MEMORY_COMPRESS = "memory_compress"
    TOOL_CALL = "tool_call"


@dataclass
class AgentStep:
    """Agent 步骤"""
    step_id: str
    step_type: StepType
    step_name: str
    status: StepStatus = StepStatus.PENDING
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    tool_call_id: Optional[str] = None

    def start(self):
        """开始执行步骤"""
        self.status = StepStatus.RUNNING
        self.start_time = time.time()

    def complete(self, output_data: Dict[str, Any]):
        """完成步骤"""
        self.status = StepStatus.COMPLETED
        self.output_data = output_data
        self.end_time = time.time()

    def fail(self, error_message: str):
        """步骤失败"""
        self.status = StepStatus.FAILED
        self.error_message = error_message
        self.end_time = time.time()

    def skip(self):
        """跳过步骤"""
        self.status = StepStatus.SKIPPED
        self.end_time = time.time()

    @property
    def duration_ms(self) -> Optional[float]:
        """获取步骤执行时长（毫秒）"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time) * 1000
        return None


@dataclass
class IntermediateConclusion:
    """中间结论"""
    step_id: str
    conclusion_type: str
    content: Any
    confidence: float = 0.0
    sources: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ToolCallRecord:
    """工具调用记录"""
    tool_call_id: str
    tool_name: str
    input_params: Dict[str, Any]
    output: Dict[str, Any]
    status: str
    duration_ms: float
    error_message: Optional[str] = None
    timestamp: float = field(default_factory=lambda: time.time())


@dataclass
class AgentState:
    """Agent 状态"""
    
    # 核心标识
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    conversation_id: Optional[str] = None
    user_id: Optional[str] = None
    
    # 当前状态
    status: AgentStatus = AgentStatus.PENDING
    
    # 目标与输入
    goal: Optional[str] = None
    original_input: Optional[str] = None
    context: str = ""
    
    # 步骤管理
    current_step_index: int = 0
    steps: List[AgentStep] = field(default_factory=list)
    planned_steps: List[str] = field(default_factory=list)
    
    # 中间结论
    intermediate_conclusions: List[IntermediateConclusion] = field(default_factory=list)
    
    # 工具调用记录
    tool_calls: List[ToolCallRecord] = field(default_factory=list)
    
    # 最终输出
    final_output: Optional[Dict[str, Any]] = None
    
    # 错误信息
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    
    # 时间戳
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    
    # 配置参数
    max_steps: int = 20
    timeout_seconds: int = 300
    
    @property
    def current_step(self) -> Optional[AgentStep]:
        """获取当前步骤"""
        if 0 <= self.current_step_index < len(self.steps):
            return self.steps[self.current_step_index]
        return None

    @property
    def elapsed_time(self) -> float:
        """获取已执行时间（秒）"""
        if self.start_time:
            return time.time() - self.start_time
        return 0.0

    @property
    def is_timeout(self) -> bool:
        """检查是否超时"""
        return self.elapsed_time > self.timeout_seconds

    @property
    def is_max_steps_reached(self) -> bool:
        """检查是否达到最大步骤数"""
        return len([s for s in self.steps if s.status in [StepStatus.COMPLETED, StepStatus.FAILED]]) >= self.max_steps

    def add_step(self, step_type: StepType, step_name: str, input_data: Optional[Dict[str, Any]] = None) -> AgentStep:
        """添加新步骤"""
        step = AgentStep(
            step_id=str(uuid.uuid4()),
            step_type=step_type,
            step_name=step_name,
            input_data=input_data or {}
        )
        self.steps.append(step)
        return step

    def advance_step(self) -> bool:
        """推进到下一步"""
        if self.current_step_index < len(self.steps) - 1:
            self.current_step_index += 1
            return True
        return False

    def add_intermediate_conclusion(self, step_id: str, conclusion_type: str, content: Any, 
                                   confidence: float = 0.0, sources: Optional[List[Dict[str, Any]]] = None):
        """添加中间结论"""
        conclusion = IntermediateConclusion(
            step_id=step_id,
            conclusion_type=conclusion_type,
            content=content,
            confidence=confidence,
            sources=sources or []
        )
        self.intermediate_conclusions.append(conclusion)

    def add_tool_call(self, tool_call_id: str, tool_name: str, input_params: Dict[str, Any],
                      output: Dict[str, Any], status: str, duration_ms: float, error_message: Optional[str] = None):
        """添加工具调用记录"""
        record = ToolCallRecord(
            tool_call_id=tool_call_id,
            tool_name=tool_name,
            input_params=input_params,
            output=output,
            status=status,
            duration_ms=duration_ms,
            error_message=error_message
        )
        self.tool_calls.append(record)

    def start(self):
        """开始执行"""
        self.status = AgentStatus.RUNNING
        self.start_time = time.time()

    def complete(self, final_output: Dict[str, Any]):
        """完成执行"""
        self.status = AgentStatus.COMPLETED
        self.final_output = final_output
        self.end_time = time.time()

    def fail(self, error_message: str, error_code: Optional[str] = None):
        """执行失败"""
        self.status = AgentStatus.FAILED
        self.error_message = error_message
        self.error_code = error_code
        self.end_time = time.time()

    def interrupt(self):
        """中断执行"""
        self.status = AgentStatus.INTERRUPTED
        self.end_time = time.time()

    def wait(self):
        """等待状态"""
        self.status = AgentStatus.WAITING

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "run_id": self.run_id,
            "trace_id": self.trace_id,
            "conversation_id": self.conversation_id,
            "user_id": self.user_id,
            "status": self.status.value,
            "goal": self.goal,
            "original_input": self.original_input,
            "context": self.context,
            "current_step_index": self.current_step_index,
            "steps": [
                {
                    "step_id": step.step_id,
                    "step_type": step.step_type.value,
                    "step_name": step.step_name,
                    "status": step.status.value,
                    "input_data": step.input_data,
                    "output_data": step.output_data,
                    "error_message": step.error_message,
                    "duration_ms": step.duration_ms,
                    "tool_call_id": step.tool_call_id
                }
                for step in self.steps
            ],
            "planned_steps": self.planned_steps,
            "intermediate_conclusions": [
                {
                    "step_id": c.step_id,
                    "conclusion_type": c.conclusion_type,
                    "content": c.content,
                    "confidence": c.confidence,
                    "sources": c.sources
                }
                for c in self.intermediate_conclusions
            ],
            "tool_calls": [
                {
                    "tool_call_id": tc.tool_call_id,
                    "tool_name": tc.tool_name,
                    "input_params": tc.input_params,
                    "output": tc.output,
                    "status": tc.status,
                    "duration_ms": tc.duration_ms,
                    "error_message": tc.error_message,
                    "timestamp": tc.timestamp
                }
                for tc in self.tool_calls
            ],
            "final_output": self.final_output,
            "error_message": self.error_message,
            "error_code": self.error_code,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "elapsed_time": self.elapsed_time,
            "max_steps": self.max_steps,
            "timeout_seconds": self.timeout_seconds
        }


class TerminationCondition:
    """终止条件判断器"""
    
    @staticmethod
    def should_terminate(state: AgentState) -> bool:
        """判断是否应该终止"""
        return any([
            state.status in [AgentStatus.COMPLETED, AgentStatus.FAILED, AgentStatus.INTERRUPTED],
            state.is_timeout,
            state.is_max_steps_reached
        ])

    @staticmethod
    def should_fail(state: AgentState) -> bool:
        """判断是否应该标记为失败"""
        # 检查是否有失败的步骤
        failed_steps = [s for s in state.steps if s.status == StepStatus.FAILED]
        return len(failed_steps) > 0

    @staticmethod
    def get_termination_reason(state: AgentState) -> str:
        """获取终止原因"""
        if state.status == AgentStatus.COMPLETED:
            return "任务已完成"
        elif state.status == AgentStatus.FAILED:
            return f"任务失败: {state.error_message or '未知原因'}"
        elif state.status == AgentStatus.INTERRUPTED:
            return "任务已中断"
        elif state.is_timeout:
            return f"任务超时（超过 {state.timeout_seconds} 秒）"
        elif state.is_max_steps_reached:
            return f"达到最大步骤数（{state.max_steps} 步）"
        return "正常运行中"
