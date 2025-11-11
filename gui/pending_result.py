"""
Lưu tạm kết quả job chờ nhận tín hiệu TCP sensor IN
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class PendingJobResult:
    """Lưu tạm kết quả job chờ sensor IN signal từ TCP"""
    
    status: str  # OK, NG, PENDING
    similarity: float = 0.0
    reason: str = ""
    detection_data: Optional[Dict[str, Any]] = None
    inference_time: float = 0.0
    timestamp: float = 0.0
    
    def __post_init__(self):
        """Validate status"""
        if self.status not in ('OK', 'NG', 'PENDING'):
            logger.warning(f"Invalid status: {self.status}, using PENDING")
            self.status = 'PENDING'
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'status': self.status,
            'similarity': self.similarity,
            'reason': self.reason,
            'detection_data': self.detection_data,
            'inference_time': self.inference_time,
            'timestamp': self.timestamp,
        }
    
    def __repr__(self) -> str:
        return (f"PendingJobResult(status={self.status}, "
                f"similarity={self.similarity:.2%}, "
                f"reason='{self.reason[:30]}...')")
