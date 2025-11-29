"""
Outfit Queue System - Manages multi-item uploads from outfit photos
"""
import uuid
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta

@dataclass
class QueuedItem:
    image_bytes: bytes
    description: str
    category: str
    color: str
    
@dataclass  
class UploadQueue:
    queue_id: str
    user_id: int
    items: List[QueuedItem]
    current_index: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    
    @property
    def total_items(self) -> int:
        return len(self.items)
    
    @property
    def has_next(self) -> bool:
        return self.current_index < len(self.items)
    
    def get_current(self) -> Optional[QueuedItem]:
        if self.has_next:
            return self.items[self.current_index]
        return None
    
    def advance(self) -> Optional[QueuedItem]:
        self.current_index += 1
        return self.get_current()


# In-memory queue storage (replace with Redis for production)
_queues: Dict[str, UploadQueue] = {}

def create_queue(user_id: int, items: List[QueuedItem]) -> UploadQueue:
    """Create a new upload queue"""
    queue_id = str(uuid.uuid4())
    queue = UploadQueue(
        queue_id=queue_id,
        user_id=user_id,
        items=items
    )
    _queues[queue_id] = queue
    
    # Clean up old queues (older than 1 hour)
    cleanup_old_queues()
    
    return queue

def get_queue(queue_id: str, user_id: int) -> Optional[UploadQueue]:
    """Get queue by ID, verify ownership"""
    queue = _queues.get(queue_id)
    if queue and queue.user_id == user_id:
        return queue
    return None

def delete_queue(queue_id: str):
    """Delete a queue"""
    if queue_id in _queues:
        del _queues[queue_id]

def cleanup_old_queues():
    """Remove queues older than 1 hour"""
    cutoff = datetime.now() - timedelta(hours=1)
    old_keys = [k for k, v in _queues.items() if v.created_at < cutoff]
    for key in old_keys:
        del _queues[key]
