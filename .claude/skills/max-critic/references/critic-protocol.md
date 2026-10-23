# Critic Loop Protocol

Detailed specification for the generate-review-revise loop orchestrated by the critic agent.

## Loop Steps

### Step 1: Receive Generator Output

Accept `patch_dict` (and optionally `code_context` with genexpr/js/n4m code strings) from the generator agent.

### Step 2: Run Critics

```python
from src.maxpat.critics import review_patch, CriticResult

results = review_patch(patch_dict, code_context=code_context, ext_code=ext_code, ext_archetype=ext_archetype, is_new=is_new)
```

`is_new` must match the save that follows: `True` for a new file (`/max-build`, or any flow that creates a file), `False` (the default) for an edit of an existing one. The save gate reviews a file with no baseline with `is_new=True`, where a Q24 uninitialized-state finding is a blocker; reviewing it with `is_new=False` in the loop would approve a warning the gate then refuses.

This invokes the DSP critic (`review_dsp`), structure critic (`review_structure`), and conditionally the RNBO critic (`review_rnbo`, when rnbo~ boxes detected) and external critic (`review_external`, when `ext_code` provided).

### Step 3: Classify Results

Separate findings by severity:
- **Blockers**: Issues that must be fixed before output is acceptable
- **Warnings**: Issues worth noting but not blocking
- **Notes**: Informational observations

### Step 4: Handle Blockers

If blockers exist:
1. Format each blocker with its `finding` and `suggestion` fields
2. Send revision request to the generator with all blocker findings
3. Record the blocker findings in the revision history (for escalation detection)
4. Wait for generator to produce revised output
5. Return to Step 2

### Step 5: Handle Warnings and Notes

If no blockers but warnings/notes exist:
1. List the warnings and notes (finding + suggestion) in the summary returned to the caller
2. Do not modify the output: no `comment` boxes in the patch, no comments in the code
3. Proceed to Step 6

What each severity means for saving: `.claude/skills/references/severity-contract.md`.

### Step 6: Approve Output

Output is clean (no blockers). Return the approved patch/code to the caller.

## Revision Tracking

Maintain a list of findings from each revision round:

```
Round 1: [finding_A, finding_B]
Round 2: [finding_A, finding_C]  -- finding_B resolved, finding_C new
Round 3: [finding_A, finding_C]  -- same as round 2
```

Track by comparing the `finding` string of each CriticResult across rounds.

## Soft Round Limit

After completing 3 total revision rounds (not counting the initial generation), the critic loop pauses before requesting further revisions. This prevents unbounded context consumption when novel findings keep appearing each round.

### Pause Behavior

At the pause, the critic must:

1. **Log a cumulative summary table** of all findings across all rounds:

   | Round | Finding | Severity | Status |
   |-------|---------|----------|--------|
   | 1 | [finding text] | blocker | resolved / persists / new |
   | 2 | [finding text] | blocker | resolved / persists / new |
   | ... | ... | ... | ... |

   Status values:
   - **resolved**: finding was present in an earlier round but is no longer reported
   - **persists**: finding was present in an earlier round and is still reported
   - **new**: finding appeared for the first time this round

2. **Present the summary to the user**

3. **Ask:** "3 revision rounds completed. Continue revising or accept current state?"

4. **Options:**
   - **continue**: resume the loop normally with no further soft-limit pauses (the next stop would be the existing 5-identical-finding escalation below)
   - **accept**: the user has accepted the remaining blockers. They are listed in the report (never written into the output) and the output is approved. Saving a new file that still holds a blocker then needs `force=True` (CLAUDE.md Rule #7: force only with the user's confirmation, and choosing "accept" is that confirmation)

### Interaction with Escalation

The soft limit and escalation are independent mechanisms:
- **Soft limit** catches loops with novel findings each round (context cost)
- **Escalation** catches loops stuck on the same finding (generator inability)

Both can trigger in the same session. If the user says "continue" at the soft limit, the escalation rule still applies to any finding persisting 5 consecutive rounds.

## Escalation Rules

**IMPORTANT:** Escalation is for repeated identical findings only, NOT a general round limit.

The loop runs until clean. A soft limit pauses after 3 rounds for user confirmation (see above). The 5-identical-finding escalation below is a separate mechanism.

Escalation triggers when:
- The **same identical finding** (matched by `finding` string) persists across **5 consecutive revisions**
- This indicates the generator cannot resolve the issue, not that the loop has run too long

When escalation triggers:
1. Present the persistent finding to the user
2. Show what the generator attempted across the 5 revisions
3. Ask the user to decide: accept as-is, provide guidance, or skip the check
4. Resume the loop with user's decision applied

**This is NOT a round limit.** A loop that produces different findings each round (fixing one thing, discovering another) is caught by the soft limit above. A stuck loop (same finding, round after round) escalates here.

## Examples

### Clean on First Pass
```
Round 1: [] (no findings)
-> Approved immediately
```

### Fix and Clean
```
Round 1: [blocker: gen~ I/O mismatch]
-> Generator fixes gen~ inlet count
Round 2: [] (no findings)
-> Approved
```

### Soft Limit Pause
```
Round 1: [blocker: missing dac~]
-> Generator adds dac~
Round 2: [blocker: gain safety on *~ inlet]
-> Generator adds gain scaling
Round 3: [blocker: fan-out without trigger]
-> Soft limit reached. Summary:
   | Round | Finding | Severity | Status |
   |-------|---------|----------|--------|
   | 1 | missing dac~ | blocker | resolved |
   | 2 | gain safety on *~ inlet | blocker | resolved |
   | 3 | fan-out without trigger | blocker | persists |
-> User: "accept"
-> Fan-out blocker accepted by the user and listed in the report; output approved (a new-file save needs force=True)
```

### Escalation
```
Round 1: [blocker: fan-out without trigger on outlet 0]
Round 2: [blocker: fan-out without trigger on outlet 0]  -- same
Round 3: [blocker: fan-out without trigger on outlet 0]  -- same
Round 4: [blocker: fan-out without trigger on outlet 0]  -- same
Round 5: [blocker: fan-out without trigger on outlet 0]  -- same (5 consecutive)
-> Escalate to user: "Generator cannot resolve this fan-out issue"
```
