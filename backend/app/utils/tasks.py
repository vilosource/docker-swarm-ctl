from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import asyncio


class TaskManager:
    def __init__(self):
        self._tasks: Dict[str, Dict[str, Any]] = {}
    
    def create_task(self, task_id: str, description: str) -> Dict[str, Any]:
        task = {
            "id": task_id,
            "status": "pending",
            "description": description,
            "progress": 0,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "result": None,
            "error": None
        }
        self._tasks[task_id] = task
        return task
    
    def update_task(
        self,
        task_id: str,
        status: Optional[str] = None,
        progress: Optional[int] = None,
        result: Optional[Any] = None,
        error: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        if task_id not in self._tasks:
            return None
        
        task = self._tasks[task_id]
        
        if status:
            task["status"] = status
        if progress is not None:
            task["progress"] = progress
        if result is not None:
            task["result"] = result
        if error:
            task["error"] = error
        
        task["updated_at"] = datetime.utcnow().isoformat()
        
        return task
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        return self._tasks.get(task_id)
    
    def list_tasks(self) -> List[Dict[str, Any]]:
        return list(self._tasks.values())
    
    def cleanup_old_tasks(self, hours: int = 24):
        """Remove tasks older than specified hours"""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        tasks_to_remove = []
        for task_id, task in self._tasks.items():
            created_at = datetime.fromisoformat(task["created_at"])
            if created_at < cutoff:
                tasks_to_remove.append(task_id)
        
        for task_id in tasks_to_remove:
            del self._tasks[task_id]


# Global task manager instance
task_manager = TaskManager()