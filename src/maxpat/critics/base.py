"""Base types for the critic system.

CriticResult is the unit of output -- a single finding from a critic
with severity, description, and suggestion for how to fix it.
"""

from __future__ import annotations

from src.maxpat import walk


class CriticResult:
    """A single critic finding.

    Attributes:
        severity: "blocker", "warning", or "note".
        finding: Human-readable description of the issue.
        suggestion: Recommended fix or improvement.
        path: Box-id chain of the scope the finding is in (``obj-1/obj-2``),
            ``""`` at the top level (Q20). Nested findings also carry a
            ``[p synth > gen~] `` prefix on ``finding`` (see
            :func:`tag_results`); top-level findings are unchanged. Part of
            the finding's identity: the save-gate key and the review
            allowlist key include it.
    """

    __slots__ = ("severity", "finding", "suggestion", "path")

    def __init__(self, severity: str, finding: str, suggestion: str, path: str = ""):
        self.severity = severity
        self.finding = finding
        self.suggestion = suggestion
        self.path = path

    def __repr__(self) -> str:
        return f"[{self.severity}] {self.finding}"


def tag_results(results: list, path: tuple) -> list:
    """Tag *results* found in the scope at walk *path* (Q20; Q19 convention).

    For a non-empty ``walk.iter_patchers`` path tuple, sets ``r.path`` to
    ``walk.path_ids(path)`` and prefixes ``r.finding`` with
    ``walk.path_prefix(path)``. For ``()`` (the top level) nothing changes.
    Suggestions are never prefixed. Returns *results*.
    """
    if not path:
        return results
    key = walk.path_ids(path)
    prefix = walk.path_prefix(path)
    for r in results:
        r.path = key
        r.finding = prefix + r.finding
    return results
