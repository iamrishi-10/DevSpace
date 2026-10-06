from enum import StrEnum

class ProjectType(StrEnum):
    """Enum for project types"""

    PYTHON = "python"
    JAVA = "java"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    GENERIC = "generic"


if __name__ == "__main__":
    assert all(isinstance(p, ProjectType) for p in ProjectType)
    assert ProjectType("typescript") is ProjectType.TYPESCRIPT
    print("ProjectType OK")
    print(ProjectType.PYTHON == "python")
