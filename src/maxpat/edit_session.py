"""Edit session for an existing patch: ``with edit_patch(path) as p:`` (fix-plan Q36, review §5.3).

One call replaces the read -> edit -> finalize -> save -> commit recipe::

    session = edit_patch(path)
    with session as p:
        ...                      # edit p through the Patcher API
    print(session.diff.render())  # what changed
    session.commit_hash           # the path-scoped commit, or None

``__enter__`` re-reads the file on every entry (``read_patch``) and returns
the change-tracked Patcher. On a clean exit, in this order:

1. route only touched cords -- new cords and cords of boxes added or moved
   in this session that have no midpoints (``_finalize_midpoints_recursive``
   with ``layout._generate_midpoints``); existing midpoints are never
   cleared;
2. text contrast on added boxes only (D-03; locked decision B11, review
   261022-ud6 WR-07): the top-level boxes this session added (ids not in
   the file as read) that carry an explicit ``textcolor`` go through
   ``aesthetics._apply_text_contrast(patcher, only_ids=...,
   explicit_only=True)`` (panels and the background still come from the
   whole patcher). A box that was moved, put into presentation or replaced
   (replace_box keeps the id) keeps its colour; a comment without a
   textcolor is never given one (MAX renders it in the theme's text
   colour); self-painted objects (bach.roll, ...) are skipped and gradient
   panels are scored on both stops. Top level only, like
   ``ensure_text_contrast`` on new patches, so codeboxes inside a freshly
   added gen~ are left alone. Whole-patch ``repair_text_contrast`` is never
   run: it restyles 33 of the 63 committed patches on a no-op;
3. serialize, and compute ``session.diff`` against the file as read (before
   any save, so it survives a refusal);
4. no-op rule (D-04; 261022-ud6 WR-03): when the new dict is strictly
   identical to the file as read (``maxjson.json_identical``), nothing is
   checked, written or committed (``saved`` False, ``commit_hash`` None) --
   the Q29 byte-identical guarantee, for files in any layout (MAX 9.1+,
   Max 5 - 9.0.x tab layout, CRLF, the framework's expanded layout);
5. otherwise one ``save_patch_roundtrip(new, path, original_text,
   force=force)`` call: stale check, save gate (new blockers, cord-removal
   SaveGateWarning, port x-rank), the file's own JSON layout, the atomic
   write and the path-scoped auto-commit. Nothing is duplicated here.

No global auto-layout, no full ``finalize_patch``, no assistance-comment
fill: an approved patch is never restyled outside what the session touched.

Refusals and discards (D-01, D-02): an exception raised in the with-body
propagates and nothing is routed, written or committed. StaleFileError (the
file changed on disk after enter, typically a MAX save) and
PatchValidationError (the save gate) propagate from the exit with the file
untouched and nothing committed; ``session.patcher`` and ``session.diff``
stay inspectable.

``force=True`` is passed to save_patch_roundtrip unchanged. Use it only when
the user confirms (D-08, CLAUDE.md Rule #7).

A with-block lives in ONE Python process: put all the edits for one save in
one script; a block cannot span separate tool calls.

``edit_patch`` edits existing files only (a missing path raises
FileNotFoundError on enter); new patches keep the
``finalize_patch(is_new=True)`` + ``save_patch_roundtrip`` path.

``current_diff()`` previews the pending change inside the block (the hook
for the Q39 ``--fix`` preview).
"""

from __future__ import annotations

import json
from pathlib import Path

import src.maxpat.hooks as _hooks
from src.maxpat.maxjson import json_identical
from src.maxpat.patch_diff import PatchDiff, diff_patch_dicts


class EditSession:
    """Context manager for one edit of an existing patch file.

    Attributes after exit:
        patcher: the edited Patcher (also after a refusal).
        original_text: the file text as read on the last enter.
        diff: PatchDiff from the file as read to the edited patch (None
            until a clean exit computes it).
        saved: True when the exit wrote the file.
        commit_hash: the auto-commit hash, or None.
    """

    def __init__(self, path, *, force: bool = False) -> None:
        self.path = Path(path)
        self.force = force
        self.patcher = None
        self.original_text = None
        self.diff = None
        self.saved = False
        self.commit_hash = None
        self._baseline = None
        self._active = False

    def __enter__(self):
        if self._active:
            raise RuntimeError("edit session already active")
        patcher, original_text = _hooks.read_patch(self.path)
        self.patcher = patcher
        self.original_text = original_text
        self._baseline = json.loads(original_text)
        self.saved = False
        self.commit_hash = None
        self.diff = None
        self._active = True
        return patcher

    def __exit__(self, exc_type, exc, tb) -> bool:
        try:
            if exc_type is not None:
                # Discard (D-02): no routing, no serialization, no write.
                return False
            from src.maxpat import layout

            # 1. Touched cords only (D-03).
            _hooks._finalize_midpoints_recursive(self.patcher, layout._generate_midpoints)
            # 2. Text contrast on added top-level boxes with an explicit
            # textcolor only (D-03, B11 / WR-07).
            added = self._added_top_level_ids()
            if added:
                from src.maxpat import aesthetics

                aesthetics._apply_text_contrast(
                    self.patcher, only_ids=added, explicit_only=True
                )
            # 3. Serialize; diff before any save so it survives a refusal (D-01).
            new_dict = self.patcher.to_dict()
            self.diff = diff_patch_dicts(self._baseline, new_dict)
            # 4. No-op (D-04; 261022-ud6 WR-03): decided on content, not
            # bytes, so files in any layout (Max 8 / 9.0.x tabs, CRLF) count.
            if json_identical(new_dict, self._baseline) or (
                _hooks.format_patch_text(new_dict, self.original_text) == self.original_text
            ):
                return False
            # 5. One save: stale check, gate, format, atomic write, commit (D-05, D-08).
            self.commit_hash = _hooks.save_patch_roundtrip(
                new_dict, self.path, self.original_text, force=self.force
            )
            self.saved = True
            return False
        finally:
            self._active = False

    def _added_top_level_ids(self) -> set:
        """Top-level boxes this session added: ids absent from the file as read.

        A replace_box keeps the old id (261022-ud6 WR-02), so a replaced box
        counts as existing and keeps its colours.
        """
        baseline = set()
        boxes = self._baseline.get("patcher", {}).get("boxes", [])
        for entry in boxes if isinstance(boxes, list) else []:
            box = entry.get("box") if isinstance(entry, dict) else None
            if isinstance(box, dict) and isinstance(box.get("id"), str):
                baseline.add(box["id"])
        return {box.id for box in self.patcher.boxes if box.id not in baseline}

    def current_diff(self) -> PatchDiff:
        """The diff from the file as read to the Patcher as it is now.

        Works inside the block (preview) and after exit.

        Raises:
            RuntimeError: the session was never entered.
        """
        if self._baseline is None or self.patcher is None:
            raise RuntimeError("edit session was never entered")
        return diff_patch_dicts(self._baseline, self.patcher.to_dict())


def edit_patch(path, *, force: bool = False) -> EditSession:
    """Open an edit session on an existing patch file (Q36).

    ``with edit_patch(path) as p:`` edits and saves on a clean exit. Keep the
    session to read the result::

        s = edit_patch(path)
        with s as p:
            p.add_box("print")
        print(s.diff.render())
        s.saved, s.commit_hash

    ``force=True`` (passed to save_patch_roundtrip) only when the user
    confirms (CLAUDE.md Rule #7).
    """
    return EditSession(path, force=force)
