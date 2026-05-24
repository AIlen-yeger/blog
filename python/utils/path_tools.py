from pathlib import Path


def get_project_tool() -> Path:
    current_file = Path(__file__).resolve()
    current_dir = current_file.parent
    current_file = current_dir.parent


    return current_file
def get_abs_path(relative_path: str) -> Path:
    project_tool = get_project_tool()
    return project_tool / relative_path