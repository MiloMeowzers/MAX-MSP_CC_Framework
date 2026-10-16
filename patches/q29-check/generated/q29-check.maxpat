{
    "patcher": {
        "fileversion": 1,
        "appversion": {
            "major": 9,
            "minor": 0,
            "revision": 0,
            "architecture": "x64",
            "modernui": 1
        },
        "classnamespace": "box",
        "rect": [ 85.0, 104.0, 1566.0, 815.0 ],
        "bglocked": 0,
        "openinpresentation": 0,
        "default_fontsize": 12.0,
        "default_fontface": 0,
        "default_fontname": "Arial",
        "gridonopen": 1,
        "gridsize": [ 15.0, 15.0 ],
        "gridsnaponopen": 1,
        "objectsnaponopen": 1,
        "statusbarvisible": 2,
        "toolbarvisible": 1,
        "lefttoolbarpinned": 0,
        "toptoolbarpinned": 0,
        "righttoolbarpinned": 0,
        "bottomtoolbarpinned": 0,
        "toolbars_unpinned_last_save": 0,
        "tallnewobj": 0,
        "boxanimatetime": 200,
        "enablehscroll": 1,
        "enablevscroll": 1,
        "devicewidth": 0.0,
        "description": "",
        "digest": "",
        "tags": "",
        "style": "",
        "subpatcher_template": "",
        "assistshowspatchername": 0,
        "boxes": [
            {
                "box": {
                    "maxclass": "comment",
                    "id": "obj-1",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "outlettype": [],
                    "patching_rect": [ 30.0, 570.0, 534.0, 20.0 ],
                    "text": "Q29 CHECK -- four MAX checks. Do step 1 (bottom) before touching anything.",
                    "fontname": "Arial",
                    "fontsize": 12.0,
                    "textcolor": [ 0.8, 0.8, 0.82, 1.0 ]
                }
            },
            {
                "box": {
                    "maxclass": "comment",
                    "id": "obj-2",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "outlettype": [],
                    "patching_rect": [ 30.0, 610.0, 471.0, 20.0 ],
                    "text": "A. write_gendsp grew q29-grow.gendsp from 2 to 3 outputs in place",
                    "fontname": "Arial",
                    "fontsize": 12.0,
                    "textcolor": [ 0.8, 0.8, 0.82, 1.0 ]
                }
            },
            {
                "box": {
                    "maxclass": "comment",
                    "id": "obj-3",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "outlettype": [],
                    "patching_rect": [ 30.0, 630.0, 772.0, 20.0 ],
                    "text": "Click ezdac~ to start DSP. Expect 0.25 / 0.5 / 0.75. Double-click gen~: the HAND EDIT comment must be there.",
                    "fontname": "Arial",
                    "fontsize": 12.0,
                    "textcolor": [ 0.8, 0.8, 0.82, 1.0 ]
                }
            },
            {
                "box": {
                    "maxclass": "ezdac~",
                    "id": "obj-4",
                    "numinlets": 2,
                    "numoutlets": 0,
                    "outlettype": [],
                    "patching_rect": [ 30.0, 660.0, 45.0, 45.0 ],
                    "parameter_enable": 0,
                    "bgcolor": [ 0.92, 0.85, 0.85, 1.0 ]
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-5",
                    "numinlets": 1,
                    "numoutlets": 3,
                    "outlettype": [ "signal", "signal", "signal" ],
                    "patching_rect": [ 30.0, 30.0, 121.0, 22.0 ],
                    "text": "gen~ q29-grow",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-6",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 30.0, 75.0, 107.0, 22.0 ],
                    "text": "snapshot~ 100",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "flonum",
                    "id": "obj-7",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "" ],
                    "patching_rect": [ 30.0, 120.0, 50.0, 22.0 ],
                    "parameter_enable": 0
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-8",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 165.0, 75.0, 107.0, 22.0 ],
                    "text": "snapshot~ 100",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "flonum",
                    "id": "obj-9",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "" ],
                    "patching_rect": [ 165.0, 120.0, 50.0, 22.0 ],
                    "parameter_enable": 0
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-10",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 300.0, 75.0, 107.0, 22.0 ],
                    "text": "snapshot~ 100",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "flonum",
                    "id": "obj-11",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "" ],
                    "patching_rect": [ 300.0, 120.0, 50.0, 22.0 ],
                    "parameter_enable": 0
                }
            },
            {
                "box": {
                    "maxclass": "comment",
                    "id": "obj-12",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "outlettype": [],
                    "patching_rect": [ 705.0, 280.0, 625.0, 20.0 ],
                    "text": "B. replace_box_safe: live.dial -> live.slider (varname q29dial), pack 0 0 -> pack 0 0 0",
                    "fontname": "Arial",
                    "fontsize": 12.0,
                    "textcolor": [ 0.8, 0.8, 0.82, 1.0 ]
                }
            },
            {
                "box": {
                    "maxclass": "comment",
                    "id": "obj-13",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "outlettype": [],
                    "patching_rect": [ 705.0, 300.0, 821.0, 20.0 ],
                    "text": "Move the slider: flonum follows. Click store 1, move it, click recall 1: it jumps back. clientwindow lists q29dial.",
                    "fontname": "Arial",
                    "fontsize": 12.0,
                    "textcolor": [ 0.8, 0.8, 0.82, 1.0 ]
                }
            },
            {
                "box": {
                    "maxclass": "live.slider",
                    "id": "obj-27",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "" ],
                    "patching_rect": [ 705.0, 330.0, 39.0, 87.0 ],
                    "parameter_enable": 1,
                    "varname": "q29dial",
                    "saved_attribute_attributes": {
                        "valueof": {
                            "parameter_longname": "q29dial",
                            "parameter_shortname": "q29dial",
                            "parameter_type": 0,
                            "parameter_mmax": 127.0,
                            "parameter_initial": [ 64.0 ],
                            "parameter_initial_enable": 1
                        }
                    }
                }
            },
            {
                "box": {
                    "maxclass": "flonum",
                    "id": "obj-15",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "" ],
                    "patching_rect": [ 705.0, 420.0, 50.0, 22.0 ],
                    "parameter_enable": 0
                }
            },
            {
                "box": {
                    "maxclass": "message",
                    "id": "obj-16",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 900.0, 30.0, 65.0, 22.0 ],
                    "text": "store 1",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "message",
                    "id": "obj-17",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 1005.0, 30.0, 72.0, 22.0 ],
                    "text": "recall 1",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "message",
                    "id": "obj-18",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 1110.0, 30.0, 100.0, 22.0 ],
                    "text": "clientwindow",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-19",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 1005.0, 75.0, 186.5, 22.0 ],
                    "text": "pattrstorage q29store",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-20",
                    "numinlets": 1,
                    "numoutlets": 4,
                    "outlettype": [ "", "", "", "" ],
                    "patching_rect": [ 1206.5, 330.0, 79.0, 22.0 ],
                    "text": "autopattr",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "comment",
                    "id": "obj-21",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "outlettype": [],
                    "patching_rect": [ 25.0, 755.0, 555.0, 20.0 ],
                    "text": "Set both numbers: the message shows 'a b 0' (all cords survived the replace).",
                    "fontname": "Arial",
                    "fontsize": 12.0,
                    "textcolor": [ 0.8, 0.8, 0.82, 1.0 ]
                }
            },
            {
                "box": {
                    "maxclass": "number",
                    "id": "obj-22",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "" ],
                    "patching_rect": [ 450.0, 45.0, 50.0, 22.0 ],
                    "parameter_enable": 0
                }
            },
            {
                "box": {
                    "maxclass": "number",
                    "id": "obj-23",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "" ],
                    "patching_rect": [ 525.0, 45.0, 50.0, 22.0 ],
                    "parameter_enable": 0
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-28",
                    "numinlets": 3,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 450.0, 75.0, 88.0, 22.0 ],
                    "text": "pack 0 0 0",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-25",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 450.0, 120.0, 97.0, 22.0 ],
                    "text": "prepend set",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "message",
                    "id": "obj-26",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 585.0, 165.0, 40.0, 22.0 ],
                    "text": "",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "comment",
                    "id": "obj-29",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "outlettype": [],
                    "patching_rect": [ 455.0, 215.0, 506.0, 20.0 ],
                    "text": "C. meter~ added 5px right of gain~: must sit side by side, not stacked",
                    "fontname": "Arial",
                    "fontsize": 12.0,
                    "textcolor": [ 0.8, 0.8, 0.82, 1.0 ]
                }
            },
            {
                "box": {
                    "maxclass": "comment",
                    "id": "obj-30",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "outlettype": [],
                    "patching_rect": [ 30.0, 270.0, 604.0, 20.0 ],
                    "text": "With DSP on, raise the gain~ fader: the meter moves. No dac~, so nothing is audible.",
                    "fontname": "Arial",
                    "fontsize": 12.0,
                    "textcolor": [ 0.8, 0.8, 0.82, 1.0 ]
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-31",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "signal" ],
                    "patching_rect": [ 30.0, 300.0, 86.0, 22.0 ],
                    "text": "cycle~ 220",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "gain~",
                    "id": "obj-32",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "signal", "" ],
                    "patching_rect": [ 30.0, 345.0, 22.0, 140.0 ],
                    "parameter_enable": 0
                }
            },
            {
                "box": {
                    "maxclass": "meter~",
                    "id": "obj-33",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 60.0, 345.0, 15.0, 100.0 ],
                    "parameter_enable": 0
                }
            },
            {
                "box": {
                    "maxclass": "comment",
                    "id": "obj-34",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "outlettype": [],
                    "patching_rect": [ 30.0, 510.0, 786.0, 20.0 ],
                    "text": "1. FIRST: open in MAX, change nothing, Cmd-S, close. Then tell Claude: it checks the diff and a no-op re-save.",
                    "fontname": "Arial",
                    "fontsize": 12.0,
                    "textcolor": [ 0.8, 0.8, 0.82, 1.0 ]
                }
            }
        ],
        "lines": [
            {
                "patchline": {
                    "source": [ "obj-5", 0 ],
                    "destination": [ "obj-6", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-6", 0 ],
                    "destination": [ "obj-7", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-5", 1 ],
                    "destination": [ "obj-8", 0 ],
                    "midpoints": [ 90.5, 58.0, 172.0, 58.0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-8", 0 ],
                    "destination": [ "obj-9", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-5", 2 ],
                    "destination": [ "obj-10", 0 ],
                    "midpoints": [ 144.0, 58.0, 307.0, 58.0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-10", 0 ],
                    "destination": [ "obj-11", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-16", 0 ],
                    "destination": [ "obj-19", 0 ],
                    "midpoints": [ 907.0, 58.0, 1012.0, 58.0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-17", 0 ],
                    "destination": [ "obj-19", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-18", 0 ],
                    "destination": [ "obj-19", 0 ],
                    "midpoints": [ 1117.0, 58.0, 1012.0, 58.0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-25", 0 ],
                    "destination": [ "obj-26", 0 ],
                    "midpoints": [ 457.0, 153.5, 592.0, 153.5 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-27", 0 ],
                    "destination": [ "obj-15", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-22", 0 ],
                    "destination": [ "obj-28", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-23", 0 ],
                    "destination": [ "obj-28", 1 ],
                    "midpoints": [ 532.0, 71.0, 494.0, 71.0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-28", 0 ],
                    "destination": [ "obj-25", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-31", 0 ],
                    "destination": [ "obj-32", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-32", 0 ],
                    "destination": [ "obj-33", 0 ],
                    "midpoints": [ 82.0, 490.0, 82.0, 337.0, 67.0, 337.0 ]
                }
            }
        ],
        "dependency_cache": [],
        "autosave": 0,
        "bgcolor": [ 0.333, 0.333, 0.333, 1.0 ],
        "editing_bgcolor": [ 0.333, 0.333, 0.333, 1.0 ],
        "locked_bgcolor": [ 0.333, 0.333, 0.333, 1.0 ]
    }
}