class DevSpaceError(Exception):
    """Base class for all DevSpace exceptions."""
    pass

class ProjectNotFoundError(DevSpaceError):
    """Raised when a project is not found."""
    pass

class DuplicateProjectError(DevSpaceError):
    """Raised when a project with the same name already exists."""
    pass

class InvalidProjectPathError(DevSpaceError):
    """Raised when an invalid project path is provided."""
    pass

class StorageError(DevSpaceError):
    """Raised when project storage operations fail."""
    pass

class CommandExecutionError(DevSpaceError):
    """Raised when a command execution fails."""
    pass


    