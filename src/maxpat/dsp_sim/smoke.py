"""GenExpr codebox smoke test (Q35, quick 261021-urs; ports 261022-ud6).

``python -m src.maxpat.dsp_sim smoke <file.gendsp|file.maxpat>`` runs every
gen~ codebox in the file through the offline interpreter
(:mod:`src.maxpat.dsp_sim.genexpr_interp`) at the Param corners and reports
broken or unstable behaviour before MAX opens the patch.

* Corners (D-02): the default run, then one run per Param at its declared min
  and one at its declared max, with the other Params at default.
* Ports (261022-ud6 CR-01): each outlet is ``audio`` or ``control`` and each
  inlet ``audio``, ``control``, ``trigger`` or ``zero``, inferred from the
  host patch graph (:mod:`src.maxpat.dsp_sim.host_graph`). A standalone
  .gendsp with no host in its directory is all audio. ``// smoke:``
  directives in the codebox override both (see ``parse_directives``).
* Stimulus (D-03, D-06): audio and control inlets get a 0.25 impulse plus
  seeded +-0.1 noise for the first half of the run, then zeros; trigger
  inlets get two gate pulses; zero inlets get zeros. ``--input K=SPEC``
  replaces one inlet's signal for the whole run.
* Checks: NaN/inf is FAIL on every output. On audio outputs peak > 4,
  permanent silence while an audio input still changes (unless a loud rerun
  stays active: then WARN, WR-03) and self-sustain are FAIL; DC offset and
  an all-silent output are WARN. Control outputs get only NaN/inf and the
  denormal WARN. Build lints (tab_char, output_typo, loop_bound_param,
  hoist_alias, implicit_channel), unused_input and smoke_directive are WARN;
  branch_state is an INFO advisory that never changes the verdict.
* Unsupported never passes (D-04): unsupported constructs, unknown names,
  locals read before they are assigned, non-codebox gen operators, a codebox
  with no outN and interpreter errors give the verdict ``unsupported``. An
  error at one corner is recorded at that corner; a FAIL elsewhere still wins.

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
from src.maxpat.dsp_sim.host_graph import (
    AUDIO,
    CONTROL,
    TRIGGER,
    ZERO,
    HostGraph,
    PortKinds,
    external_gendsp_name,
    gen_port_map,
)
from src.maxpat.genexpr_parse import io_counts

__all__ = [
    "CodeboxEntry",
    "CodeboxResult",
    "Finding",
    "PortKinds",
    "discover_codeboxes",
    "parse_directives",
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
GATE_FRACTION = 0.02      # trigger inlets: two gates this long (x driven window)
LOUD_NOISE_AMP = IMPULSE  # WR-03 silence rerun: noise as loud as the impulse

# Checks
PEAK_LIMIT = 4.0          # FAIL above this absolute peak
SILENCE_FLOOR = 1e-9      # tail max below this after activity = silence FAIL
ACTIVITY_FLOOR = 1e-6     # "the output did something" threshold
DC_DRIVEN_LIMIT = 0.1     # |mean| over the driven window -> dc WARN
DC_TAIL_LIMIT = 0.05      # |mean| of the ring-out tail -> dc latch WARN
SUSTAIN_ABS = 0.01        # small-run tail detrended RMS floor for self_sustain
SUSTAIN_RATIO = 0.5       # small/nominal tail ratio above this = self_sustain
TAIL_FRACTION = 0.1       # tail = last 10% of a window
DENORMAL_MAX = sys.float_info.min   # 0 < |x| < this is a subnormal double

# Run limits
MAX_SECONDS = 60.0
MIN_SAMPLERATE = 1000.0
MAX_SAMPLERATE = 384000.0

_DEFAULT_SPEC = ("impulse+noise", 0.0)
_GATE_SPEC = ("gate", 0.0)
_ZERO_SPEC = ("zero", 0.0)
# Specs that are silent over the ring-out (second) half of the run.
_QUIET_SPECS = (_DEFAULT_SPEC, _GATE_SPEC, _ZERO_SPEC)
_KIND_SPEC = {AUDIO: _DEFAULT_SPEC, CONTROL: _DEFAULT_SPEC, TRIGGER: _GATE_SPEC, ZERO: _ZERO_SPEC}


# ===========================================================================
# Records
# ===========================================================================


@dataclass
class Finding:
    """One check result. ``output`` is 1-based; 0 means the whole codebox."""

    check: str        # nonfinite | peak | silence | silent | dc | self_sustain |
                      # denormal | constant_assign | tab_char | output_typo |
                      # loop_bound_param | hoist_alias | implicit_channel |
                      # unused_input | smoke_directive |
                      # unsupported (an error at one corner, or "all corners") |
                      # branch_state (INFO: stateful call inside an if/else body)
    severity: str     # fail | warn | unsupported | info
    corner: str
    output: int
    detail: str


@dataclass
class CodeboxEntry:
    label: str
    code: str
    status: str       # ok | unsupported | skipped
    reason: str = ""
    ports: PortKinds | None = None   # host-inferred port kinds (None: no host)


@dataclass
class CodeboxResult:
    label: str
    verdict: str      # pass | fail | unsupported | skipped
    reason: str
    corners: int
    findings: list = field(default_factory=list)
    inputs: dict = field(default_factory=dict)       # inN -> audio|control|trigger|zero
    outputs: dict = field(default_factory=dict)      # outN -> audio|control
    port_notes: dict = field(default_factory=dict)   # "in1"/"out2" -> evidence
    port_host: str = ""                               # where the kinds came from


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


def _merge_ports(per_host: list, n_in: int, n_out: int) -> PortKinds:
    """One PortKinds from several hosts: an output is audio when any host
    makes it audio; an inlet takes its strongest kind (audio > trigger >
    control), and is zero only when it is zero in every host."""
    rank = {AUDIO: 3, TRIGGER: 2, CONTROL: 1, ZERO: 0}
    merged = PortKinds(host=", ".join(dict.fromkeys(pk.host for pk in per_host)))
    for k in range(1, n_out + 1):
        best = max(per_host, key=lambda pk: pk.outputs.get(k) == AUDIO)
        merged.outputs[k] = best.outputs.get(k, CONTROL)
        merged.notes[f"out{k}"] = best.notes.get(f"out{k}", "")
    for k in range(1, n_in + 1):
        best = max(per_host, key=lambda pk: rank[pk.inputs.get(k, ZERO)])
        merged.inputs[k] = best.inputs.get(k, ZERO)
        merged.notes[f"in{k}"] = best.notes.get(f"in{k}", "")
    return merged


def _ports_for(code_box_id, code: str, gen_patcher: dict, hosts: list):
    """PortKinds for one codebox from its gen~ box(es) in host patches.

    ``hosts`` holds (graph, scope, box id) for every gen~ / mc.gen~ box that
    runs this gen patcher. Returns None when there is no host."""
    if not hosts:
        return None
    n_in, n_out = io_counts(code)
    in_map, out_map = gen_port_map(gen_patcher, code_box_id)
    per_host: list = []
    for graph, scope, bid in hosts:
        pk = PortKinds(host=scope.fidx.path.name)
        for k in range(1, n_out + 1):
            outs = out_map.get(k)
            if not outs:
                pk.outputs[k], pk.notes[f"out{k}"] = CONTROL, "codebox outlet not wired to an out object"
                continue
            kinds = [graph.outlet_kind(scope, bid, o) for o in outs]
            audio = [ev for kd, ev in kinds if kd == AUDIO]
            pk.outputs[k] = AUDIO if audio else CONTROL
            pk.notes[f"out{k}"] = audio[0] if audio else kinds[0][1]
        for k in range(1, n_in + 1):
            if k not in in_map:
                pk.inputs[k], pk.notes[f"in{k}"] = ZERO, "codebox inlet not wired to an in object"
                continue
            pk.inputs[k], pk.notes[f"in{k}"] = graph.inlet_kind(scope, bid, in_map[k])
        per_host.append(pk)
    if len(per_host) == 1:
        return per_host[0]
    return _merge_ports(per_host, n_in, n_out)


def _gen_patcher_entries(patcher: dict, prefix: str, hosts: list = ()) -> list:
    """Entries for one gen patcher (a .gendsp top level or an embedded gen~)."""
    codes: list = []
    foreign: list = []
    for entry in patcher.get("boxes", []) or []:
        box = entry.get("box", {}) if isinstance(entry, dict) else {}
        mc = box.get("maxclass")
        if mc == "codebox":
            codes.append((box.get("id"), box.get("code", "") or ""))
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
    out: list = []
    for k, (cid, code) in enumerate(codes, 1):
        try:
            ports = _ports_for(cid, code, patcher, list(hosts))
        except Exception:   # port inference is best-effort; never block a smoke
            ports = None
        out.append(CodeboxEntry(f"{prefix} > codebox {k}", code, "ok", ports=ports))
    return out


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


def _external_entries(maxpat: Path, label: str, tokens: list, hosts: list) -> list:
    name = external_gendsp_name(tokens)
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
    return _gen_patcher_entries(data["patcher"], f"{label} > {fname}", hosts)


def _walk_scope(graph: HostGraph, sc, maxpat: Path, prefix: str, out: list) -> None:
    for bid, box in sc.boxes.items():
        inner = box.get("patcher")
        inner = inner if isinstance(inner, dict) else None
        text = _box_text(box)
        tokens = text.split()
        first = tokens[0] if tokens else ""
        if box.get("maxclass") == "newobj":
            if first in _GEN_OBJECTS:
                label = f"{prefix} > {text}"
                data = box.get("data")
                if inner is None and isinstance(data, dict) and isinstance(data.get("patcher"), dict):
                    # WR-01: MAX saves an mc.gen~ wrapper's gen patcher under
                    # box["data"]["patcher"] (with wrapper_uniquekey).
                    inner = data["patcher"]
                hosts = [(graph, sc, bid)]
                if inner is not None:
                    out.extend(_gen_patcher_entries(inner, label, hosts))
                else:
                    out.extend(_external_entries(maxpat, label, tokens, hosts))
                continue
            if first in _SKIP_OBJECTS:
                # IN-06: reported whether or not the patcher is embedded.
                out.append(CodeboxEntry(
                    f"{prefix} > {text}", "", "skipped", f"not gen~ ({first})"
                ))
                continue
        if inner is not None:
            # p / bpatcher with an embedded patcher: recurse.
            sub = text or str(box.get("maxclass", "patcher"))
            if bid in sc.children:
                _walk_scope(graph, sc.children[bid], maxpat, f"{prefix} > {sub}", out)
            else:
                out.append(CodeboxEntry(
                    f"{prefix} > {sub}", "", "unsupported",
                    f"patcher nesting deeper than {_MAX_DEPTH}",
                ))


def discover_codeboxes(path) -> list:
    """Every gen~ codebox in a .gendsp or .maxpat, as CodeboxEntry records.

    .gendsp: the top-level gen patcher; its ports come from every gen~ /
    mc.gen~ box in a sibling .maxpat that loads it by name (none: no ports,
    so every port is audio). .maxpat: every gen~ / mc.gen~ newobj,
    recursively through embedded patchers (depth <= 32); an embedded gen
    patcher (``box["patcher"]``, or ``box["data"]["patcher"]`` for a
    MAX-saved mc.gen~) is used directly, otherwise ``<name>.gendsp`` is
    resolved in the patch's own directory only; jit.gen / jit.pix /
    jit.gl.pix are reported as skipped. Each entry carries the port kinds
    inferred from the host graph. Raises ValueError for an unreadable file
    or an unsupported suffix.
    """
    p = Path(path)
    suffix = p.suffix.lower()
    if suffix not in (".gendsp", ".maxpat"):
        raise ValueError(f"{p}: expected a .gendsp or .maxpat file")
    data = _read_json(p)
    graph = HostGraph()
    if suffix == ".gendsp":
        try:
            hosts = [(graph, sc, bid) for sc, bid in graph.gen_hosts(p.resolve())]
        except Exception:   # best-effort: a broken sibling never blocks a smoke
            hosts = []
        return _gen_patcher_entries(data["patcher"], p.name, hosts)
    out: list = []
    fidx = graph.file(p)
    if fidx is None:
        raise ValueError(f"cannot index {p}")
    _walk_scope(graph, fidx.root, p, p.name, out)
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

    Forms: ``impulse+noise`` (default), ``gate`` (two gate pulses, the trigger
    stimulus), ``zero``, ``const:V`` (``dc:V`` is an alias), ``phasor:HZ``
    (0..1 ramp), ``sine:HZ`` (amplitude 0.25).
    """
    s = str(spec).strip()
    if s == "impulse+noise":
        return _DEFAULT_SPEC
    if s == "gate":
        return _GATE_SPEC
    if s == "zero":
        return _ZERO_SPEC
    m = _SPEC_RE.match(s)
    if not m:
        raise ValueError(
            f"bad input spec {spec!r}: use impulse+noise, gate, zero, const:V, dc:V, "
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


def _signal(spec: tuple, k: int, n: int, samplerate: float, seed: int,
            noise_amp: float = NOISE_AMP):
    kind, value = spec
    nd = int(n * DRIVE_FRACTION)
    if kind == "impulse+noise":
        x = np.zeros(n)
        rng = np.random.default_rng((seed, k))
        x[:nd] = rng.uniform(-NOISE_AMP, NOISE_AMP, nd) * (noise_amp / NOISE_AMP)
        x[0] += IMPULSE
        return x
    if kind == "gate":
        # Two gates in the driven half: a trigger fires twice and a gate
        # opens and closes twice; zeros after.
        x = np.zeros(n)
        g = max(1, int(nd * GATE_FRACTION))
        x[:min(g, nd)] = 1.0
        half = nd // 2
        x[half:min(half + g, nd)] = 1.0
        return x
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
# // smoke: directives (CR-01)
# ===========================================================================

_DIRECTIVE_RE = re.compile(r"//\s*smoke\s*:(.*)$", re.MULTILINE)
_PORT_RE = re.compile(r"^(in|out)(\d+)$")
_IN_SPEC_RE = re.compile(r"^in(\d+)=(\S+)$")
_OUT_WORDS = {"audio": AUDIO, "control": CONTROL}
_IN_WORDS = {"audio": AUDIO, "control": CONTROL, "trigger": TRIGGER, "gate": TRIGGER,
             "zero": ZERO}


def parse_directives(code: str, n_in: int, n_out: int) -> tuple:
    """Read ``// smoke:`` comment lines from a codebox.

    Grammar: ``// smoke: <word> <port> [<port> ...] [<word> <port> ...]``,
    where a word sets the kind of the ports that follow it:

    * outlets (``outN``): ``audio`` or ``control``;
    * inlets (``inN``): ``audio``, ``control``, ``trigger`` (alias ``gate``;
      two gate pulses) or ``zero``;
    * ``inN=SPEC`` sets inlet N's stimulus to an ``--input`` SPEC
      (``in1=phasor:2``). ``--input`` on the command line still wins.

    Example: ``// smoke: control out2 out4 trigger in1``. Returns
    (inputs, outputs, specs, problems): kind maps keyed by 1-based port, a
    {inlet: spec tuple} map, and one string per token that could not be
    applied (reported as a ``smoke_directive`` WARN).
    """
    inputs: dict = {}
    outputs: dict = {}
    specs: dict = {}
    problems: list = []
    for m in _DIRECTIVE_RE.finditer(code):
        word = None
        for tok in m.group(1).split():
            low = tok.lower()
            sm = _IN_SPEC_RE.match(tok)
            if sm:
                k = int(sm.group(1))
                if not 1 <= k <= n_in:
                    problems.append(f"'{tok}': this codebox has {n_in} inlet(s)")
                    continue
                try:
                    specs[k] = parse_input_spec(sm.group(2))
                except ValueError as exc:
                    problems.append(f"'{tok}': {exc}")
                continue
            if low in _IN_WORDS or low in _OUT_WORDS:
                word = low
                continue
            pm = _PORT_RE.match(low)
            if not pm:
                problems.append(f"'{tok}' is not a kind word (audio, control, trigger, "
                                "zero), a port (inN / outN) or inN=SPEC")
                continue
            side, k = pm.group(1), int(pm.group(2))
            if word is None:
                problems.append(f"'{tok}' has no kind word before it")
                continue
            if side == "out":
                if not 1 <= k <= n_out:
                    problems.append(f"'{tok}': this codebox has {n_out} outlet(s)")
                elif word not in _OUT_WORDS:
                    problems.append(f"'{word} {tok}': outlets are audio or control")
                else:
                    outputs[k] = _OUT_WORDS[word]
            else:
                if not 1 <= k <= n_in:
                    problems.append(f"'{tok}': this codebox has {n_in} inlet(s)")
                else:
                    inputs[k] = _IN_WORDS[word]
    return inputs, outputs, specs, problems


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


def _denormal_finding(run: _Run, k: int, y: np.ndarray, samplerate: float):
    a = np.abs(y)
    sub = (a > 0.0) & (a < DENORMAL_MAX)
    if not sub.any():
        return None
    i = int(np.argmax(sub))
    return Finding(
        "denormal", "warn", run.corner, k,
        f"{int(sub.sum())} subnormal sample(s), first at n={i} ({i / samplerate:.4f} s): "
        "a decaying state reaches the denormal range (slow on the CPU); "
        "fixdenorm() on the feedback path avoids it",
    )


def _driven_checks(run: _Run, samplerate: float, out_kinds: dict, full: bool = True,
                   excited: bool = True) -> tuple:
    """Driven-window checks on one run. Returns (findings, finite_outputs,
    silence_candidates).

    Every output: nonfinite (FAIL) and, on full runs, denormal (WARN).
    Audio outputs only (CR-01): peak (FAIL), and on full runs silent / dc
    (WARN) and permanent silence. ``full=False`` runs only nonfinite and
    peak (the self-sustain small run). ``excited=False`` skips the
    permanent-silence check (WR-05): no audio inlet still changes over the
    tail of the driven window, so an output that decays there is correct.
    A silence hit is returned as a candidate, not a finding: smoke_codebox
    confirms it with a loud rerun first (WR-03)."""
    findings: list = []
    finite: list = []
    silent_cands: list = []
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
        if full:
            den = _denormal_finding(run, k, y, samplerate)
            if den is not None:
                findings.append(den)
        if out_kinds.get(k, AUDIO) != AUDIO:
            continue
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
                silent_cands.append((k, tail_n))
            mean = float(np.mean(d))
            if abs(mean) > DC_DRIVEN_LIMIT:
                findings.append(Finding(
                    "dc", "warn", run.corner, k,
                    f"mean {mean:+.4g} over the driven window (|mean| > {DC_DRIVEN_LIMIT:g})",
                ))
    return findings, finite, silent_cands


def _silence_findings(run: _Run, cands: list, loud_outputs, samplerate: float) -> list:
    """WR-03: a silence candidate is a FAIL only when a loud rerun (default
    inlets' noise as loud as the impulse) also goes silent. A gate, threshold
    or one-shot that the +-0.1 noise can no longer open is a WARN."""
    out: list = []
    d0, d1 = run.driven
    for k, tail_n in cands:
        base = (
            "permanent silence after excitation: last "
            f"{tail_n / samplerate:.3f} s of the driven window below "
            f"{SILENCE_FLOOR:g} while an input is still changing"
        )
        y = loud_outputs[k - 1] if loud_outputs is not None else None
        if y is not None and np.all(np.isfinite(y)):
            tail = np.abs(y[d0:d1][-tail_n:])
            if tail.size and tail.max() >= SILENCE_FLOOR:
                out.append(Finding(
                    "silence", "warn", run.corner, k,
                    base + f"; a loud rerun (noise +-{LOUD_NOISE_AMP:g}) stays active, "
                    "so the output went quiet when the input dropped below the level "
                    "that opened it (a gate, threshold or one-shot), not a failure",
                ))
                continue
        out.append(Finding("silence", "fail", run.corner, k, base))
    return out


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


def _ringout_checks(run: _Run, small_outputs, finite: list, samplerate: float,
                    out_kinds: dict) -> list:
    """dc latch (WARN) and self_sustain (FAIL, D-05) on the ring-out window,
    audio outputs only. ``small_outputs`` is None when no inlet is scaled
    (no audio inlet: a generator), which skips self_sustain."""
    findings: list = []
    for k in finite:
        if out_kinds.get(k, AUDIO) != AUDIO:
            continue
        y = run.outputs[k - 1]
        tail = _tail(y, run.ring)
        mean = float(np.mean(tail))
        if abs(mean) > DC_TAIL_LIMIT:
            findings.append(Finding(
                "dc", "warn", run.corner, k,
                f"dc latch: mean {mean:+.4g} over the last {tail.size / samplerate:.3f} s "
                f"of the ring-out (|mean| > {DC_TAIL_LIMIT:g})",
            ))
        if small_outputs is None:
            continue
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
                "with an audio inlet; mark trigger / control inlets with "
                "'// smoke: trigger inN' or skip with --no-ringout",
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


def _validate_seed(seed) -> int:
    if isinstance(seed, bool) or not isinstance(seed, (int, np.integer)) or seed < 0:
        raise ValueError(f"seed must be a non-negative integer, got {seed!r}")
    return int(seed)


def _resolve_ports(cb, ports, directive_in: dict, directive_out: dict) -> tuple:
    """(in_kinds, out_kinds, notes, host): directives > host graph > audio."""
    in_kinds = {k: AUDIO for k in range(1, cb.n_in + 1)}
    out_kinds = {k: AUDIO for k in range(1, cb.n_out + 1)}
    notes: dict = {}
    host = ""
    if ports is not None:
        host = ports.host
        for k, v in ports.inputs.items():
            if k in in_kinds:
                in_kinds[k] = v
                notes[f"in{k}"] = ports.notes.get(f"in{k}", "")
        for k, v in ports.outputs.items():
            if k in out_kinds:
                out_kinds[k] = v
                notes[f"out{k}"] = ports.notes.get(f"out{k}", "")
    for k, v in directive_in.items():
        in_kinds[k] = v
        notes[f"in{k}"] = "// smoke: directive"
    for k, v in directive_out.items():
        out_kinds[k] = v
        notes[f"out{k}"] = "// smoke: directive"
    return in_kinds, out_kinds, notes, host


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
    ports: PortKinds | None = None,
) -> CodeboxResult:
    """Smoke one codebox at every corner and return its verdict.

    ``inputs`` maps a 1-based inlet to a SPEC string (a key beyond the
    codebox's inlet count is not applied and gives an ``unused_input`` WARN).
    ``ports`` carries host-inferred port kinds (discover_codeboxes fills it);
    ``// smoke:`` directives in the code override it, and without either
    every port is audio. An error at one corner is an ``unsupported``
    finding at that corner; the other corners still run, so a FAIL is never
    lost. Raises ValueError on bad arguments.
    """
    n = _validate_run_args(seconds, samplerate)
    samplerate = float(samplerate)
    seed = _validate_seed(seed)
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

    d_in, d_out, d_specs, d_problems = parse_directives(code, cb.n_in, cb.n_out)
    in_kinds, out_kinds, notes, host = _resolve_ports(cb, ports, d_in, d_out)
    port_info = dict(inputs=in_kinds, outputs=out_kinds, port_notes=notes, port_host=host)

    specs = []
    for k in range(1, cb.n_in + 1):
        if k in parsed_inputs:
            specs.append(parsed_inputs[k])
        elif k in d_specs:
            specs.append(d_specs[k])
        else:
            specs.append(_KIND_SPEC[in_kinds[k]])
    driving = [s in (_DEFAULT_SPEC, _GATE_SPEC) for s in specs]
    nd = int(n * DRIVE_FRACTION)
    # The default and gate stimuli stop at N/2, so the driven window ends
    # there whenever an inlet carries one; otherwise the inputs drive the run.
    driven = (0, nd) if any(driving) else (0, n)
    ring = (nd, n) if (ringout and any(driving) and all(s in _QUIET_SPECS for s in specs)) else None
    signals = [_signal(s, k, n, samplerate, seed) for k, s in enumerate(specs, 1)]
    # Audio inlets on the default stimulus are the ones the self-sustain
    # rerun scales and the WR-03 loud rerun raises; control and trigger
    # inlets keep their stimulus (a trigger's level is not an amplitude).
    scaled = [s == _DEFAULT_SPEC and in_kinds[k] == AUDIO for k, s in enumerate(specs, 1)]
    # WR-05: permanent silence only means something while an audio input
    # still changes over the tail of the driven window.
    d0, d1 = driven
    tail_n = max(1, int((d1 - d0) * TAIL_FRACTION))
    excited = any(
        in_kinds[k] == AUDIO and float(np.ptp(sig[d1 - tail_n:d1])) > ACTIVITY_FLOOR
        for k, sig in enumerate(signals, 1)
    )

    findings: list = [
        Finding("constant_assign", "warn", "build", 0, w) for w in cb.warnings
    ]
    findings.extend(Finding(check, "warn", "build", 0, detail) for check, detail in cb.lint)
    findings.extend(Finding("smoke_directive", "warn", "build", 0, f"// smoke: {p}")
                    for p in d_problems)
    # INFO advisories never change the verdict, the exit code or the warning count.
    findings.extend(Finding(check, "info", "build", 0, detail) for check, detail in cb.advisories)
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
            f, finite, cands = _driven_checks(run, samplerate, out_kinds, excited=excited)
            findings.extend(f)
            if cands:
                loud_prog = cb.build(params=cparams, samplerate=samplerate, seed=seed,
                                     buffers=buffers)
                loud = [
                    _signal(s, k, n, samplerate, seed, noise_amp=LOUD_NOISE_AMP) if sc else x
                    for k, (s, x, sc) in enumerate(zip(specs, signals, scaled), 1)
                ]
                findings.extend(_silence_findings(run, cands, loud_prog.run(loud, n), samplerate))
            if ring is None:
                continue
            small_outs = None
            if any(scaled):
                # Self-sustain rerun (D-05): fresh Program, every scaled
                # inlet and the Buffer backing x SUSTAIN_SCALE, same seeds.
                small_prog = cb.build(
                    params=cparams, samplerate=samplerate, seed=seed, buffers=buffers,
                    buffer_scale=SUSTAIN_SCALE,
                )
                small_outs = small_prog.run(
                    [x * SUSTAIN_SCALE if sc else x for x, sc in zip(signals, scaled)], n
                )
                small_run = _Run(
                    f"{corner} @{SUSTAIN_SCALE:g}x", cparams, small_outs, driven, ring
                )
                f_small, _, _ = _driven_checks(small_run, samplerate, out_kinds, full=False)
                findings.extend(f_small)
            findings.extend(_ringout_checks(run, small_outs, finite, samplerate, out_kinds))
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
        return CodeboxResult(label, "fail", reason, completed, findings, **port_info)
    if errors:
        reason = errors[0][1]
        if len(errors) < n_corners:
            reason += f" ({len(errors)} of {n_corners} corners)"
        return CodeboxResult(label, "unsupported", reason, completed, findings, **port_info)
    return CodeboxResult(label, "pass", "", completed, findings, **port_info)


def smoke_file(path, **kwargs) -> list:
    """Smoke every codebox in ``path``. Skipped and unsupported discovery
    entries pass through as results. Raises ValueError on a read error."""
    results: list = []
    for e in discover_codeboxes(path):
        if e.status != "ok":
            results.append(CodeboxResult(e.label, e.status, e.reason, 0, []))
            continue
        results.append(smoke_codebox(e.code, label=e.label, ports=e.ports, **kwargs))
    return results


# ===========================================================================
# CLI
# ===========================================================================

_EPILOG = """\
ports: each outlet is audio (some cord path reaches dac~ / plugout~ / out~ /
gain~ / meters) or control (Hz, ms, indices, flags: only NaN/inf and denormal
are checked), and each inlet audio, control, trigger or zero, inferred from
the host patch (for a .gendsp: a sibling .maxpat that loads it; none: every
port is audio). Override in the codebox with a comment line such as
  // smoke: control out2 out4 trigger in1 in3=phasor:2

input SPEC forms (per inlet, --input K=SPEC, repeatable):
  impulse+noise   default for audio and control inlets: 0.25 impulse at n=0
                  plus seeded +-0.1 noise for the first half, then zeros
  gate            default for trigger inlets: two 1.0 gates in the first
                  half, then zeros
  zero            all zeros (default for unconnected inlets in a host)
  const:V         constant V for the whole run (dc:V is an alias)
  phasor:HZ       0..1 ramp at HZ, e.g. --input 1=phasor:2
  sine:HZ         sine at HZ, amplitude 0.25
const / phasor / sine hold their signal for the whole run, which turns the
ring-out checks (self_sustain, dc latch) off. self_sustain also needs an
audio inlet on the default stimulus (it is the one scaled by 0.01x).

Buffer backing: MAX's buffer~ contents are not available offline; each
Buffer is 48000 frames x 1 channel of a 0.25 220 Hz sine unless resized with
--buffer NAME=FRAMES[:CHANS] (scaled with the stimulus in the self-sustain
rerun). Data is zero-filled.

exit codes: 0 every codebox passed (warnings allowed), 1 any FAIL,
2 usage or read error, 3 any unsupported codebox (and no FAIL) or nothing
to smoke.
"""


def _seed_arg(text: str) -> int:
    """IN-03: name the problem here, before numpy rejects a negative seed."""
    try:
        v = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not an integer: {text!r}") from None
    if v < 0:
        raise argparse.ArgumentTypeError(f"must be a non-negative integer, got {v}")
    return v


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
            "report NaN/inf (FAIL) on every output, and peak > 4, permanent "
            "silence and self-sustain (FAIL) plus DC offset (WARN) on audio "
            "outputs; control outputs (Hz, ms, indices, flags; inferred from "
            "the host patch) get only NaN/inf and denormal checks. Unsupported "
            "constructs never pass. Advisory: not a save gate."
        ),
        epilog=_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("path", help="a .gendsp or .maxpat file")
    p.add_argument("--seconds", type=_seconds_arg, default=1.0,
                   help="seconds per corner run (default 1.0, max 60)")
    p.add_argument("--samplerate", type=_samplerate_arg, default=44100.0,
                   help="sample rate in Hz (default 44100)")
    p.add_argument("--seed", type=_seed_arg, default=1,
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


def _ports_line(r) -> str:
    """``  ports: in1 trigger (click~); out1 audio (dac~)`` when the kinds came
    from a host patch or a directive, or any port is not audio."""
    if not (r.inputs or r.outputs):
        return ""
    if not (r.port_host or r.port_notes
            or any(v != "audio" for v in list(r.inputs.values()) + list(r.outputs.values()))):
        return ""

    def fmt(prefix, kinds):
        parts = []
        for k in sorted(kinds):
            note = r.port_notes.get(f"{prefix}{k}", "")
            parts.append(f"{prefix}{k} {kinds[k]}" + (f" ({note})" if note else ""))
        return ", ".join(parts)

    body = "; ".join(x for x in (fmt("in", r.inputs), fmt("out", r.outputs)) if x)
    host = f" [host: {r.port_host}]" if r.port_host else ""
    return f"  ports: {body}{host}"


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
        ports = _ports_line(r)
        if ports:
            lines.append(ports)
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
                "ports": {
                    "inputs": {str(k): v for k, v in sorted(r.inputs.items())},
                    "outputs": {str(k): v for k, v in sorted(r.outputs.items())},
                    "notes": dict(r.port_notes),
                    "host": r.port_host,
                },
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
