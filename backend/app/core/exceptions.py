"""
应用异常处理模块

定义统一的异常基类和常见业务异常子类，用于标准化API错误响应格式。
"""

from typing import Any, Dict, Optional


class AppException(Exception):
    """应用异常基类"""
    
    def __init__(
        self,
        error_code: str,
        detail: str,
        status_code: int = 500,
        extra: Optional[Dict[str, Any]] = None
    ):
        self.error_code = error_code
        self.detail = detail
        self.status_code = status_code
        self.extra = extra or {}
        super().__init__(self.detail)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为标准错误响应格式"""
        return {
            "error": self.error_code,
            "detail": self.detail,
            "status_code": self.status_code,
            **self.extra
        }


class AuthException(AppException):
    """认证相关异常"""
    
    def __init__(self, detail: str, status_code: int = 401, extra: Optional[Dict[str, Any]] = None):
        super().__init__("AUTH_ERROR", detail, status_code, extra)


class CaseException(AppException):
    """案件相关异常"""
    
    def __init__(self, detail: str, status_code: int = 400, extra: Optional[Dict[str, Any]] = None):
        super().__init__("CASE_ERROR", detail, status_code, extra)


class WorkflowException(AppException):
    """工作流相关异常"""
    
    def __init__(self, detail: str, status_code: int = 400, extra: Optional[Dict[str, Any]] = None):
        super().__init__("WORKFLOW_ERROR", detail, status_code, extra)


class ApprovalException(AppException):
    """审批相关异常"""
    
    def __init__(self, detail: str, status_code: int = 400, extra: Optional[Dict[str, Any]] = None):
        super().__init__("APPROVAL_ERROR", detail, status_code, extra)


class RateLimitExceededError(AppException):
    """API 限流异常"""

    def __init__(self, detail: str = "请求过于频繁，请稍后再试", extra: Optional[Dict[str, Any]] = None):
        super().__init__("RATE_LIMIT_EXCEEDED", detail, 429, extra)


class LlmQueueTimeoutError(AppException):
    """LLM 排队超时异常"""

    def __init__(self, detail: str = "LLM 服务繁忙，请稍后重试", extra: Optional[Dict[str, Any]] = None):
        super().__init__("LLM_QUEUE_TIMEOUT", detail, 503, extra)