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
        rule: Keyword-only. The emitting check's id: its function name
            without ``_check_`` (``fan_out_without_trigger``,
            ``gain_staging``, ...), or a per-finding ``ext_*`` /
            ``rnbo_missing_inner_patcher`` id where one function emits
            several kinds (fix-plan Q33 / review S7).
        box_ids: Keyword-only. The real box ids the finding is about,
            deduplicated, in the order the finding text names them (a
            subject box the text names only by label may be included);
            never a placeholder such as ``"?"``. Stored as a tuple.
        port: Keyword-only. The port index that is part of the finding's
            identity -- the source outlet for ``fan_out_without_trigger``,
            the gain inlet for ``unsafe_gain_sources`` and the destination
            inlet for ``bach_llll_types`` -- else None.

    The review allowlist (tests/review_blocker_allowlist.json) keys on
    ``(rule, box_ids, port, path)``.
    """

    __slots__ = ("severity", "finding", "suggestion", "path", "rule", "box_ids", "port")

    def __init__(
        self,
        severity: str,
        finding: str,
        suggestion: str,
        path: str = "",
        *,
        rule: str = "",
        box_ids=(),
        port: int | None = None,
    ):
        self.severity = severity
        self.finding = finding
        self.suggestion = suggestion
        self.path = path
        self.rule = rule
        self.box_ids = tuple(box_ids)
        self.port = port

    def __repr__(self) -> str:
        return f"[{self.severity}] {self.finding}"


def finding_ids(*ids) -> tuple:
    """Box ids for :attr:`CriticResult.box_ids` (Q33).

    Keeps the str ids in order, drops duplicates, ``None`` and the ``"?"``
    placeholder (a box without an id).
    """
    out: list[str] = []
    for i in ids:
        if isinstance(i, str) and i and i != "?" and i not in out:
            out.append(i)
    return tuple(out)


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
