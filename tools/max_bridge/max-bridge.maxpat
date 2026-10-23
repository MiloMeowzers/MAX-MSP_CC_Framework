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
        "rect": [ 85.0, 104.0, 1760.0, 720.0 ],
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
                    "patching_rect": [ 20.0, 15.0, 394.0, 20.0 ],
                    "text": "MAX bridge (Q34 spike) — driven by tools/max_bridge.py",
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
                    "patching_rect": [ 20.0, 37.0, 1199.0, 20.0 ],
                    "text": "Listens for OSC on UDP 7400 on ALL network interfaces (udpreceive has no bind-host option): close this patch when not in use, and deny incoming connections if macOS asks",
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
                    "patching_rect": [ 20.0, 59.0, 506.0, 20.0 ],
                    "text": "Replies to 127.0.0.1:7401. Never add print here (error feedback loop).",
                    "fontname": "Arial",
                    "fontsize": 12.0,
                    "textcolor": [ 0.8, 0.8, 0.82, 1.0 ]
                }
            },
            {
                "box": {
                    "maxclass": "comment",
                    "id": "obj-4",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "outlettype": [],
                    "patching_rect": [ 1690.5, 15.0, 58.0, 20.0 ],
                    "text": "v0.2.0",
                    "fontname": "Arial",
                    "fontsize": 12.0,
                    "textcolor": [ 0.8, 0.8, 0.82, 1.0 ]
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-5",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 200.0, 220.0, 129.5, 22.0 ],
                    "text": "udpreceive 7400",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-6",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 200.0, 300.0, 72.0, 22.0 ],
                    "text": "deferlow",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "comment",
                    "id": "obj-7",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "outlettype": [],
                    "patching_rect": [ 287.0, 300.0, 709.0, 20.0 ],
                    "text": "deferlow: loads run on the low-priority queue, and /open then /ping stay ordered (the load barrier)",
                    "fontname": "Arial",
                    "fontsize": 12.0,
                    "textcolor": [ 0.8, 0.8, 0.82, 1.0 ]
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-47",
                    "numinlets": 12,
                    "numoutlets": 12,
                    "outlettype": [ "", "", "", "", "", "", "", "", "", "", "", "" ],
                    "patching_rect": [ 200.0, 340.0, 604.0, 22.0 ],
                    "text": "route /ping /open /sf /console /dsp /listen /close /openfile /closefile /query /note",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-9",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "outlettype": [],
                    "patching_rect": [ 405.0, 645.0, 170.0, 22.0 ],
                    "text": "udpsend 127.0.0.1 7401",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "message",
                    "id": "obj-10",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 20.0, 605.0, 51.0, 22.0 ],
                    "text": "/pong",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-11",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 86.0, 420.0, 100.0, 22.0 ],
                    "text": "prepend load",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-12",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 86.0, 460.0, 72.0, 22.0 ],
                    "text": "pcontrol",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-13",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "signal" ],
                    "patching_rect": [ 216.0, 420.0, 170.0, 22.0 ],
                    "text": "receive~ __maxbridge_L",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-14",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "signal" ],
                    "patching_rect": [ 401.0, 420.0, 170.0, 22.0 ],
                    "text": "receive~ __maxbridge_R",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-15",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "signal" ],
                    "patching_rect": [ 201.0, 470.0, 214.0, 22.0 ],
                    "text": "sfrecord~ 2",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-16",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 201.0, 510.0, 107.0, 22.0 ],
                    "text": "snapshot~ 100",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "flonum",
                    "id": "obj-17",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "" ],
                    "patching_rect": [ 201.0, 550.0, 50.0, 22.0 ],
                    "parameter_enable": 0
                }
            },
            {
                "box": {
                    "maxclass": "comment",
                    "id": "obj-18",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "outlettype": [],
                    "patching_rect": [ 201.0, 575.0, 180.0, 20.0 ],
                    "text": "elapsed ms; sfrecord~ records only while DSP is on",
                    "fontname": "Arial",
                    "fontsize": 12.0,
                    "textcolor": [ 0.8, 0.8, 0.82, 1.0 ]
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-19",
                    "numinlets": 1,
                    "numoutlets": 3,
                    "outlettype": [ "", "", "" ],
                    "patching_rect": [ 586.0, 420.0, 300.0, 22.0 ],
                    "text": "console @showonlyerrors 1",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-20",
                    "numinlets": 3,
                    "numoutlets": 3,
                    "outlettype": [ "", "", "" ],
                    "patching_rect": [ 901.0, 420.0, 86.0, 22.0 ],
                    "text": "select 1 0",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "message",
                    "id": "obj-21",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 901.0, 460.0, 93.0, 22.0 ],
                    "text": ";\rdsp start",
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
                    "patching_rect": [ 1013.0, 460.0, 86.0, 22.0 ],
                    "text": ";\rdsp stop",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-23",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 1132.0, 420.0, 87.5, 22.0 ],
                    "text": "loadmess 0",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-24",
                    "numinlets": 1,
                    "numoutlets": 4,
                    "outlettype": [ "", "", "", "" ],
                    "patching_rect": [ 1117.0, 460.0, 79.0, 22.0 ],
                    "text": "t i i i i",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "comment",
                    "id": "obj-25",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "outlettype": [],
                    "patching_rect": [ 1117.0, 535.0, 604.0, 20.0 ],
                    "text": "listening is off at load: error off and the gates closed keep the feedback loop shut",
                    "fontname": "Arial",
                    "fontsize": 12.0,
                    "textcolor": [ 0.8, 0.8, 0.82, 1.0 ]
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-26",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 405.0, 535.0, 51.0, 22.0 ],
                    "text": "error",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-27",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 548.0, 535.0, 52.0, 22.0 ],
                    "text": "gate",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-28",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 691.0, 535.0, 52.0, 22.0 ],
                    "text": "gate",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-29",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 834.0, 535.0, 52.0, 22.0 ],
                    "text": "gate",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-30",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 548.0, 575.0, 128.0, 22.0 ],
                    "text": "prepend /con/obj",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-31",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 691.0, 575.0, 128.0, 22.0 ],
                    "text": "prepend /con/msg",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-32",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 834.0, 575.0, 135.0, 22.0 ],
                    "text": "prepend /con/type",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-33",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 405.0, 575.0, 100.0, 22.0 ],
                    "text": "prepend /err",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "message",
                    "id": "obj-34",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 1234.5, 420.0, 184.0, 22.0 ],
                    "text": ";\r__maxbridge_close bang",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "comment",
                    "id": "obj-35",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "outlettype": [],
                    "patching_rect": [ 1234.5, 450.0, 219.0, 20.0 ],
                    "text": "closes the temp copy's window",
                    "fontname": "Arial",
                    "fontsize": 12.0,
                    "textcolor": [ 0.8, 0.8, 0.82, 1.0 ]
                }
            },
            {
                "box": {
                    "maxclass": "message",
                    "id": "obj-36",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 1450.5, 420.0, 205.0, 22.0 ],
                    "text": ";\rmax openfile maxbridge $1",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "message",
                    "id": "obj-37",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 1690.5, 420.0, 191.0, 22.0 ],
                    "text": ";\rmax closefile maxbridge",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "comment",
                    "id": "obj-38",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "outlettype": [],
                    "patching_rect": [ 1450.5, 450.0, 261.0, 20.0 ],
                    "text": "variant B: max openfile / closefile",
                    "fontname": "Arial",
                    "fontsize": 12.0,
                    "textcolor": [ 0.8, 0.8, 0.82, 1.0 ]
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-39",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 20.0, 100.0, 72.0, 22.0 ],
                    "text": "loadbang",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "message",
                    "id": "obj-40",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 20, 140, 40.0, 22.0 ],
                    "text": "0",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "toggle",
                    "id": "obj-41",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 20.0, 180.0, 24.0, 24.0 ],
                    "parameter_enable": 0
                }
            },
            {
                "box": {
                    "maxclass": "comment",
                    "id": "obj-42",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "outlettype": [],
                    "patching_rect": [ 50, 182, 856.0, 20.0 ],
                    "text": "ENABLE (kill switch): OFF at every load, so every incoming command is dropped. Turn it ON to let tools/max_bridge.py in.",
                    "fontname": "Arial",
                    "fontsize": 12.0,
                    "textcolor": [ 0.8, 0.8, 0.82, 1.0 ]
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-43",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "" ],
                    "patching_rect": [ 20.0, 220.0, 51.0, 22.0 ],
                    "text": "t i i",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-44",
                    "numinlets": 2,
                    "numoutlets": 2,
                    "outlettype": [ "", "" ],
                    "patching_rect": [ 20.0, 260.0, 72.0, 22.0 ],
                    "text": "select 0",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "message",
                    "id": "obj-45",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 20, 300, 79.0, 22.0 ],
                    "text": "/listen 0",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-46",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 200.0, 260.0, 72.0, 22.0 ],
                    "text": "gate 1 0",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-48",
                    "numinlets": 1,
                    "numoutlets": 3,
                    "outlettype": [ "", "", "" ],
                    "patching_rect": [ 1920.0, 420.0, 65.0, 22.0 ],
                    "text": "t b b b",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-49",
                    "numinlets": 1,
                    "numoutlets": 4,
                    "outlettype": [ "", "", "", "" ],
                    "patching_rect": [ 1920.0, 460.0, 79.0, 22.0 ],
                    "text": "dspstate~",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-50",
                    "numinlets": 2,
                    "numoutlets": 2,
                    "outlettype": [ "", "" ],
                    "patching_rect": [ 2014.0, 460.0, 107.0, 22.0 ],
                    "text": "adstatus sr",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-51",
                    "numinlets": 2,
                    "numoutlets": 2,
                    "outlettype": [ "", "" ],
                    "patching_rect": [ 2136.0, 460.0, 121.0, 22.0 ],
                    "text": "adstatus switch",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-52",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 1920.0, 500.0, 135.0, 22.0 ],
                    "text": "prepend /state/sr",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-53",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 2070.0, 500.0, 149.0, 22.0 ],
                    "text": "prepend /state/adsr",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-54",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 2234.0, 500.0, 142.0, 22.0 ],
                    "text": "prepend /state/dsp",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-55",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "outlettype": [],
                    "patching_rect": [ 1920.0, 540.0, 170.0, 22.0 ],
                    "text": "send __maxbridge_reply",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-56",
                    "numinlets": 0,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 990.0, 575.0, 191.0, 22.0 ],
                    "text": "receive __maxbridge_reply",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "comment",
                    "id": "obj-57",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "outlettype": [],
                    "patching_rect": [ 1920.0, 580, 751.0, 20.0 ],
                    "text": "/query: DSP on/off and sample rate -> 127.0.0.1:7401 (args become bangs; a query never changes a setting)",
                    "fontname": "Arial",
                    "fontsize": 12.0,
                    "textcolor": [ 0.8, 0.8, 0.82, 1.0 ]
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-58",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "outlettype": [],
                    "patching_rect": [ 2287.0, 420.0, 163.0, 22.0 ],
                    "text": "send __maxbridge_note",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "comment",
                    "id": "obj-59",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "outlettype": [],
                    "patching_rect": [ 2287.0, 460, 450.0, 20.0 ],
                    "text": "/note pitch vel ch -> the temp copy's receive __maxbridge_note",
                    "fontname": "Arial",
                    "fontsize": 12.0,
                    "textcolor": [ 0.8, 0.8, 0.82, 1.0 ]
                }
            }
        ],
        "lines": [
            {
                "patchline": {
                    "source": [ "obj-10", 0 ],
                    "destination": [ "obj-9", 0 ],
                    "midpoints": [ 27.0, 480.0, 412.0, 480.0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-11", 0 ],
                    "destination": [ "obj-12", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-13", 0 ],
                    "destination": [ "obj-15", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-14", 0 ],
                    "destination": [ "obj-15", 1 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-15", 0 ],
                    "destination": [ "obj-16", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-16", 0 ],
                    "destination": [ "obj-17", 0 ]
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
                    "source": [ "obj-20", 1 ],
                    "destination": [ "obj-22", 0 ],
                    "midpoints": [ 944.0, 291.0, 1020.0, 291.0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-23", 0 ],
                    "destination": [ "obj-24", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-24", 0 ],
                    "destination": [ "obj-26", 0 ],
                    "midpoints": [ 1124.0, 338.0, 412.0, 338.0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-24", 1 ],
                    "destination": [ "obj-27", 0 ],
                    "midpoints": [ 1145.6666666666667, 343.0, 555.0, 343.0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-24", 2 ],
                    "destination": [ "obj-28", 0 ],
                    "midpoints": [ 1167.3333333333333, 348.0, 698.0, 348.0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-24", 3 ],
                    "destination": [ "obj-29", 0 ],
                    "midpoints": [ 1189.0, 353.0, 841.0, 353.0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-19", 0 ],
                    "destination": [ "obj-27", 1 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-27", 0 ],
                    "destination": [ "obj-30", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-30", 0 ],
                    "destination": [ "obj-9", 0 ],
                    "midpoints": [ 555.0, 469.0, 412.0, 469.0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-19", 1 ],
                    "destination": [ "obj-28", 1 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-28", 0 ],
                    "destination": [ "obj-31", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-31", 0 ],
                    "destination": [ "obj-9", 0 ],
                    "midpoints": [ 698.0, 463.0, 412.0, 463.0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-19", 2 ],
                    "destination": [ "obj-29", 1 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-29", 0 ],
                    "destination": [ "obj-32", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-32", 0 ],
                    "destination": [ "obj-9", 0 ],
                    "midpoints": [ 841.0, 457.0, 412.0, 457.0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-26", 0 ],
                    "destination": [ "obj-33", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-33", 0 ],
                    "destination": [ "obj-9", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-5", 0 ],
                    "destination": [ "obj-46", 1 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-46", 0 ],
                    "destination": [ "obj-6", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-39", 0 ],
                    "destination": [ "obj-40", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-40", 0 ],
                    "destination": [ "obj-41", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-41", 0 ],
                    "destination": [ "obj-43", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-43", 1 ],
                    "destination": [ "obj-46", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-43", 0 ],
                    "destination": [ "obj-44", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-44", 0 ],
                    "destination": [ "obj-45", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-6", 0 ],
                    "destination": [ "obj-47", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-47", 0 ],
                    "destination": [ "obj-10", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-47", 1 ],
                    "destination": [ "obj-11", 0 ],
                    "midpoints": [ 82.44444444444444, 238.0, 93.0, 238.0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-47", 2 ],
                    "destination": [ "obj-15", 0 ],
                    "midpoints": [ 137.88888888888889, 234.0, 208.0, 234.0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-47", 3 ],
                    "destination": [ "obj-19", 0 ],
                    "midpoints": [ 193.33333333333331, 230.0, 593.0, 230.0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-47", 4 ],
                    "destination": [ "obj-20", 0 ],
                    "midpoints": [ 248.77777777777777, 226.0, 908.0, 226.0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-47", 5 ],
                    "destination": [ "obj-24", 0 ],
                    "midpoints": [ 304.22222222222223, 222.0, 1124.0, 222.0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-47", 6 ],
                    "destination": [ "obj-34", 0 ],
                    "midpoints": [ 359.66666666666663, 218.0, 1241.5, 218.0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-47", 7 ],
                    "destination": [ "obj-36", 0 ],
                    "midpoints": [ 415.1111111111111, 214.0, 1457.5, 214.0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-47", 8 ],
                    "destination": [ "obj-37", 0 ],
                    "midpoints": [ 470.55555555555554, 210.0, 1697.5, 210.0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-45", 0 ],
                    "destination": [ "obj-47", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-47", 9 ],
                    "destination": [ "obj-48", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-48", 0 ],
                    "destination": [ "obj-49", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-48", 1 ],
                    "destination": [ "obj-50", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-48", 2 ],
                    "destination": [ "obj-51", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-49", 1 ],
                    "destination": [ "obj-52", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-50", 1 ],
                    "destination": [ "obj-53", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-51", 1 ],
                    "destination": [ "obj-54", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-52", 0 ],
                    "destination": [ "obj-55", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-53", 0 ],
                    "destination": [ "obj-55", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-54", 0 ],
                    "destination": [ "obj-55", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-56", 0 ],
                    "destination": [ "obj-9", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-47", 10 ],
                    "destination": [ "obj-58", 0 ]
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