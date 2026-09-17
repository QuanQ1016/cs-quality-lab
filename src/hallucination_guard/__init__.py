"""客服回复幻觉检测工具。"""

from .core import Detection, HallucinationDetector, MockLLMClient, ReplyCase

__all__ = ["Detection", "HallucinationDetector", "MockLLMClient", "ReplyCase"]
__version__ = "1.0.0"
