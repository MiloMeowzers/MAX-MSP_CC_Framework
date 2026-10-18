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
        "rect": [ 85.0, 104.0, 520.0, 300.0 ],
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
                    "patching_rect": [ 30.0, 30.0, 415.0, 20.0 ],
                    "text": "fx-clean (Q34 bridge fixture): a clean 440 Hz tone at 0.2",
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
                    "patching_rect": [ 30.0, 52.0, 450.0, 20.0 ],
                    "text": "Expected: no errors; peak ~0.2, pitch ~440 Hz, dc ~0, no flags",
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
                    "text": "cycle~ 440",
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
                    "outlettype": [ "signal" ],
                    "patching_rect": [ 30.0, 135.0, 58.0, 22.0 ],
                    "text": "*~ 0.2",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-5",
                    "numinlets": 2,
                    "numoutlets": 0,
                    "outlettype": [],
                    "patching_rect": [ 30.0, 180.0, 44.0, 22.0 ],
                    "text": "dac~",
                    "fontname": "Arial",
                    "fontsize": 12.0,
                    "bgcolor": [ 0.92, 0.85, 0.85, 1.0 ]
                }
            }
        ],
        "lines": [
            {
                "patchline": {
                    "source": [ "obj-3", 0 ],
                    "destination": [ "obj-4", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-4", 0 ],
                    "destination": [ "obj-5", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-4", 0 ],
                    "destination": [ "obj-5", 1 ],
                    "midpoints": [ 37.0, 168.5, 67.0, 168.5 ]
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