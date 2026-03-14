class TodocError(Exception):
    """Base exception for todoc."""
    pass

class TaskNotFoundError(TodocError):
    """Raised when a task ID does not exist."""
    pass

class StorageError(TodocError):
    """Raised when reading/writing to JSON fails."""
    pass
