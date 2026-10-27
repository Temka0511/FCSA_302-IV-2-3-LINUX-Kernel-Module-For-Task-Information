"""Choose a startup source; explicit kernel requests never fall back."""
from pathlib import Path


def startup_source(source=None, kernel=False, procfs=False):
    if source is not None:
        return str(Path(source)), False
    if procfs:
        return "/proc/taskgraph", True
    if kernel or Path("/proc/taskgraph").exists():
        return "/proc/taskgraph", False
    # Portable UI preview: always visibly marked FIXTURE in the application.
    project = Path(__file__).resolve().parents[2]
    return str(project / "examples" / "small_tree.tsv"), False
