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
        "rect": [ 85.0, 104.0, 751.0, 300.0 ],
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
                    "patching_rect": [ 30.0, 30.0, 632.0, 20.0 ],
                    "text": "DELIBERATE ERROR FIXTURE: osc~ is a Pure Data name; MAX must post 'osc~: No such object'",
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
                    "patching_rect": [ 30.0, 52.0, 681.0, 20.0 ],
                    "text": "fx-nosuchobj (Q34 bridge fixture): breaks Rule #1 on purpose, for the console-capture test only",
                    "fontname": "Arial",
                    "fontsize": 12.0,
                    "textcolor": [ 0.8, 0.8, 0.82, 1.0 ]
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-3",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "signal" ],
                    "patching_rect": [ 30.0, 90.0, 86.0, 22.0 ],
                    "text": "osc~ 440",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            }
        ],
        "lines": [],
        "dependency_cache": [],
        "autosave": 0,
        "bgcolor": [ 0.333, 0.333, 0.333, 1.0 ],
        "editing_bgcolor": [ 0.333, 0.333, 0.333, 1.0 ],
        "locked_bgcolor": [ 0.333, 0.333, 0.333, 1.0 ]
    }
}