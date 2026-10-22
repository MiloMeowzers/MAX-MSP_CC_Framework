"""GenExpr codebox smoke test (Q35, quick 261021-urs).

``python -m src.maxpat.dsp_sim smoke <file.gendsp|file.maxpat>`` runs every
gen~ codebox in the file through the offline interpreter
(:mod:`src.maxpat.dsp_sim.genexpr_interp`) at the Param corners and reports
broken or unstable behaviour before MAX opens the patch.

* Corners (D-02): the default run, then one run per Param at its declared min
  and one at its declared max, with the other Params at default.
* Stimulus (D-03, D-06): every inlet gets a 0.25 impulse plus seeded +-0.1
  noise for the first half of the run, then zeros. ``--input K=SPEC``
  replaces one inlet's signal for the whole run.
* Checks: NaN/inf, peak > 4, permanent silence after excitation and
  self-sustain are FAIL; DC offset and an all-silent output are WARN.
* Unsupported never passes (D-04): unsupported constructs, unknown names,
  non-codebox gen operators and interpreter errors give the verdict
  ``unsupported``.

Advisory only: nothing in the save path imports this module (D-07).
See src/maxpat/dsp_sim/README.md for the full contract.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from src.maxpat.dsp_sim.genexpr_interp import Unsupported, parse_codebox

__all__ = [
    "CodeboxEntry",
    "CodeboxResult",
    "Finding",
    "discover_codeboxes",
    "parse_input_spec",
    "smoke_codebox",
    "smoke_file",
    "smoke_main",
]


# ===========================================================================
# Constants
# ===========================================================================

# Stimulus
IMPULSE = 0.25            # impulse at n = 0 on every default inlet
NOISE_AMP = 0.1           # uniform +-NOISE_AMP noise over the driven half
DRIVE_FRACTION = 0.5      # fraction of the run the default stimulus is active
SUSTAIN_SCALE = 0.01      # self-sustain rerun stimulus scale

# Checks
PEAK_LIMIT = 4.0          # FAIL above this absolute peak
SILENCE_FLOOR = 1e-9      # tail max below this after activity = silence FAIL
ACTIVITY_FLOOR = 1e-6     # "the output did something" threshold
DC_DRIVEN_LIMIT = 0.1     # |mean| over the driven window -> dc WARN
DC_TAIL_LIMIT = 0.05      # |mean| of the ring-out tail -> dc latch WARN
SUSTAIN_ABS = 0.01        # small-run tail detrended RMS floor for self_sustain
SUSTAIN_RATIO = 0.5       # small/nominal tail ratio above this = self_sustain
TAIL_FRACTION = 0.1       # tail = last 10% of a window

# Run limits
MAX_SECONDS = 60.0
MIN_SAMPLERATE = 1000.0
MAX_SAMPLERATE = 384000.0

_DEFAULT_SPEC = ("impulse+noise", 0.0)


# ===========================================================================
# Records
# ===========================================================================


@dataclass
class Finding:
    """One check result. ``output`` is 1-based; 0 means the whole codebox."""

    check: str        # nonfinite | peak | silence | silent | dc | self_sustain |
                      # constant_assign | tab_char | output_typo | unused_input |
                      # unsupported (an error at one corner, or "all corners")
    severity: str     # fail | warn | unsupported
    corner: str
    output: int
    detail: str


@dataclass
class CodeboxEntry:
    label: str
    code: str
    status: str       # ok | unsupported | skipped
    reason: str = ""


@dataclass
class CodeboxResult:
    label: str
    verdict: str      # pass | fail | unsupported | skipped
    reason: str
    corners: int
    findings: list = field(default_factory=list)


@dataclass
class _Run:
    corner: str
    params: dict
    outputs: list
    driven: tuple            # (start, stop)
    ring: tuple | None       # (start, stop) or None when ring-out is off


# ===========================================================================
# Discovery
# ===========================================================================

_PLUMBING_RE = re.compile(r"^(in|out)\s+\d+(\s|$)")


def _box_text(box: dict) -> str:
    return str(box.get("text", "") or "").strip()


def _gen_patcher_entries(patcher: dict, prefix: str) -> list:
    """Entries for one gen patcher (a .gendsp top level or an embedded gen~)."""
    codes: list = []
    foreign: list = []
    for entry in patcher.get("boxes", []) or []:
        box = entry.get("box", {}) if isinstance(entry, dict) else {}
        mc = box.get("maxclass")
        if mc == "codebox":
            codes.append(box.get("code", "") or "")
            continue
        if mc in ("comment", "panel"):
            continue
        text = _box_text(box)
        if mc == "newobj" and _PLUMBING_RE.match(text):
            continue
        foreign.append(text or str(mc))
    if foreign:
        return [CodeboxEntry(
            prefix, "", "unsupported",
            "non-codebox gen operators: " + ", ".join(foreign[:5]),
        )]
    if not codes:
        return [CodeboxEntry(prefix, "", "unsupported", "no codebox")]
    return [
        CodeboxEntry(f"{prefix} > codebox {k}", code, "ok")
        for k, code in enumerate(codes, 1)
    ]


def _read_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read {path}: {exc}") from None
    if not isinstance(data, dict) or not isinstance(data.get("patcher"), dict):
        raise ValueError(f"{path} has no top-level patcher")
    return data


_MAX_DEPTH = 32
_GEN_OBJECTS = ("gen~", "mc.gen~")
_SKIP_OBJECTS = ("jit.gen", "jit.pix", "jit.gl.pix")


def _external_name(tokens: list):
    """The .gendsp name of an external gen~ box: the value after @gen, else
    the first token after the object name that does not start with '@'."""
    if "@gen" in tokens:
        i = tokens.index("@gen")
        return tokens[i + 1] if i + 1 < len(tokens) else None
    for tok in tokens[1:]:
        if tok.startswith("@"):
            return None
        return tok
    return None


def _external_entries(maxpat: Path, label: str, tokens: list) -> list:
    name = _external_name(tokens)
    if not name:
        return [CodeboxEntry(
            label, "", "unsupported", "gen~ without embedded patcher or file name"
        )]
    if "/" in name or "\\" in name or ".." in name:
        return [CodeboxEntry(
            label, "", "unsupported",
            f"external gendsp name is not a plain file name: {name!r}",
        )]
    fname = name if name.endswith(".gendsp") else f"{name}.gendsp"
    target = maxpat.parent / fname
    if not target.is_file():
        return [CodeboxEntry(
            label, "", "unsupported",
            f"external gendsp not found: {fname} (only the patch's own directory "
            "is searched)",
        )]
    try:
        data = _read_json(target)
    except ValueError as exc:
        return [CodeboxEntry(label, "", "unsupported", str(exc))]
    return _gen_patcher_entries(data["patcher"], f"{label} > {fname}")


def _walk_maxpat(patcher: dict, maxpat: Path, prefix: str, out: list, depth: int) -> None:
    if depth > _MAX_DEPTH:
        out.append(CodeboxEntry(
            prefix, "", "unsupported", f"patcher nesting deeper than {_MAX_DEPTH}"
        ))
        return
    for entry in patcher.get("boxes", []) or []:
        box = entry.get("box", {}) if isinstance(entry, dict) else {}
        inner = box.get("patcher")
        inner = inner if isinstance(inner, dict) else None
        text = _box_text(box)
        tokens = text.split()
        first = tokens[0] if tokens else ""
        if box.get("maxclass") == "newobj":
            if first in _GEN_OBJECTS:
                label = f"{prefix} > {text}"
                if inner is not None:
                    out.extend(_gen_patcher_entries(inner, label))
                else:
                    out.extend(_external_entries(maxpat, label, tokens))
                continue
            if first in _SKIP_OBJECTS and inner is not None:
                out.append(CodeboxEntry(
                    f"{prefix} > {text}", "", "skipped", f"not gen~ ({first})"
                ))
                continue
        if inner is not None:
            # p / bpatcher / poly~ with an embedded patcher: recurse.
            sub = text or str(box.get("maxclass", "patcher"))
            _walk_maxpat(inner, maxpat, f"{prefix} > {sub}", out, depth + 1)


def discover_codeboxes(path) -> list:
    """Every gen~ codebox in a .gendsp or .maxpat, as CodeboxEntry records.

    .gendsp: the top-level gen patcher. .maxpat: every gen~ / mc.gen~ newobj,
    recursively through embedded patchers (depth <= 32); an embedded gen
    patcher is used directly, otherwise ``<name>.gendsp`` is resolved in the
    patch's own directory only; jit.gen / jit.pix / jit.gl.pix are skipped.
    Raises ValueError for an unreadable file or an unsupported suffix.
    """
    p = Path(path)
    suffix = p.suffix.lower()
    if suffix not in (".gendsp", ".maxpat"):
        raise ValueError(f"{p}: expected a .gendsp or .maxpat file")
    data = _read_json(p)
    if suffix == ".gendsp":
        return _gen_patcher_entries(data["patcher"], p.name)
    out: list = []
    _walk_maxpat(data["patcher"], p, p.name, out, 0)
    # Two identical gen~ boxes in one patcher would share a label: number
    # the repeats so every report line names exactly one codebox.
    seen: dict = {}
    for e in out:
        seen[e.label] = seen.get(e.label, 0) + 1
        if seen[e.label] > 1:
            e.label = f"{e.label} (#{seen[e.label]})"
    return out


# ===========================================================================
# Stimulus
# ===========================================================================

_SPEC_RE = re.compile(r"^(const|dc|phasor|sine):(.+)$")


def parse_input_spec(spec: str) -> tuple:
    """Parse an inlet SPEC into (kind, value). Raises ValueError when malformed.

    Forms: ``impulse+noise`` (default), ``zero``, ``const:V`` (``dc:V`` is an
    alias), ``phasor:HZ`` (0..1 ramp), ``sine:HZ`` (amplitude 0.25).
    """
    s = str(spec).strip()
    if s == "impulse+noise":
        return _DEFAULT_SPEC
    if s == "zero":
        return ("zero", 0.0)
    m = _SPEC_RE.match(s)
    if not m:
        raise ValueError(
            f"bad input spec {spec!r}: use impulse+noise, zero, const:V, dc:V, "
            "phasor:HZ or sine:HZ"
        )
    kind = "const" if m.group(1) == "dc" else m.group(1)
    try:
        value = float(m.group(2))
    except ValueError:
        raise ValueError(f"bad input spec {spec!r}: {m.group(2)!r} is not a number") from None
    if not np.isfinite(value):
        raise ValueError(f"bad input spec {spec!r}: value must be finite")
    return (kind, value)


def _signal(spec: tuple, k: int, n: int, samplerate: float, seed: int, scale: float = 1.0):
    kind, value = spec
    if kind == "impulse+noise":
        x = np.zeros(n)
        nd = int(n * DRIVE_FRACTION)
        rng = np.random.default_rng((seed, k))
        x[:nd] = rng.uniform(-NOISE_AMP, NOISE_AMP, nd)
        x[0] += IMPULSE
        return x * scale
    if kind == "zero":
        return np.zeros(n)
    if kind == "const":
        return np.full(n, value)
    t = np.arange(n) / samplerate
    if kind == "phasor":
        return np.mod(t * value, 1.0)
    if kind == "sine":
        return 0.25 * np.sin(2.0 * np.pi * value * t)
    raise ValueError(f"unknown input kind {kind!r}")


# ===========================================================================
# Corners
# ===========================================================================


def _corners(params: list, mode: str) -> list:
    out = [("default", {})]
    if mode == "default":
        return out
    for p in params:
        name, default = p["name"], p["default"]
        for side in ("min", "max"):
            v = p.get(side)
            if v is None or v == default:
                continue
            out.append((f"{name}={side} ({v:g})", {name: v}))
    return out


# ===========================================================================
# Checks
# ===========================================================================


def _driven_checks(run: _Run, samplerate: float, full: bool = True,
                   excited: bool = True) -> tuple:
    """Driven-window checks on one run. Returns (findings, finite_outputs).

    ``full=False`` runs only the nonfinite and peak checks (the self-sustain
    small run). ``excited=False`` skips the permanent-silence check (WR-05):
    no inlet still changes over the tail of the driven window, so an output
    that decays there (a 0-inlet decay, a const-driven DC blocker, a finished
    one-shot player) is correct."""
    findings: list = []
    finite: list = []
    d0, d1 = run.driven
    for k, y in enumerate(run.outputs, 1):
        bad = ~np.isfinite(y)
        if bad.any():
            i = int(np.argmax(bad))
            findings.append(Finding(
                "nonfinite", "fail", run.corner, k,
                f"non-finite sample {float(y[i])!r} at n={i} ({i / samplerate:.4f} s)",
            ))
            continue
        finite.append(k)
        a = np.abs(y)
        pk = float(a.max()) if a.size else 0.0
        if pk > PEAK_LIMIT:
            i = int(np.argmax(a))
            findings.append(Finding(
                "peak", "fail", run.corner, k,
                f"peak {pk:.4g} > {PEAK_LIMIT:g} at n={i} ({i / samplerate:.4f} s)",
            ))
        if not full:
            continue
        if pk <= ACTIVITY_FLOOR:
            findings.append(Finding(
                "silent", "warn", run.corner, k,
                f"output never exceeds {ACTIVITY_FLOOR:g} (max {pk:.3g})",
            ))
            continue
        d = y[d0:d1]
        if d.size >= 2:
            tail_n = max(1, int(d.size * TAIL_FRACTION))
            early = np.abs(d[:-tail_n])
            tail = np.abs(d[-tail_n:])
            if (excited and early.size and early.max() > ACTIVITY_FLOOR
                    and tail.max() < SILENCE_FLOOR):
                findings.append(Finding(
                    "silence", "fail", run.corner, k,
                    "permanent silence after excitation: last "
                    f"{tail_n / samplerate:.3f} s of the driven window below "
                    f"{SILENCE_FLOOR:g} while an input is still changing",
                ))
            mean = float(np.mean(d))
            if abs(mean) > DC_DRIVEN_LIMIT:
                findings.append(Finding(
                    "dc", "warn", run.corner, k,
                    f"mean {mean:+.4g} over the driven window (|mean| > {DC_DRIVEN_LIMIT:g})",
                ))
    return findings, finite


def _tail(y: np.ndarray, ring: tuple) -> np.ndarray:
    r0, r1 = ring
    tail_n = max(2, int((r1 - r0) * TAIL_FRACTION))
    return y[r1 - tail_n:r1]


def _detrended_rms(y: np.ndarray) -> float:
    """RMS after removing a least-squares line (np.polyfit degree 1)."""
    if y.size < 2:
        return 0.0
    x = np.arange(y.size, dtype=float)
    x -= x.mean()
    slope, intercept = np.polyfit(x, y, 1)
    r = y - (slope * x + intercept)
    return float(np.sqrt(np.mean(r * r)))


def _ringout_checks(run: _Run, small_outputs: list, finite: list, samplerate: float) -> list:
    """dc latch (WARN) and self_sustain (FAIL, D-05) on the ring-out window."""
    findings: list = []
    r0, r1 = run.ring
    for k in finite:
        y = run.outputs[k - 1]
        tail = _tail(y, run.ring)
        mean = float(np.mean(tail))
        if abs(mean) > DC_TAIL_LIMIT:
            findings.append(Finding(
                "dc", "warn", run.corner, k,
                f"dc latch: mean {mean:+.4g} over the last {tail.size / samplerate:.3f} s "
                f"of the ring-out (|mean| > {DC_TAIL_LIMIT:g})",
            ))
        ys = small_outputs[k - 1]
        if not np.all(np.isfinite(ys)):
            continue
        nom = _detrended_rms(tail)
        small = _detrended_rms(_tail(ys, run.ring))
        if small > SUSTAIN_ABS and small / max(nom, 1e-12) > SUSTAIN_RATIO:
            findings.append(Finding(
                "self_sustain", "fail", run.corner, k,
                f"sustains with zero input (small {small:.3g} at {SUSTAIN_SCALE:g}x vs "
                f"{nom:.3g} at 1x): self-oscillation, latched feedback or a generator "
                "with an inlet; --no-ringout skips this check",
            ))
    return findings


# ===========================================================================
# Smoke one codebox
# ===========================================================================


def _validate_run_args(seconds, samplerate) -> int:
    seconds = float(seconds)
    samplerate = float(samplerate)
    if not (0.0 < seconds <= MAX_SECONDS):
        raise ValueError(f"seconds must be in (0, {MAX_SECONDS:g}], got {seconds:g}")
    if not (MIN_SAMPLERATE <= samplerate <= MAX_SAMPLERATE):
        raise ValueError(
            f"samplerate must be in [{MIN_SAMPLERATE:g}, {MAX_SAMPLERATE:g}], got {samplerate:g}"
        )
    return max(2, int(round(seconds * samplerate)))


def smoke_codebox(
    code: str,
    *,
    label: str = "codebox",
    seconds: float = 1.0,
    samplerate: float = 44100.0,
    inputs: dict | None = None,
    buffers: dict | None = None,
    corners: str = "all",
    seed: int = 1,
    ringout: bool = True,
) -> CodeboxResult:
    """Smoke one codebox at every corner and return its verdict.

    ``inputs`` maps a 1-based inlet to a SPEC string (a key beyond the
    codebox's inlet count is not applied and gives an ``unused_input`` WARN).
    An error at one corner is an ``unsupported`` finding at that corner; the
    other corners still run, so a FAIL is never lost. Raises ValueError on
    bad arguments.
    """
    n = _validate_run_args(seconds, samplerate)
    samplerate = float(samplerate)
    if corners not in ("all", "default"):
        raise ValueError(f"corners must be 'all' or 'default', got {corners!r}")
    raw_inputs = dict(inputs or {})
    parsed_inputs = {int(k): parse_input_spec(v) for k, v in raw_inputs.items()}

    try:
        cb = parse_codebox(code)
    except Unsupported as exc:
        return CodeboxResult(label, "unsupported", str(exc), 0, [])
    except Exception as exc:  # never pass on an interpreter error
        return CodeboxResult(
            label, "unsupported", f"interpreter error: {type(exc).__name__}: {exc}", 0, []
        )
    if cb.n_out == 0:  # CR-02: nothing would be checked, so never a pass
        return CodeboxResult(
            label, "unsupported", "codebox has no outN outputs: nothing to check", 0, []
        )

    specs = [parsed_inputs.get(k, _DEFAULT_SPEC) for k in range(1, cb.n_in + 1)]
    any_default = any(s == _DEFAULT_SPEC for s in specs)
    all_default = cb.n_in >= 1 and all(s == _DEFAULT_SPEC for s in specs)
    nd = int(n * DRIVE_FRACTION)
    # The default stimulus stops at N/2, so the driven window ends there
    # whenever an inlet carries it; fully overridden inlets drive the run.
    driven = (0, nd) if any_default else (0, n)
    ring = (nd, n) if (ringout and all_default) else None
    signals = [_signal(s, k, n, samplerate, seed) for k, s in enumerate(specs, 1)]
    # WR-05: permanent silence only means something while an input still
    # changes over the tail of the driven window.
    d0, d1 = driven
    tail_n = max(1, int((d1 - d0) * TAIL_FRACTION))
    excited = cb.n_in >= 1 and any(
        float(np.ptp(sig[d1 - tail_n:d1])) > ACTIVITY_FLOOR for sig in signals
    )

    findings: list = [
        Finding("constant_assign", "warn", "build", 0, w) for w in cb.warnings
    ]
    findings.extend(Finding(check, "warn", "build", 0, detail) for check, detail in cb.lint)
    for k in sorted(parsed_inputs):  # WR-06
        if k > cb.n_in:
            raw = next(v for kk, v in raw_inputs.items() if int(kk) == k)
            findings.append(Finding(
                "unused_input", "warn", "build", 0,
                f"--input {k}={raw} not applied: this codebox has {cb.n_in} inlet(s)",
            ))

    corner_list = _corners(cb.params, corners)
    errors: list = []   # (finding, legacy reason text), one per errored corner
    for corner, cparams in corner_list:
        try:
            prog = cb.build(params=cparams, samplerate=samplerate, seed=seed, buffers=buffers)
            outs = prog.run(signals, n)
            run = _Run(corner, cparams, outs, driven, ring)
            f, finite = _driven_checks(run, samplerate, excited=excited)
            findings.extend(f)
            if ring is None:
                continue
            # Self-sustain rerun (D-05): fresh Program, every inlet's default
            # stimulus x SUSTAIN_SCALE, same seeds.
            small_prog = cb.build(
                params=cparams, samplerate=samplerate, seed=seed, buffers=buffers
            )
            small_outs = small_prog.run([x * SUSTAIN_SCALE for x in signals], n)
            small_run = _Run(
                f"{corner} @{SUSTAIN_SCALE:g}x", cparams, small_outs, driven, ring
            )
            f_small, _ = _driven_checks(small_run, samplerate, full=False)
            findings.extend(f_small)
            findings.extend(_ringout_checks(run, small_outs, finite, samplerate))
        except Unsupported as exc:  # WR-01: record per corner, keep earlier findings
            legacy = str(exc)
            detail = legacy[len("unsupported: "):] if legacy.startswith("unsupported: ") else legacy
            errors.append((Finding("unsupported", "unsupported", corner, 0, detail), legacy))
        except Exception as exc:  # never pass on an interpreter error
            legacy = f"interpreter error: {type(exc).__name__}: {exc}"
            errors.append((Finding("unsupported", "unsupported", corner, 0, legacy), legacy))

    n_corners = len(corner_list)
    completed = n_corners - len(errors)
    if errors and len(errors) == n_corners and len({f.detail for f, _ in errors}) == 1:
        findings.append(Finding("unsupported", "unsupported", "all corners", 0, errors[0][0].detail))
    else:
        findings.extend(f for f, _ in errors)

    n_fail = sum(1 for f in findings if f.severity == "fail")
    if n_fail:
        reason = f"{n_fail} failing check(s)"
        if errors:
            reason += f"; unsupported at {len(errors)} corner(s)"
        return CodeboxResult(label, "fail", reason, completed, findings)
    if errors:
        reason = errors[0][1]
        if len(errors) < n_corners:
            reason += f" ({len(errors)} of {n_corners} corners)"
        return CodeboxResult(label, "unsupported", reason, completed, findings)
    return CodeboxResult(label, "pass", "", completed, findings)


def smoke_file(path, **kwargs) -> list:
    """Smoke every codebox in ``path``. Skipped and unsupported discovery
    entries pass through as results. Raises ValueError on a read error."""
    results: list = []
    for e in discover_codeboxes(path):
        if e.status != "ok":
            results.append(CodeboxResult(e.label, e.status, e.reason, 0, []))
            continue
        results.append(smoke_codebox(e.code, label=e.label, **kwargs))
    return results


# ===========================================================================
# CLI
# ===========================================================================

_EPILOG = """\
input SPEC forms (per inlet, --input K=SPEC, repeatable):
  impulse+noise   default: 0.25 impulse at n=0 plus seeded +-0.1 noise for
                  the first half of the run, then zeros
  zero            all zeros
  const:V         constant V for the whole run (dc:V is an alias)
  phasor:HZ       0..1 ramp at HZ, e.g. --input 1=phasor:2
  sine:HZ         sine at HZ, amplitude 0.25
An overridden inlet holds its signal for the whole run. The ring-out checks
(self_sustain, dc latch) run only when every inlet is on the default
stimulus.

Buffer backing: MAX's buffer~ contents are not available offline; each
Buffer is 48000 frames x 1 channel of a 0.25 220 Hz sine unless resized with
--buffer NAME=FRAMES[:CHANS]. Data is zero-filled.

exit codes: 0 every codebox passed (warnings allowed), 1 any FAIL,
2 usage or read error, 3 any unsupported codebox (and no FAIL) or nothing
to smoke.
"""


def _seconds_arg(text: str) -> float:
    try:
        v = float(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a number: {text!r}") from None
    if not (0.0 < v <= MAX_SECONDS):
        raise argparse.ArgumentTypeError(f"must be in (0, {MAX_SECONDS:g}]")
    return v


def _samplerate_arg(text: str) -> float:
    try:
        v = float(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a number: {text!r}") from None
    if not (MIN_SAMPLERATE <= v <= MAX_SAMPLERATE):
        raise argparse.ArgumentTypeError(
            f"must be in [{MIN_SAMPLERATE:g}, {MAX_SAMPLERATE:g}]"
        )
    return v


def _input_arg(text: str) -> tuple:
    key, sep, spec = text.partition("=")
    if not sep:
        raise argparse.ArgumentTypeError(f"expected K=SPEC, got {text!r}")
    try:
        k = int(key)
    except ValueError:
        raise argparse.ArgumentTypeError(f"inlet {key!r} is not an integer") from None
    if k < 1:
        raise argparse.ArgumentTypeError("inlet numbers start at 1")
    try:
        parse_input_spec(spec)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from None
    return (k, spec)


def _buffer_arg(text: str) -> tuple:
    from src.maxpat.dsp_sim.genexpr_interp import STATE_CAP

    name, sep, size = text.partition("=")
    if not sep or not name.strip():
        raise argparse.ArgumentTypeError(f"expected NAME=FRAMES[:CHANS], got {text!r}")
    frames_s, _c, chans_s = size.partition(":")
    try:
        frames = int(frames_s)
        chans = int(chans_s) if chans_s else 1
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"expected NAME=FRAMES[:CHANS] with integers, got {text!r}"
        ) from None
    if frames < 1 or chans < 1:
        raise argparse.ArgumentTypeError("FRAMES and CHANS must be >= 1")
    if frames * chans > STATE_CAP:
        raise argparse.ArgumentTypeError(f"FRAMES * CHANS must be <= {STATE_CAP}")
    return (name.strip(), (frames, chans))


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m src.maxpat.dsp_sim smoke",
        description=(
            "GenExpr codebox smoke test: run every gen~ codebox in a .gendsp "
            "or .maxpat at the default and per-Param min/max corners and "
            "report NaN/inf, peak > 4, permanent silence and self-sustain "
            "(FAIL) and DC offset (WARN). Unsupported constructs never pass. "
            "Advisory: not a save gate."
        ),
        epilog=_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("path", help="a .gendsp or .maxpat file")
    p.add_argument("--seconds", type=_seconds_arg, default=1.0,
                   help="seconds per corner run (default 1.0, max 60)")
    p.add_argument("--samplerate", type=_samplerate_arg, default=44100.0,
                   help="sample rate in Hz (default 44100)")
    p.add_argument("--seed", type=int, default=1,
                   help="stimulus and noise() seed (default 1)")
    p.add_argument("--corners", choices=("all", "default"), default="all",
                   help="all = default + each Param at min and max (default); "
                        "default = the default run only")
    p.add_argument("--no-ringout", action="store_true",
                   help="skip the ring-out checks (self_sustain, dc latch)")
    p.add_argument("--input", dest="inputs", action="append", type=_input_arg,
                   default=[], metavar="K=SPEC",
                   help="override inlet K's stimulus, e.g. --input 1=phasor:2 "
                        "or --input 1=const:220 (see SPEC forms below)")
    p.add_argument("--buffer", dest="buffers", action="append", type=_buffer_arg,
                   default=[], metavar="NAME=FRAMES[:CHANS]",
                   help="size the Buffer bound to buffer~ NAME (default 48000:1, "
                        "a 0.25 220 Hz sine), e.g. --buffer bufname=1000:2")
    p.add_argument("--json", action="store_true",
                   help="print the report as one JSON object")
    return p


def _exit_code(results: list) -> int:
    if any(r.verdict == "fail" for r in results):
        return 1
    smoked = [r for r in results if r.verdict == "pass"]
    if any(r.verdict == "unsupported" for r in results) or not smoked:
        return 3
    return 0


def _format_text(path, args, results: list, code: int) -> str:
    lines = [
        f"smoke {path}: seconds={args.seconds:g} samplerate={args.samplerate:g} "
        f"seed={args.seed} corners={args.corners}"
    ]
    for r in results:
        head = f"{r.label}: {r.verdict.upper()} ({r.corners} corners)"
        if r.reason:
            head += f": {r.reason}"
        lines.append(head)
        for f in r.findings:
            where = f"out{f.output}" if f.output else "codebox"
            if f.severity == "unsupported":
                lines.append(f"  UNSUPPORTED [{f.corner}] {where}: {f.detail}")
            else:
                lines.append(f"  {f.severity.upper()} {f.check} [{f.corner}] {where}: {f.detail}")
    counts = {v: sum(1 for r in results if r.verdict == v)
              for v in ("pass", "fail", "unsupported", "skipped")}
    warns = sum(1 for r in results for f in r.findings if f.severity == "warn")
    lines.append(
        f"summary: {len(results)} codebox(es): {counts['pass']} pass, "
        f"{counts['fail']} fail, {counts['unsupported']} unsupported, "
        f"{counts['skipped']} skipped, {warns} warning(s); exit {code}"
    )
    return "\n".join(lines)


def _report_dict(path, args, results: list, code: int) -> dict:
    return {
        "path": str(path),
        "seconds": args.seconds,
        "samplerate": args.samplerate,
        "seed": args.seed,
        "corners": args.corners,
        "exit_code": code,
        "codeboxes": [
            {
                "label": r.label,
                "verdict": r.verdict,
                "reason": r.reason,
                "corners": r.corners,
                "findings": [
                    {
                        "check": f.check,
                        "severity": f.severity,
                        "corner": f.corner,
                        "output": f.output,
                        "detail": f.detail,
                    }
                    for f in r.findings
                ],
            }
            for r in results
        ],
    }


def smoke_main(argv=None) -> int:
    """Entry point for ``python -m src.maxpat.dsp_sim smoke``. Returns the exit code."""
    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 2
    inputs = {k: spec for k, spec in args.inputs}
    try:
        results = smoke_file(
            args.path,
            seconds=args.seconds,
            samplerate=args.samplerate,
            inputs=inputs,
            corners=args.corners,
            seed=args.seed,
            ringout=not args.no_ringout,
            buffers=dict(args.buffers),
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    code = _exit_code(results)
    if args.json:
        print(json.dumps(_report_dict(args.path, args, results, code), indent=2))
    else:
        print(_format_text(args.path, args, results, code))
    return code
