# q29-check

Throwaway MAX check patch for the Q29 fixes (quick task 261016-d3y): write_gendsp in-place grow,
replace_box_safe identity + rewire, add_box companion placement, no-op save byte-identity.

- q29-grow.gendsp history: 60119697 (2 outs) -> c2994e96 (hand-edit comment added) -> 719dc7d3 (write_gendsp grew to 3 outs in place).
- Built by hand layout (no finalize_patch auto-layout) so add_box placement is what MAX shows.
