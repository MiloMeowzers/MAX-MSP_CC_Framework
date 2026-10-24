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
        "rect": [ 85.0, 104.0, 1124.0, 500.0 ],
        "bglocked": 0,
        "openinpresentation": 1,
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
                    "maxclass": "newobj",
                    "id": "obj-1",
                    "numinlets": 0,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 30.0, 30.0, 86.0, 22.0 ],
                    "text": "receive #2",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-2",
                    "numinlets": 1,
                    "numoutlets": 3,
                    "outlettype": [ "", "", "" ],
                    "patching_rect": [ 30.0, 75.0, 107.0, 22.0 ],
                    "text": "trigger f f f",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-3",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 195.0, 150.0, 51.0, 22.0 ],
                    "text": "float",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-4",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 150.0, 120.0, 58.0, 22.0 ],
                    "text": "gate 1",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-5",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "" ],
                    "patching_rect": [ 270.0, 150.0, 93.0, 22.0 ],
                    "text": "trigger f f",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-6",
                    "numinlets": 2,
                    "numoutlets": 3,
                    "outlettype": [ "", "", "" ],
                    "patching_rect": [ 465.0, 240.0, 65.0, 22.0 ],
                    "text": "peak 0.",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-7",
                    "numinlets": 2,
                    "numoutlets": 3,
                    "outlettype": [ "", "", "" ],
                    "patching_rect": [ 360.0, 240.0, 79.0, 22.0 ],
                    "text": "trough 0.",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-8",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "" ],
                    "patching_rect": [ 30.0, 120.0, 93.0, 22.0 ],
                    "text": "trigger f f",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-9",
                    "numinlets": 5,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 255.0, 285.0, 128.0, 22.0 ],
                    "text": "zmap #5 #6 #7 #8",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-10",
                    "numinlets": 1,
                    "numoutlets": 4,
                    "outlettype": [ "", "", "", "" ],
                    "patching_rect": [ 270.0, 330.0, 121.0, 22.0 ],
                    "text": "trigger f f f f",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-11",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "outlettype": [],
                    "patching_rect": [ 510.0, 360.0, 97.5, 22.0 ],
                    "text": "send #3",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "outlet",
                    "id": "obj-12",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "outlettype": [],
                    "patching_rect": [ 465.0, 360.0, 30.0, 30.0 ],
                    "parameter_enable": 0,
                    "comment": "normalized value"
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-13",
                    "numinlets": 0,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 135.0, 30.0, 142.0, 22.0 ],
                    "text": "receive face.learn",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-14",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "" ],
                    "patching_rect": [ 165.0, 75.0, 93.0, 22.0 ],
                    "text": "trigger i i",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-15",
                    "numinlets": 2,
                    "numoutlets": 2,
                    "outlettype": [ "", "" ],
                    "patching_rect": [ 255.0, 120.0, 72.0, 22.0 ],
                    "text": "select 1",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-16",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "" ],
                    "patching_rect": [ 195.0, 195.0, 93.0, 22.0 ],
                    "text": "trigger f f",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-17",
                    "numinlets": 0,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 300.0, 30.0, 86.0, 22.0 ],
                    "text": "receive #4",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-18",
                    "numinlets": 2,
                    "numoutlets": 2,
                    "outlettype": [ "", "" ],
                    "patching_rect": [ 300.0, 75.0, 101.0, 22.0 ],
                    "text": "route range",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-19",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "" ],
                    "patching_rect": [ 345.0, 120.0, 116.0, 22.0 ],
                    "text": "unpack f f",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-20",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 405.0, 30.0, 72.0, 22.0 ],
                    "text": "loadbang",
                    "fontname": "Arial",
                    "fontsize": 12.0,
                    "bgcolor": [ 0.85, 0.92, 0.85, 1.0 ]
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-21",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "" ],
                    "patching_rect": [ 420.0, 75.0, 93.0, 22.0 ],
                    "text": "trigger b b",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "message",
                    "id": "obj-22",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 645.0, 120.0, 58.0, 22.0 ],
                    "text": "set #1",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "message",
                    "id": "obj-23",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 480.0, 120.0, 121.0, 22.0 ],
                    "text": "setminmax #7 #8",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "comment",
                    "id": "obj-24",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "outlettype": [],
                    "patching_rect": [ 645.0, 150.0, 65.0, 20.0 ],
                    "text": "feature",
                    "fontname": "Arial",
                    "fontsize": 12.0,
                    "presentation": 1,
                    "presentation_rect": [ 0.0, 2.0, 62.0, 20.0 ],
                    "textcolor": [ 0.8, 0.8, 0.82, 1.0 ]
                }
            },
            {
                "box": {
                    "maxclass": "flonum",
                    "id": "obj-25",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "" ],
                    "patching_rect": [ 120.0, 150.0, 50.0, 22.0 ],
                    "parameter_enable": 0,
                    "presentation": 1,
                    "presentation_rect": [ 62.0, 1.0, 62.0, 20.0 ],
                    "numdecimalplaces": 3,
                    "ignoreclick": 1
                }
            },
            {
                "box": {
                    "maxclass": "multislider",
                    "id": "obj-26",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "" ],
                    "patching_rect": [ 630.0, 360.0, 200.0, 100.0 ],
                    "parameter_enable": 0,
                    "presentation": 1,
                    "presentation_rect": [ 128.0, 2.0, 110.0, 18.0 ],
                    "orientation": 0,
                    "settype": 1,
                    "size": 1,
                    "setminmax": [ 0.0, 1.0 ],
                    "setstyle": 1,
                    "ignoreclick": 1
                }
            },
            {
                "box": {
                    "maxclass": "flonum",
                    "id": "obj-27",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "" ],
                    "patching_rect": [ 390.0, 360.0, 50.0, 22.0 ],
                    "parameter_enable": 0,
                    "presentation": 1,
                    "presentation_rect": [ 242.0, 1.0, 58.0, 20.0 ],
                    "numdecimalplaces": 3,
                    "ignoreclick": 1
                }
            },
            {
                "box": {
                    "maxclass": "comment",
                    "id": "obj-28",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "outlettype": [],
                    "patching_rect": [ 480.0, 30.0, 604.0, 20.0 ],
                    "text": "args: label, raw receive, normalized send, cfg receive, in lo, in hi, out lo, out hi",
                    "fontname": "Arial",
                    "fontsize": 12.0,
                    "textcolor": [ 0.8, 0.8, 0.82, 1.0 ]
                }
            },
            {
                "box": {
                    "maxclass": "comment",
                    "id": "obj-29",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "outlettype": [],
                    "patching_rect": [ 225.0, 120.0, 520.0, 20.0 ],
                    "text": "learn 1: reset min/max to the current value, then widen; learn 0: freeze",
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
                    "patching_rect": [ 390.0, 30.0, 520.0, 20.0 ],
                    "text": "cfg receive: \"range lo hi\" sets the input range (sent on tracker switch)",
                    "fontname": "Arial",
                    "fontsize": 12.0,
                    "textcolor": [ 0.8, 0.8, 0.82, 1.0 ]
                }
            }
        ],
        "lines": [
            {
                "patchline": {
                    "source": [ "obj-1", 0 ],
                    "destination": [ "obj-2", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-2", 2 ],
                    "destination": [ "obj-3", 1 ],
                    "midpoints": [ 130.0, 146.0, 239.0, 146.0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-2", 1 ],
                    "destination": [ "obj-4", 1 ],
                    "midpoints": [ 83.5, 103.0, 201.0, 103.0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-4", 0 ],
                    "destination": [ "obj-5", 0 ],
                    "midpoints": [ 157.0, 146.0, 277.0, 146.0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-5", 1 ],
                    "destination": [ "obj-7", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-5", 0 ],
                    "destination": [ "obj-6", 0 ],
                    "midpoints": [ 277.0, 176.0, 472.0, 176.0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-6", 0 ],
                    "destination": [ "obj-9", 2 ],
                    "midpoints": [ 472.0, 268.0, 319.0, 268.0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-7", 0 ],
                    "destination": [ "obj-9", 1 ],
                    "midpoints": [ 367.0, 273.5, 290.5, 273.5 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-2", 0 ],
                    "destination": [ "obj-8", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-8", 1 ],
                    "destination": [ "obj-25", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-8", 0 ],
                    "destination": [ "obj-9", 0 ],
                    "midpoints": [ 37.0, 223.0, 262.0, 223.0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-9", 0 ],
                    "destination": [ "obj-10", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-10", 3 ],
                    "destination": [ "obj-27", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-10", 2 ],
                    "destination": [ "obj-26", 0 ],
                    "midpoints": [ 348.3333333333333, 356.0, 637.0, 356.0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-10", 1 ],
                    "destination": [ "obj-12", 0 ],
                    "midpoints": [ 312.6666666666667, 356.0, 472.0, 356.0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-10", 0 ],
                    "destination": [ "obj-11", 0 ],
                    "midpoints": [ 277.0, 356.0, 517.0, 356.0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-13", 0 ],
                    "destination": [ "obj-14", 0 ],
                    "midpoints": [ 142.0, 56.0, 172.0, 56.0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-14", 1 ],
                    "destination": [ "obj-15", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-15", 0 ],
                    "destination": [ "obj-3", 0 ],
                    "midpoints": [ 262.0, 146.0, 202.0, 146.0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-3", 0 ],
                    "destination": [ "obj-16", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-16", 1 ],
                    "destination": [ "obj-7", 1 ],
                    "midpoints": [ 281.0, 228.5, 432.0, 228.5 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-16", 0 ],
                    "destination": [ "obj-6", 1 ],
                    "midpoints": [ 202.0, 225.0, 523.0, 225.0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-14", 0 ],
                    "destination": [ "obj-4", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-17", 0 ],
                    "destination": [ "obj-18", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-18", 0 ],
                    "destination": [ "obj-19", 0 ],
                    "midpoints": [ 307.0, 108.5, 352.0, 108.5 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-19", 1 ],
                    "destination": [ "obj-9", 2 ],
                    "midpoints": [ 454.0, 213.5, 319.0, 213.5 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-19", 0 ],
                    "destination": [ "obj-9", 1 ],
                    "midpoints": [ 352.0, 213.5, 290.5, 213.5 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-20", 0 ],
                    "destination": [ "obj-21", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-21", 1 ],
                    "destination": [ "obj-23", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-21", 0 ],
                    "destination": [ "obj-22", 0 ],
                    "midpoints": [ 427.0, 108.5, 652.0, 108.5 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-23", 0 ],
                    "destination": [ "obj-26", 0 ],
                    "midpoints": [ 487.0, 251.0, 637.0, 251.0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-22", 0 ],
                    "destination": [ "obj-24", 0 ]
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