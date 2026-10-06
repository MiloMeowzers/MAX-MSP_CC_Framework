// scenefile.js -- one file dialog, two scene files (barnett-dbap v0.7.3)
// The source's read / write go to its own pattrstorage AND, over the scene cord, to the
// dbap-motion module's pattrstorage, which has no file buttons of its own. The motion file sits
// beside the source file: "show.json" -> "show-motion.json". Picking the -motion file in the read
// dialog loads the pair it belongs to. A source with no motion module patched in writes only its
// own file (outlet 1 goes nowhere).
//
// inlet 0:   read <path> / write <path>   (from opendialog / savedialog via prepend)
// outlet 0:  read|write <path>            -> this source's pattrstorage
// outlet 1:  read|write <path>-motion     -> scene cord -> dbap-motion's pattrstorage

inlets = 1;
outlets = 2;

var MOTION_SUFFIX = "-motion.json";

function endsWith(s, tail) {
    return s.length >= tail.length && s.toLowerCase().substring(s.length - tail.length) === tail;
}

// the source file for any chosen path: .json added if missing, a -motion file mapped back
function sourcePath(p) {
    if (endsWith(p, MOTION_SUFFIX)) return p.substring(0, p.length - MOTION_SUFFIX.length) + ".json";
    if (endsWith(p, ".json")) return p;
    return p + ".json";
}

function motionPath(src) {
    return src.substring(0, src.length - ".json".length) + MOTION_SUFFIX;
}

function send(verb, p) {
    if (typeof p !== "string" || p.length === 0) return;
    var src = sourcePath(p);
    outlet(1, verb, motionPath(src));
    outlet(0, verb, src);
}

function read(p) {
    send("read", p);
}

function write(p) {
    send("write", p);
}

function anything() {
    post("scenefile.js: unknown message " + messagename + "\n");
}
