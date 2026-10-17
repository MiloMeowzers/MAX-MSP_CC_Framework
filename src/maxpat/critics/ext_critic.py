"""External code critic -- semantic review of generated C++ external code.

Catches structural issues in Min-DevKit C++ source files:
  - Missing MIN_EXTERNAL macro (required for MAX to load the external),
    or one that names no class
  - Missing #include "c74_min.h" (required header)
  - Class name or MIN_EXTERNAL argument that is not a valid C++ identifier
    (a MAX name such as ``foo~`` must become ``foo_tilde``; see
    ``ext_templates.cpp_identifier``)
  - Class/MIN_EXTERNAL name mismatch (the object class is the one deriving
    from ``object<...>``, so helper classes declared first do not count)
  - Missing inlet<>/outlet<> for message/scheduler archetypes
  - Missing sample_operator/vector_operator for DSP archetypes
  - Missing timer<> for scheduler archetypes
  - TODO comments (informational -- handlers need implementation)

Structural checks read the code with C-style comments and string contents
masked (``genexpr_parse.mask``), so a commented-out ``MIN_EXTERNAL``,
``#include`` or class never counts. Known limit: a char literal holding a
double quote (``'"'``) is not modelled; no template emits one.
"""

from __future__ import annotations

import re

from src.maxpat.critics.base import CriticResult
from src.maxpat.ext_templates import cmake_folder_name, cpp_identifier
from src.maxpat.genexpr_parse import mask


# Regex patterns for external code checks
_MIN_EXTERNAL_RE = re.compile(r"MIN_EXTERNAL\s*\(\s*([^)]*?)\s*\)")
_INCLUDE_C74_RE = re.compile(r'#include\s+[<"]c74_min\.h[>"]')
_OBJECT_CLASS_RE = re.compile(
    r"\bclass\s+([^\s:{;<>,()]+)\s*:\s*public\s+object\s*<"
)
_CLASS_DECL_RE = re.compile(r"\bclass\s+([^\s:{;<>,()]+)\s*:")
_VALID_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_INLET_RE = re.compile(r"inlet<[^>]*>")
_OUTLET_RE = re.compile(r"outlet<[^>]*>")
_SAMPLE_OPERATOR_RE = re.compile(r"sample_operator|vector_operator")
_TIMER_RE = re.compile(r"timer<[^>]*>")
_TODO_RE = re.compile(r"//\s*TODO\b[^\n]*|/\*.*?TODO\b.*?\*/", re.DOTALL)


def review_external(
    code_str: str,
    archetype: str = "message",
) -> list[CriticResult]:
    """Review C++ external source code for structural issues.

    Checks for required includes, macros, and archetype-specific patterns.

    Args:
        code_str: Complete C++ source code string.
        archetype: One of "message", "dsp", "scheduler".

    Returns:
        List of CriticResult findings.
    """
    results: list[CriticResult] = []
    masked = mask(code_str)

    # Check 1: #include "c74_min.h" -- searched on the raw code (the mask
    # blanks the header name) but only a match whose '#' survives the mask,
    # i.e. one outside a comment, counts.
    has_include = any(
        masked[m.start()] == "#" for m in _INCLUDE_C74_RE.finditer(code_str)
    )
    if not has_include:
        results.append(CriticResult(
            "blocker",
            'Missing #include "c74_min.h" -- required Min-DevKit header',
            'Add #include "c74_min.h" at the top of the source file',
            rule="ext_missing_include",
        ))

    # Check 2: MIN_EXTERNAL macro (on the mask)
    min_ext_match = _MIN_EXTERNAL_RE.search(masked)
    ext_class_name = ""
    if not min_ext_match:
        results.append(CriticResult(
            "blocker",
            "Missing MIN_EXTERNAL() macro -- MAX cannot load the external "
            "without this registration",
            "Add MIN_EXTERNAL(ClassName) at the end of the source file",
            rule="ext_missing_min_external",
        ))
    else:
        ext_class_name = min_ext_match.group(1).strip()
        if not ext_class_name:
            results.append(CriticResult(
                "blocker",
                "MIN_EXTERNAL() names no class -- MAX cannot load the external",
                "Pass the object class: MIN_EXTERNAL(ClassName)",
                rule="ext_min_external_no_class",
            ))

    # Check 3: the object class (the one deriving from object<...>, else the
    # first class with a base list), identifier validity, and name match.
    class_match = _OBJECT_CLASS_RE.search(masked) or _CLASS_DECL_RE.search(masked)
    declared_class = class_match.group(1) if class_match else ""

    sites: dict[str, list[str]] = {}
    if declared_class:
        sites.setdefault(declared_class, []).append("class declaration")
    if ext_class_name:
        sites.setdefault(ext_class_name, []).append("MIN_EXTERNAL")
    for tok, where in sites.items():
        if not _VALID_IDENT_RE.match(tok):
            results.append(CriticResult(
                "blocker",
                f"'{tok}' is not a valid C++ identifier ({' and '.join(where)})",
                f"Use '{cpp_identifier(tok)}' in both places -- a MAX name's "
                f"'~' maps to '_tilde', and min-api's CMake builds the folder "
                f"'{cmake_folder_name(tok)}' as the '~' external",
                rule="ext_invalid_identifier",
            ))

    if declared_class and ext_class_name and declared_class != ext_class_name:
        results.append(CriticResult(
            "blocker",
            f"MIN_EXTERNAL({ext_class_name}) does not match "
            f"class declaration '{declared_class}'",
            f"Change MIN_EXTERNAL to MIN_EXTERNAL({declared_class}) "
            f"or rename the class to '{ext_class_name}'",
            rule="ext_class_mismatch",
        ))

    # Check 4: Inlet presence for message/scheduler archetypes (on the mask)
    if archetype in ("message", "scheduler"):
        if not _INLET_RE.search(masked):
            results.append(CriticResult(
                "warning",
                f"No inlet<> found for {archetype} archetype -- "
                f"external will have no input",
                "Add at least one inlet<> declaration to the class",
                rule="ext_missing_inlet",
            ))

    # Check 5: DSP -- sample_operator or vector_operator
    if archetype == "dsp":
        if not _SAMPLE_OPERATOR_RE.search(masked):
            results.append(CriticResult(
                "blocker",
                "DSP archetype requires sample_operator or vector_operator "
                "but neither was found",
                "Add a sample_operator or vector_operator method to process "
                "audio samples",
                rule="ext_missing_dsp_operator",
            ))

    # Check 6: Scheduler -- timer<>
    if archetype == "scheduler":
        if not _TIMER_RE.search(masked):
            results.append(CriticResult(
                "blocker",
                "Scheduler archetype requires timer<> but none was found",
                "Add a timer<> member to drive scheduled events",
                rule="ext_missing_timer",
            ))

    # Check 7: TODO comments (informational; raw code -- they live in comments)
    todo_matches = _TODO_RE.findall(code_str)
    if todo_matches:
        todo_summary = "; ".join(
            m.strip().lstrip("/ ").lstrip("*").strip()[:60]
            for m in todo_matches[:5]  # cap at 5
        )
        results.append(CriticResult(
            "note",
            f"Found {len(todo_matches)} TODO comment(s): {todo_summary}",
            "Implement the TODO items before using the external",
            rule="ext_todo",
        ))

    return results
