import pytest
from unittest.mock import MagicMock, patch
from todoc.core.service import TodoService
from todoc.core.models import Task
from todoc.exceptions import TaskNotFoundError

def test_create_task():
    # Mock the repository
    with patch('todoc.core.service.TaskRepository') as MockRepo:
        mock_repo_instance = MockRepo.return_value
        mock_repo_instance.get_all.return_value = []
        
        service = TodoService()
        task = service.create_task("Buy milk")
        
        assert task.description == "Buy milk"
        assert task.id == 1
        mock_repo_instance.add.assert_called_once()

def test_complete_nonexistent_task():
    with patch('todoc.core.service.TaskRepository') as MockRepo:
        mock_repo_instance = MockRepo.return_value
        mock_repo_instance.get_all.return_value = [] # Empty list
        
        service = TodoService()
        
        with pytest.raises(TaskNotFoundError):
            service.complete_task(999)
