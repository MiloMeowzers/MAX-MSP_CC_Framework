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
        "rect": [ 85.0, 104.0, 1990.0, 525.0 ],
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
                    "patching_rect": [ 290.0, 205.0, 394.0, 20.0 ],
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
                    "patching_rect": [ 290.0, 227.0, 1199.0, 20.0 ],
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
                    "patching_rect": [ 50.0, 39.0, 506.0, 20.0 ],
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
                    "patching_rect": [ 30.0, 465.0, 58.0, 20.0 ],
                    "text": "v0.1.0",
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
                    "patching_rect": [ 30.0, 75.0, 129.5, 22.0 ],
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
                    "patching_rect": [ 30.0, 120.0, 72.0, 22.0 ],
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
                    "patching_rect": [ 105.0, 120.0, 723.0, 20.0 ],
                    "text": "deferlow: moves loads to the low-priority queue and keeps /open then /ping ordered (the load barrier)",
                    "fontname": "Arial",
                    "fontsize": 12.0,
                    "textcolor": [ 0.8, 0.8, 0.82, 1.0 ]
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-8",
                    "numinlets": 10,
                    "numoutlets": 10,
                    "outlettype": [ "", "", "", "", "", "", "", "", "", "" ],
                    "patching_rect": [ 30.0, 165.0, 513.0, 22.0 ],
                    "text": "route /ping /open /sf /console /dsp /listen /close /openfile /closefile",
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
                    "patching_rect": [ 765.0, 405.0, 170.0, 22.0 ],
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
                    "patching_rect": [ 270.0, 195.0, 51.0, 22.0 ],
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
                    "patching_rect": [ 1275.0, 195.0, 100.0, 22.0 ],
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
                    "patching_rect": [ 1275.0, 315.0, 72.0, 22.0 ],
                    "text": "pcontrol",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "message",
                    "id": "obj-13",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 1395.0, 195.0, 205.0, 22.0 ],
                    "text": ";\rmax openfile maxbridge $1",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "message",
                    "id": "obj-14",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 30.0, 270.0, 191.0, 22.0 ],
                    "text": ";\rmax closefile maxbridge",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "comment",
                    "id": "obj-15",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "outlettype": [],
                    "patching_rect": [ 1605.0, 195.0, 345.0, 20.0 ],
                    "text": "variant B open/close (max openfile / closefile)",
                    "fontname": "Arial",
                    "fontsize": 12.0,
                    "textcolor": [ 0.8, 0.8, 0.82, 1.0 ]
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-16",
                    "numinlets": 3,
                    "numoutlets": 3,
                    "outlettype": [ "", "", "" ],
                    "patching_rect": [ 255.0, 270.0, 86.0, 22.0 ],
                    "text": "select 1 0",
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
                    "patching_rect": [ 255.0, 315.0, 93.0, 22.0 ],
                    "text": ";\rdsp start",
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
                    "patching_rect": [ 375.0, 315.0, 86.0, 22.0 ],
                    "text": ";\rdsp stop",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "message",
                    "id": "obj-19",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 360.0, 270.0, 184.0, 22.0 ],
                    "text": ";\r__maxbridge_close bang",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "comment",
                    "id": "obj-20",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "outlettype": [],
                    "patching_rect": [ 555.0, 270.0, 457.0, 20.0 ],
                    "text": "the temp copy's receive __maxbridge_close closes its own window",
                    "fontname": "Arial",
                    "fontsize": 12.0,
                    "textcolor": [ 0.8, 0.8, 0.82, 1.0 ]
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-21",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 480.0, 75.0, 87.5, 22.0 ],
                    "text": "loadmess 0",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-22",
                    "numinlets": 1,
                    "numoutlets": 4,
                    "outlettype": [ "", "", "", "" ],
                    "patching_rect": [ 795.0, 270.0, 79.0, 22.0 ],
                    "text": "t i i i i",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "comment",
                    "id": "obj-23",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "outlettype": [],
                    "patching_rect": [ 885.0, 270.0, 555.0, 20.0 ],
                    "text": "listening off at load: error off and the gates closed block the feedback loop",
                    "fontname": "Arial",
                    "fontsize": 12.0,
                    "textcolor": [ 0.8, 0.8, 0.82, 1.0 ]
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-24",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 915.0, 315.0, 51.0, 22.0 ],
                    "text": "error",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-25",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 690.0, 315.0, 52.0, 22.0 ],
                    "text": "gate",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-26",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 765.0, 315.0, 52.0, 22.0 ],
                    "text": "gate",
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
                    "patching_rect": [ 840.0, 315.0, 52.0, 22.0 ],
                    "text": "gate",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-28",
                    "numinlets": 1,
                    "numoutlets": 3,
                    "outlettype": [ "", "", "" ],
                    "patching_rect": [ 585.0, 270.0, 191.0, 22.0 ],
                    "text": "console @showonlyerrors 1",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-29",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 690.0, 360.0, 128.0, 22.0 ],
                    "text": "prepend /con/obj",
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
                    "patching_rect": [ 840.0, 360.0, 128.0, 22.0 ],
                    "text": "prepend /con/msg",
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
                    "patching_rect": [ 990.0, 360.0, 135.0, 22.0 ],
                    "text": "prepend /con/type",
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
                    "patching_rect": [ 1140.0, 360.0, 100.0, 22.0 ],
                    "text": "prepend /err",
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
                    "outlettype": [ "signal" ],
                    "patching_rect": [ 780.0, 75.0, 170.0, 22.0 ],
                    "text": "receive~ __maxbridge_L",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-34",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "signal" ],
                    "patching_rect": [ 585.0, 75.0, 170.0, 22.0 ],
                    "text": "receive~ __maxbridge_R",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-35",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "signal" ],
                    "patching_rect": [ 900.0, 270.0, 176.0, 22.0 ],
                    "text": "sfrecord~ 2",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-36",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 990.0, 315.0, 107.0, 22.0 ],
                    "text": "snapshot~ 100",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "flonum",
                    "id": "obj-37",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "" ],
                    "patching_rect": [ 1260.0, 360.0, 50.0, 22.0 ],
                    "parameter_enable": 0
                }
            },
            {
                "box": {
                    "maxclass": "comment",
                    "id": "obj-38",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "outlettype": [],
                    "patching_rect": [ 1320.0, 360.0, 366.0, 20.0 ],
                    "text": "elapsed ms; sfrecord~ records only while DSP is on",
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
                    "destination": [ "obj-8", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-8", 0 ],
                    "destination": [ "obj-10", 0 ],
                    "midpoints": [ 37.0, 191.0, 277.0, 191.0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-10", 0 ],
                    "destination": [ "obj-9", 0 ],
                    "midpoints": [ 277.0, 221.0, 249.0, 221.0, 249.0, 397.0, 772.0, 397.0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-8", 1 ],
                    "destination": [ "obj-11", 0 ],
                    "midpoints": [ 92.44444444444444, 191.0, 1282.0, 191.0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-11", 0 ],
                    "destination": [ "obj-12", 0 ],
                    "midpoints": [ 1282.0, 221.0, 1495.0, 221.0, 1495.0, 309.0, 1282.0, 309.0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-8", 7 ],
                    "destination": [ "obj-13", 0 ],
                    "midpoints": [ 425.1111111111111, 191.0, 1402.0, 191.0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-8", 8 ],
                    "destination": [ "obj-14", 0 ],
                    "midpoints": [ 480.55555555555554, 228.5, 37.0, 228.5 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-8", 4 ],
                    "destination": [ "obj-16", 0 ],
                    "midpoints": [ 258.77777777777777, 195.0, 262.0, 195.0 ]
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
                    "source": [ "obj-16", 1 ],
                    "destination": [ "obj-18", 0 ],
                    "midpoints": [ 298.0, 296.0, 382.0, 296.0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-8", 6 ],
                    "destination": [ "obj-19", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-21", 0 ],
                    "destination": [ "obj-22", 0 ],
                    "midpoints": [ 487.0, 183.5, 802.0, 183.5 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-8", 5 ],
                    "destination": [ "obj-22", 0 ],
                    "midpoints": [ 314.22222222222223, 228.5, 802.0, 228.5 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-22", 0 ],
                    "destination": [ "obj-24", 0 ],
                    "midpoints": [ 802.0, 303.5, 922.0, 303.5 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-22", 1 ],
                    "destination": [ "obj-25", 0 ],
                    "midpoints": [ 823.6666666666666, 303.5, 697.0, 303.5 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-22", 2 ],
                    "destination": [ "obj-26", 0 ],
                    "midpoints": [ 845.3333333333334, 303.5, 772.0, 303.5 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-22", 3 ],
                    "destination": [ "obj-27", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-8", 3 ],
                    "destination": [ "obj-28", 0 ],
                    "midpoints": [ 203.33333333333331, 228.5, 592.0, 228.5 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-28", 0 ],
                    "destination": [ "obj-25", 1 ],
                    "midpoints": [ 592.0, 303.5, 735.0, 303.5 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-25", 0 ],
                    "destination": [ "obj-29", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-29", 0 ],
                    "destination": [ "obj-9", 0 ],
                    "midpoints": [ 697.0, 393.5, 772.0, 393.5 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-28", 1 ],
                    "destination": [ "obj-26", 1 ],
                    "midpoints": [ 680.5, 303.5, 810.0, 303.5 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-26", 0 ],
                    "destination": [ "obj-30", 0 ],
                    "midpoints": [ 772.0, 343.0, 847.0, 343.0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-30", 0 ],
                    "destination": [ "obj-9", 0 ],
                    "midpoints": [ 847.0, 386.0, 772.0, 386.0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-28", 2 ],
                    "destination": [ "obj-27", 1 ],
                    "midpoints": [ 769.0, 303.5, 885.0, 303.5 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-27", 0 ],
                    "destination": [ "obj-31", 0 ],
                    "midpoints": [ 847.0, 343.0, 997.0, 343.0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-31", 0 ],
                    "destination": [ "obj-9", 0 ],
                    "midpoints": [ 997.0, 386.0, 772.0, 386.0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-24", 0 ],
                    "destination": [ "obj-32", 0 ],
                    "midpoints": [ 922.0, 343.0, 1147.0, 343.0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-32", 0 ],
                    "destination": [ "obj-9", 0 ],
                    "midpoints": [ 1147.0, 386.0, 772.0, 386.0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-33", 0 ],
                    "destination": [ "obj-35", 0 ],
                    "midpoints": [ 787.0, 183.5, 907.0, 183.5 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-34", 0 ],
                    "destination": [ "obj-35", 1 ],
                    "midpoints": [ 592.0, 183.5, 1069.0, 183.5 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-8", 2 ],
                    "destination": [ "obj-35", 0 ],
                    "midpoints": [ 147.88888888888889, 228.5, 907.0, 228.5 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-35", 0 ],
                    "destination": [ "obj-36", 0 ],
                    "midpoints": [ 907.0, 303.5, 997.0, 303.5 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-36", 0 ],
                    "destination": [ "obj-37", 0 ],
                    "midpoints": [ 997.0, 343.0, 1267.0, 343.0 ]
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