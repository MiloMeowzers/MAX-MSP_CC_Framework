stage: build
progress: v6_206 (expr-ternary fix) built + sent, awaiting user test. Base = ChopChop_v6_206.amxd. v6_205 test: instant playback but insanely quick; diag showed FRC(---frRenderMs)=0 and SPD(---karmaRep4 loop-end)=85.33ms (4096-sample clamp). Root cause: arithmetic-in-condition expr ternaries (pc_startx from v6_204, pc_spanx from v6_205) emit nothing in Max -> renderMs stayed at pack default 0 -> delay 0 -> play same tick as record -> 85ms loop. v6_206: both exprs rewritten as max() (CLAUDE.md-mandated form), nothing else. 28 cycles / 0 problems / size preserved. Expect SPD ~13712 (loop end ms), FRC ~1714 (renderMs), real audio, sane slices. See v6_206 build-log in context.md.
created: 2026-09-03T03:54:30.518730+00:00
updated: 2026-09-04
