"""
Diff service: thin wrapper to produce unified diff between two Terraform strings.
Used by the Monaco Diff Editor integration.
"""
import difflib


def unified_diff(original: str, modified: str) -> list[str]:
    return list(
        difflib.unified_diff(
            original.splitlines(),
            modified.splitlines(),
            fromfile="generated.tf",
            tofile="reviewed.tf",
            lineterm="",
        )
    )


def diff_stats(original: str, modified: str) -> dict:
    lines = unified_diff(original, modified)
    added = sum(1 for l in lines if l.startswith("+") and not l.startswith("+++"))
    removed = sum(1 for l in lines if l.startswith("-") and not l.startswith("---"))
    return {"lines_added": added, "lines_removed": removed, "total_changes": added + removed}
