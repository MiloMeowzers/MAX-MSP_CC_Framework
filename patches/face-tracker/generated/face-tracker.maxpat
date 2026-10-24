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
        "rect": [ 60.0, 60.0, 1630.0, 1879.0 ],
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
                    "maxclass": "bpatcher",
                    "id": "obj-1",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 75.0, 225.0, 250.0, 55.0 ],
                    "args": [],
                    "bgmode": 0,
                    "border": 0,
                    "clickthrough": 0,
                    "enablehscroll": 0,
                    "enablevscroll": 0,
                    "lockeddragscroll": 0,
                    "offset": [ 0.0, 0.0 ],
                    "viewvisibility": 1,
                    "name": "jit-vis-grab-ui.maxpat",
                    "presentation": 1,
                    "presentation_rect": [ 16.0, 318.0, 250.0, 55.0 ]
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-2",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 30.0, 30.0, 87.5, 22.0 ],
                    "text": "loadmess 1",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-3",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "" ],
                    "patching_rect": [ 165.0, 465.0, 93.0, 22.0 ],
                    "text": "trigger l l",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-4",
                    "numinlets": 1,
                    "numoutlets": 3,
                    "outlettype": [ "", "", "" ],
                    "patching_rect": [ 30.0, 510.0, 723.0, 22.0 ],
                    "text": "jit.world ftview @visible 0 @enable 1 @output_texture 1 @size 640 360 @dim 640 360 @preserve_aspect 0",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "jit.pwindow",
                    "id": "obj-5",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "" ],
                    "patching_rect": [ 165.0, 555.0, 480, 270 ],
                    "parameter_enable": 0,
                    "presentation": 1,
                    "presentation_rect": [ 16.0, 40.0, 480.0, 270.0 ]
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-6",
                    "numinlets": 2,
                    "numoutlets": 2,
                    "outlettype": [ "", "" ],
                    "patching_rect": [ 780.0, 510.0, 72.0, 22.0 ],
                    "text": "gate 2 1",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-7",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 510.0, 165.0, 37.0, 22.0 ],
                    "text": "+ 1",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-8",
                    "numinlets": 1,
                    "numoutlets": 3,
                    "outlettype": [ "", "", "" ],
                    "patching_rect": [ 30.0, 855.0, 611.0, 22.0 ],
                    "text": "jit.vis.face @async 0 @smooth 0 @debugdraw 1 @drawto ftview @outputdict 0 @mirrored 1",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-9",
                    "numinlets": 1,
                    "numoutlets": 3,
                    "outlettype": [ "", "", "" ],
                    "patching_rect": [ 660.0, 555.0, 478.0, 22.0 ],
                    "text": "jit.vis.facemesh @mirrored 1 @debugdraw 0 @drawto ftview @smooth 0",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-10",
                    "numinlets": 0,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 300.0, 30.0, 149.0, 22.0 ],
                    "text": "receive ft.face.ctl",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-11",
                    "numinlets": 0,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 135.0, 30.0, 149.0, 22.0 ],
                    "text": "receive ft.mesh.ctl",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "jit.fpsgui",
                    "id": "obj-12",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "" ],
                    "patching_rect": [ 495.0, 945.0, 80.0, 36.0 ],
                    "parameter_enable": 0,
                    "presentation": 1,
                    "presentation_rect": [ 276.0, 318.0, 80.0, 35.0 ]
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-13",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "" ],
                    "patching_rect": [ 300.0, 900.0, 93.0, 22.0 ],
                    "text": "trigger l l",
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
                    "patching_rect": [ 660.0, 900.0, 93.0, 22.0 ],
                    "text": "trigger l l",
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
                    "patching_rect": [ 765.0, 510.0, 260.0, 20.0 ],
                    "text": "offscreen jit.world: camera as background + tracker debugdraw overlay -> texture -> pwindow",
                    "fontname": "Arial",
                    "fontsize": 12.0,
                    "textcolor": [ 0.8, 0.8, 0.82, 1.0 ]
                }
            },
            {
                "box": {
                    "maxclass": "comment",
                    "id": "obj-16",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "outlettype": [],
                    "patching_rect": [ 855.0, 510.0, 260.0, 20.0 ],
                    "text": "gate 2 feeds only the selected tracker, so the idle one costs nothing",
                    "fontname": "Arial",
                    "fontsize": 12.0,
                    "textcolor": [ 0.8, 0.8, 0.82, 1.0 ]
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-17",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "outlettype": [],
                    "patching_rect": [ 300.0, 945.0, 121.0, 22.0 ],
                    "text": "p face-features",
                    "fontname": "Arial",
                    "fontsize": 12.0,
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
                        "rect": [ 100.0, 100.0, 400.0, 300.0 ],
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
                                    "maxclass": "inlet",
                                    "id": "obj-1",
                                    "numinlets": 0,
                                    "numoutlets": 1,
                                    "outlettype": [ "" ],
                                    "patching_rect": [ 30.0, 30.0, 30.0, 30.0 ],
                                    "parameter_enable": 0,
                                    "comment": "jit.vis.face landmark matrix (12 x 4 faces, x y z conf)"
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
                                    "text": "trigger l l l",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "newobj",
                                    "id": "obj-3",
                                    "numinlets": 1,
                                    "numoutlets": 2,
                                    "outlettype": [ "", "" ],
                                    "patching_rect": [ 30.0, 120.0, 240.0, 22.0 ],
                                    "text": "jit.spill @plane 3 @listlength 1",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "newobj",
                                    "id": "obj-4",
                                    "numinlets": 1,
                                    "numoutlets": 1,
                                    "outlettype": [ "" ],
                                    "patching_rect": [ 105.0, 165.0, 107.0, 22.0 ],
                                    "text": "expr $f1 > 0.",
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
                                    "patching_rect": [ 120.0, 210.0, 93.0, 22.0 ],
                                    "text": "trigger i i",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "newobj",
                                    "id": "obj-6",
                                    "numinlets": 1,
                                    "numoutlets": 3,
                                    "outlettype": [ "", "", "" ],
                                    "patching_rect": [ 150.0, 255.0, 58.0, 22.0 ],
                                    "text": "change",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "newobj",
                                    "id": "obj-7",
                                    "numinlets": 1,
                                    "numoutlets": 0,
                                    "outlettype": [],
                                    "patching_rect": [ 120.0, 285.0, 142.0, 22.0 ],
                                    "text": "send face.detected",
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
                                    "patching_rect": [ 285.0, 120.0, 247.0, 22.0 ],
                                    "text": "jit.spill @plane 1 @listlength 12",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "newobj",
                                    "id": "obj-9",
                                    "numinlets": 1,
                                    "numoutlets": 12,
                                    "outlettype": [ "", "", "", "", "", "", "", "", "", "", "", "" ],
                                    "patching_rect": [ 285.0, 165.0, 226.0, 22.0 ],
                                    "text": "unpack f f f f f f f f f f f f",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "newobj",
                                    "id": "obj-10",
                                    "numinlets": 1,
                                    "numoutlets": 2,
                                    "outlettype": [ "", "" ],
                                    "patching_rect": [ 555.0, 120.0, 247.0, 22.0 ],
                                    "text": "jit.spill @plane 0 @listlength 12",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "newobj",
                                    "id": "obj-11",
                                    "numinlets": 1,
                                    "numoutlets": 12,
                                    "outlettype": [ "", "", "", "", "", "", "", "", "", "", "", "" ],
                                    "patching_rect": [ 555.0, 165.0, 226.0, 22.0 ],
                                    "text": "unpack f f f f f f f f f f f f",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "newobj",
                                    "id": "obj-12",
                                    "numinlets": 9,
                                    "numoutlets": 1,
                                    "outlettype": [ "" ],
                                    "patching_rect": [ 420.0, 210.0, 170.0, 22.0 ],
                                    "text": "pack f f f f f f f f f",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "newobj",
                                    "id": "obj-13",
                                    "numinlets": 2,
                                    "numoutlets": 1,
                                    "outlettype": [ "" ],
                                    "patching_rect": [ 255.0, 255.0, 58.0, 22.0 ],
                                    "text": "gate 1",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "newobj",
                                    "id": "obj-14",
                                    "numinlets": 1,
                                    "numoutlets": 7,
                                    "outlettype": [ "", "", "", "", "", "", "" ],
                                    "patching_rect": [ 285.0, 285.0, 163.0, 22.0 ],
                                    "text": "trigger l l l l l l l",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "newobj",
                                    "id": "obj-15",
                                    "numinlets": 4,
                                    "numoutlets": 1,
                                    "outlettype": [ "" ],
                                    "patching_rect": [ 435.0, 330.0, 92.0, 22.0 ],
                                    "text": "expr $f4",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "newobj",
                                    "id": "obj-16",
                                    "numinlets": 1,
                                    "numoutlets": 0,
                                    "outlettype": [],
                                    "patching_rect": [ 435.0, 465.0, 121.0, 22.0 ],
                                    "text": "send face.raw.x",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "newobj",
                                    "id": "obj-17",
                                    "numinlets": 9,
                                    "numoutlets": 1,
                                    "outlettype": [ "" ],
                                    "patching_rect": [ 555.0, 330.0, 92.0, 22.0 ],
                                    "text": "expr $f9",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "newobj",
                                    "id": "obj-18",
                                    "numinlets": 1,
                                    "numoutlets": 0,
                                    "outlettype": [],
                                    "patching_rect": [ 585.0, 465.0, 121.0, 22.0 ],
                                    "text": "send face.raw.y",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "newobj",
                                    "id": "obj-19",
                                    "numinlets": 6,
                                    "numoutlets": 1,
                                    "outlettype": [ "" ],
                                    "patching_rect": [ 675.0, 330.0, 443.0, 22.0 ],
                                    "text": "expr (sqrt(($f2-$f1)*($f2-$f1)+($f6-$f5)*($f6-$f5))+0.000001)",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "newobj",
                                    "id": "obj-20",
                                    "numinlets": 1,
                                    "numoutlets": 0,
                                    "outlettype": [],
                                    "patching_rect": [ 1050.0, 465.0, 142.0, 22.0 ],
                                    "text": "send face.raw.size",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "newobj",
                                    "id": "obj-21",
                                    "numinlets": 8,
                                    "numoutlets": 1,
                                    "outlettype": [ "" ],
                                    "patching_rect": [ 30.0, 375.0, 513.0, 22.0 ],
                                    "text": "expr ($f8-$f7)/(sqrt(($f2-$f1)*($f2-$f1)+($f6-$f5)*($f6-$f5))+0.000001)",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "newobj",
                                    "id": "obj-22",
                                    "numinlets": 1,
                                    "numoutlets": 0,
                                    "outlettype": [],
                                    "patching_rect": [ 30.0, 465.0, 149.0, 22.0 ],
                                    "text": "send face.raw.mouth",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "newobj",
                                    "id": "obj-23",
                                    "numinlets": 6,
                                    "numoutlets": 1,
                                    "outlettype": [ "" ],
                                    "patching_rect": [ 570.0, 375.0, 583.0, 22.0 ],
                                    "text": "expr ($f3-($f1+$f2)*0.5)/(sqrt(($f2-$f1)*($f2-$f1)+($f6-$f5)*($f6-$f5))+0.000001)",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "newobj",
                                    "id": "obj-24",
                                    "numinlets": 1,
                                    "numoutlets": 0,
                                    "outlettype": [],
                                    "patching_rect": [ 735.0, 465.0, 135.0, 22.0 ],
                                    "text": "send face.raw.yaw",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "newobj",
                                    "id": "obj-25",
                                    "numinlets": 7,
                                    "numoutlets": 1,
                                    "outlettype": [ "" ],
                                    "patching_rect": [ 30.0, 420.0, 583.0, 22.0 ],
                                    "text": "expr ($f7-($f5+$f6)*0.5)/(sqrt(($f2-$f1)*($f2-$f1)+($f6-$f5)*($f6-$f5))+0.000001)",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "newobj",
                                    "id": "obj-26",
                                    "numinlets": 1,
                                    "numoutlets": 0,
                                    "outlettype": [],
                                    "patching_rect": [ 195.0, 465.0, 149.0, 22.0 ],
                                    "text": "send face.raw.pitch",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "newobj",
                                    "id": "obj-27",
                                    "numinlets": 6,
                                    "numoutlets": 1,
                                    "outlettype": [ "" ],
                                    "patching_rect": [ 630.0, 420.0, 513.0, 22.0 ],
                                    "text": "expr atan2(($f5-$f6)*($f1-$f2)\\, ($f1-$f2)*($f1-$f2)+0.000001)*57.29578",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "newobj",
                                    "id": "obj-28",
                                    "numinlets": 1,
                                    "numoutlets": 0,
                                    "outlettype": [],
                                    "patching_rect": [ 885.0, 465.0, 142.0, 22.0 ],
                                    "text": "send face.raw.roll",
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
                                    "patching_rect": [ 600.0, 210.0, 260.0, 20.0 ],
                                    "text": "rows: 0 L eye, 1 R eye, 6 nose, 8 outer lips, 10 contour; unpack fires right-to-left so x row 0 (hot) lands last",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "comment",
                                    "id": "obj-30",
                                    "numinlets": 1,
                                    "numoutlets": 0,
                                    "outlettype": [],
                                    "patching_rect": [ 330.0, 255.0, 260.0, 20.0 ],
                                    "text": "conf plane gates out frames with no face (values hold)",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "comment",
                                    "id": "obj-31",
                                    "numinlets": 1,
                                    "numoutlets": 0,
                                    "outlettype": [],
                                    "patching_rect": [ 465.0, 285.0, 260.0, 20.0 ],
                                    "text": "centroids only: no blink here; mouth is a nose-to-lip proxy, pose is eye/nose geometry",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
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
                                    "destination": [ "obj-3", 0 ],
                                    "midpoints": [ 130.0, 108.5, 37.0, 108.5 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-3", 0 ],
                                    "destination": [ "obj-4", 0 ],
                                    "midpoints": [ 37.0, 153.5, 112.0, 153.5 ]
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
                                    "source": [ "obj-5", 1 ],
                                    "destination": [ "obj-6", 0 ],
                                    "midpoints": [ 206.0, 243.5, 157.0, 243.5 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-6", 0 ],
                                    "destination": [ "obj-7", 0 ],
                                    "midpoints": [ 157.0, 281.0, 127.0, 281.0 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-5", 0 ],
                                    "destination": [ "obj-13", 0 ],
                                    "midpoints": [ 127.0, 236.0, 262.0, 236.0 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-2", 1 ],
                                    "destination": [ "obj-8", 0 ],
                                    "midpoints": [ 83.5, 105.0, 292.0, 105.0 ]
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
                                    "source": [ "obj-2", 0 ],
                                    "destination": [ "obj-10", 0 ],
                                    "midpoints": [ 37.0, 105.0, 562.0, 105.0 ]
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
                                    "source": [ "obj-11", 0 ],
                                    "destination": [ "obj-12", 0 ],
                                    "midpoints": [ 562.0, 193.0, 427.0, 193.0 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-11", 1 ],
                                    "destination": [ "obj-12", 1 ],
                                    "midpoints": [ 581.2727272727273, 193.0, 446.5, 193.0 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-11", 6 ],
                                    "destination": [ "obj-12", 2 ],
                                    "midpoints": [ 677.6363636363636, 193.0, 466.0, 193.0 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-11", 10 ],
                                    "destination": [ "obj-12", 3 ],
                                    "midpoints": [ 754.7272727272727, 193.0, 485.5, 193.0 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-9", 0 ],
                                    "destination": [ "obj-12", 4 ],
                                    "midpoints": [ 292.0, 198.5, 505.0, 198.5 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-9", 1 ],
                                    "destination": [ "obj-12", 5 ],
                                    "midpoints": [ 311.27272727272725, 198.5, 524.5, 198.5 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-9", 6 ],
                                    "destination": [ "obj-12", 6 ],
                                    "midpoints": [ 407.6363636363636, 198.5, 544.0, 198.5 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-9", 8 ],
                                    "destination": [ "obj-12", 7 ],
                                    "midpoints": [ 446.1818181818182, 193.0, 563.5, 193.0 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-9", 10 ],
                                    "destination": [ "obj-12", 8 ],
                                    "midpoints": [ 484.72727272727275, 193.0, 583.0, 193.0 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-12", 0 ],
                                    "destination": [ "obj-13", 1 ],
                                    "midpoints": [ 427.0, 236.0, 306.0, 236.0 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-13", 0 ],
                                    "destination": [ "obj-14", 0 ],
                                    "midpoints": [ 262.0, 281.0, 292.0, 281.0 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-14", 6 ],
                                    "destination": [ "obj-15", 0 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-15", 0 ],
                                    "destination": [ "obj-16", 0 ],
                                    "midpoints": [ 442.0, 358.0, 24.0, 358.0, 24.0, 459.0, 442.0, 459.0 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-14", 5 ],
                                    "destination": [ "obj-17", 0 ],
                                    "midpoints": [ 416.16666666666663, 311.0, 562.0, 311.0 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-17", 0 ],
                                    "destination": [ "obj-18", 0 ],
                                    "midpoints": [ 562.0, 403.0, 619.0, 403.0, 619.0, 459.0, 592.0, 459.0 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-14", 4 ],
                                    "destination": [ "obj-19", 0 ],
                                    "midpoints": [ 391.3333333333333, 311.0, 682.0, 311.0 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-19", 0 ],
                                    "destination": [ "obj-20", 0 ],
                                    "midpoints": [ 682.0, 358.0, 1159.0, 358.0, 1159.0, 459.0, 1057.0, 459.0 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-14", 3 ],
                                    "destination": [ "obj-21", 0 ],
                                    "midpoints": [ 366.5, 311.0, 37.0, 311.0 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-21", 0 ],
                                    "destination": [ "obj-22", 0 ],
                                    "midpoints": [ 37.0, 403.0, 24.0, 403.0, 24.0, 459.0, 37.0, 459.0 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-14", 2 ],
                                    "destination": [ "obj-23", 0 ],
                                    "midpoints": [ 341.6666666666667, 358.0, 577.0, 358.0 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-23", 0 ],
                                    "destination": [ "obj-24", 0 ],
                                    "midpoints": [ 577.0, 403.0, 624.0, 403.0, 624.0, 459.0, 742.0, 459.0 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-14", 1 ],
                                    "destination": [ "obj-25", 0 ],
                                    "midpoints": [ 316.8333333333333, 311.0, 24.0, 311.0, 24.0, 414.0, 37.0, 414.0 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-25", 0 ],
                                    "destination": [ "obj-26", 0 ],
                                    "midpoints": [ 37.0, 448.0, 202.0, 448.0 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-14", 0 ],
                                    "destination": [ "obj-27", 0 ],
                                    "midpoints": [ 292.0, 311.0, 549.0, 311.0, 549.0, 414.0, 637.0, 414.0 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-27", 0 ],
                                    "destination": [ "obj-28", 0 ],
                                    "midpoints": [ 637.0, 448.0, 892.0, 448.0 ]
                                }
                            }
                        ],
                        "dependency_cache": [],
                        "autosave": 0
                    },
                    "saved_object_attributes": {
                        "description": "",
                        "digest": "",
                        "globalpatchername": "",
                        "tags": ""
                    }
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-18",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 735.0, 945.0, 149.0, 22.0 ],
                    "text": "p facemesh-features",
                    "fontname": "Arial",
                    "fontsize": 12.0,
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
                        "rect": [ 100.0, 100.0, 400.0, 300.0 ],
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
                                    "maxclass": "inlet",
                                    "id": "obj-1",
                                    "numinlets": 0,
                                    "numoutlets": 1,
                                    "outlettype": [ "" ],
                                    "patching_rect": [ 30.0, 450.0, 30.0, 30.0 ],
                                    "parameter_enable": 0,
                                    "comment": "facemesh landmark matrix"
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "inlet",
                                    "id": "obj-2",
                                    "numinlets": 0,
                                    "numoutlets": 1,
                                    "outlettype": [ "" ],
                                    "patching_rect": [ 45.0, 30.0, 30.0, 30.0 ],
                                    "parameter_enable": 0,
                                    "comment": "face pose dictionary"
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "outlet",
                                    "id": "obj-3",
                                    "numinlets": 1,
                                    "numoutlets": 0,
                                    "outlettype": [],
                                    "patching_rect": [ 840.0, 210.0, 30.0, 30.0 ],
                                    "parameter_enable": 0,
                                    "comment": "blendshapes dictionary (for dict.view)"
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "newobj",
                                    "id": "obj-4",
                                    "numinlets": 1,
                                    "numoutlets": 9,
                                    "outlettype": [ "", "", "", "", "", "", "", "", "" ],
                                    "patching_rect": [ 30.0, 495.0, 170.0, 22.0 ],
                                    "text": "jit.vis.facemesh.parts",
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
                                    "patching_rect": [ 75.0, 540.0, 93.0, 22.0 ],
                                    "text": "trigger l l",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "newobj",
                                    "id": "obj-6",
                                    "numinlets": 1,
                                    "numoutlets": 4,
                                    "outlettype": [ "", "", "", "" ],
                                    "patching_rect": [ 105.0, 585.0, 62.25, 22.0 ],
                                    "text": "jit.3m",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "newobj",
                                    "id": "obj-7",
                                    "numinlets": 1,
                                    "numoutlets": 4,
                                    "outlettype": [ "", "", "", "" ],
                                    "patching_rect": [ 195.0, 585.0, 62.25, 22.0 ],
                                    "text": "jit.3m",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "newobj",
                                    "id": "obj-8",
                                    "numinlets": 1,
                                    "numoutlets": 4,
                                    "outlettype": [ "", "", "", "" ],
                                    "patching_rect": [ 105.0, 630.0, 116.0, 22.0 ],
                                    "text": "unpack f f f f",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "newobj",
                                    "id": "obj-9",
                                    "numinlets": 1,
                                    "numoutlets": 4,
                                    "outlettype": [ "", "", "", "" ],
                                    "patching_rect": [ 240.0, 630.0, 116.0, 22.0 ],
                                    "text": "unpack f f f f",
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
                                    "patching_rect": [ 375.0, 630.0, 116.0, 22.0 ],
                                    "text": "unpack f f f f",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "newobj",
                                    "id": "obj-11",
                                    "numinlets": 2,
                                    "numoutlets": 1,
                                    "outlettype": [ "" ],
                                    "patching_rect": [ 135.0, 675.0, 114.0, 22.0 ],
                                    "text": "expr $f1 - $f2",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "newobj",
                                    "id": "obj-12",
                                    "numinlets": 1,
                                    "numoutlets": 0,
                                    "outlettype": [],
                                    "patching_rect": [ 135.0, 705.0, 142.0, 22.0 ],
                                    "text": "send face.raw.size",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "newobj",
                                    "id": "obj-13",
                                    "numinlets": 1,
                                    "numoutlets": 0,
                                    "outlettype": [],
                                    "patching_rect": [ 570.0, 675.0, 121.0, 22.0 ],
                                    "text": "send face.raw.x",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "newobj",
                                    "id": "obj-14",
                                    "numinlets": 1,
                                    "numoutlets": 0,
                                    "outlettype": [],
                                    "patching_rect": [ 420.0, 675.0, 121.0, 22.0 ],
                                    "text": "send face.raw.y",
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
                                    "patching_rect": [ 180.0, 540.0, 260.0, 20.0 ],
                                    "text": "face_oval part: mean x/y = position, max x - min x = width (size)",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "newobj",
                                    "id": "obj-16",
                                    "numinlets": 1,
                                    "numoutlets": 3,
                                    "outlettype": [ "", "", "" ],
                                    "patching_rect": [ 30.0, 75.0, 198.0, 22.0 ],
                                    "text": "dict.unpack face_0: count:",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "newobj",
                                    "id": "obj-17",
                                    "numinlets": 1,
                                    "numoutlets": 1,
                                    "outlettype": [ "" ],
                                    "patching_rect": [ 135.0, 120.0, 100.0, 22.0 ],
                                    "text": "expr $f1 > 0",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "newobj",
                                    "id": "obj-18",
                                    "numinlets": 1,
                                    "numoutlets": 3,
                                    "outlettype": [ "", "", "" ],
                                    "patching_rect": [ 135.0, 165.0, 58.0, 22.0 ],
                                    "text": "change",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "newobj",
                                    "id": "obj-19",
                                    "numinlets": 1,
                                    "numoutlets": 0,
                                    "outlettype": [],
                                    "patching_rect": [ 135.0, 210.0, 142.0, 22.0 ],
                                    "text": "send face.detected",
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
                                    "patching_rect": [ 255.0, 120.0, 345.0, 22.0 ],
                                    "text": "dict.unpack blendshapes: rotation: translation:",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "newobj",
                                    "id": "obj-21",
                                    "numinlets": 1,
                                    "numoutlets": 3,
                                    "outlettype": [ "", "", "" ],
                                    "patching_rect": [ 255.0, 165.0, 107.0, 22.0 ],
                                    "text": "trigger l l l",
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
                                    "patching_rect": [ 360.0, 210.0, 359.0, 22.0 ],
                                    "text": "dict.unpack jawOpen: eyeBlinkLeft: eyeBlinkRight:",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "newobj",
                                    "id": "obj-23",
                                    "numinlets": 1,
                                    "numoutlets": 0,
                                    "outlettype": [],
                                    "patching_rect": [ 360.0, 255.0, 149.0, 22.0 ],
                                    "text": "send face.raw.mouth",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "newobj",
                                    "id": "obj-24",
                                    "numinlets": 1,
                                    "numoutlets": 0,
                                    "outlettype": [],
                                    "patching_rect": [ 525.0, 255.0, 156.0, 22.0 ],
                                    "text": "send face.raw.blinkL",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "newobj",
                                    "id": "obj-25",
                                    "numinlets": 1,
                                    "numoutlets": 0,
                                    "outlettype": [],
                                    "patching_rect": [ 705.0, 255.0, 156.0, 22.0 ],
                                    "text": "send face.raw.blinkR",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "newobj",
                                    "id": "obj-26",
                                    "numinlets": 1,
                                    "numoutlets": 4,
                                    "outlettype": [ "", "", "", "" ],
                                    "patching_rect": [ 390.0, 165.0, 156.0, 22.0 ],
                                    "text": "dict.unpack x: y: z:",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "newobj",
                                    "id": "obj-27",
                                    "numinlets": 1,
                                    "numoutlets": 0,
                                    "outlettype": [],
                                    "patching_rect": [ 885.0, 210.0, 149.0, 22.0 ],
                                    "text": "send face.raw.pitch",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "newobj",
                                    "id": "obj-28",
                                    "numinlets": 1,
                                    "numoutlets": 0,
                                    "outlettype": [],
                                    "patching_rect": [ 1050.0, 210.0, 135.0, 22.0 ],
                                    "text": "send face.raw.yaw",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "newobj",
                                    "id": "obj-29",
                                    "numinlets": 1,
                                    "numoutlets": 0,
                                    "outlettype": [],
                                    "patching_rect": [ 1200.0, 210.0, 142.0, 22.0 ],
                                    "text": "send face.raw.roll",
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
                                    "patching_rect": [ 735.0, 210.0, 79.0, 22.0 ],
                                    "text": "dict.iter",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "newobj",
                                    "id": "obj-31",
                                    "numinlets": 1,
                                    "numoutlets": 2,
                                    "outlettype": [ "", "" ],
                                    "patching_rect": [ 885.0, 255.0, 93.0, 22.0 ],
                                    "text": "trigger l l",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "newobj",
                                    "id": "obj-32",
                                    "numinlets": 2,
                                    "numoutlets": 2,
                                    "outlettype": [ "", "" ],
                                    "patching_rect": [ 975.0, 300.0, 86.0, 22.0 ],
                                    "text": "zl.slice 1",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "newobj",
                                    "id": "obj-33",
                                    "numinlets": 2,
                                    "numoutlets": 2,
                                    "outlettype": [ "", "" ],
                                    "patching_rect": [ 1080.0, 300.0, 86.0, 22.0 ],
                                    "text": "zl.slice 1",
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
                                    "outlettype": [ "" ],
                                    "patching_rect": [ 975.0, 345.0, 177.0, 22.0 ],
                                    "text": "sprintf send face.bs.%s",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "newobj",
                                    "id": "obj-35",
                                    "numinlets": 1,
                                    "numoutlets": 0,
                                    "outlettype": [],
                                    "patching_rect": [ 1065.0, 375.0, 65.0, 22.0 ],
                                    "text": "forward",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "comment",
                                    "id": "obj-36",
                                    "numinlets": 1,
                                    "numoutlets": 0,
                                    "outlettype": [],
                                    "patching_rect": [ 555.0, 165.0, 260.0, 20.0 ],
                                    "text": "rotation = head pose in Euler degrees (x pitch, y yaw, z roll)",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "comment",
                                    "id": "obj-37",
                                    "numinlets": 1,
                                    "numoutlets": 0,
                                    "outlettype": [],
                                    "patching_rect": [ 990.0, 255.0, 260.0, 20.0 ],
                                    "text": "every blendshape -> face.bs.<name>: set the forward target first, then send the value",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            }
                        ],
                        "lines": [
                            {
                                "patchline": {
                                    "source": [ "obj-1", 0 ],
                                    "destination": [ "obj-4", 0 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-4", 5 ],
                                    "destination": [ "obj-5", 0 ],
                                    "midpoints": [ 134.5, 528.5, 82.0, 528.5 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-5", 1 ],
                                    "destination": [ "obj-6", 0 ],
                                    "midpoints": [ 161.0, 573.5, 112.0, 573.5 ]
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
                                    "destination": [ "obj-11", 1 ],
                                    "midpoints": [ 112.0, 658.0, 242.0, 658.0 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-5", 0 ],
                                    "destination": [ "obj-7", 0 ],
                                    "midpoints": [ 82.0, 566.0, 202.0, 566.0 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-7", 2 ],
                                    "destination": [ "obj-9", 0 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-9", 0 ],
                                    "destination": [ "obj-11", 0 ],
                                    "midpoints": [ 247.0, 658.0, 142.0, 658.0 ]
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
                                    "source": [ "obj-7", 1 ],
                                    "destination": [ "obj-10", 0 ],
                                    "midpoints": [ 218.08333333333334, 613.0, 382.0, 613.0 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-10", 1 ],
                                    "destination": [ "obj-14", 0 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-10", 0 ],
                                    "destination": [ "obj-13", 0 ],
                                    "midpoints": [ 382.0, 658.0, 577.0, 658.0 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-2", 0 ],
                                    "destination": [ "obj-16", 0 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-16", 1 ],
                                    "destination": [ "obj-17", 0 ]
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
                                    "destination": [ "obj-19", 0 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-16", 0 ],
                                    "destination": [ "obj-20", 0 ],
                                    "midpoints": [ 37.0, 105.0, 262.0, 105.0 ]
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
                                    "source": [ "obj-21", 2 ],
                                    "destination": [ "obj-22", 0 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-22", 0 ],
                                    "destination": [ "obj-23", 0 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-22", 1 ],
                                    "destination": [ "obj-24", 0 ],
                                    "midpoints": [ 482.0, 238.0, 532.0, 238.0 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-22", 2 ],
                                    "destination": [ "obj-25", 0 ],
                                    "midpoints": [ 597.0, 238.0, 712.0, 238.0 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-21", 1 ],
                                    "destination": [ "obj-30", 0 ],
                                    "midpoints": [ 308.5, 191.0, 742.0, 191.0 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-21", 0 ],
                                    "destination": [ "obj-3", 0 ],
                                    "midpoints": [ 262.0, 191.0, 847.0, 191.0 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-20", 1 ],
                                    "destination": [ "obj-26", 0 ],
                                    "midpoints": [ 372.3333333333333, 153.5, 397.0, 153.5 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-26", 0 ],
                                    "destination": [ "obj-27", 0 ],
                                    "midpoints": [ 397.0, 191.0, 892.0, 191.0 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-26", 1 ],
                                    "destination": [ "obj-28", 0 ],
                                    "midpoints": [ 444.3333333333333, 191.0, 1057.0, 191.0 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-26", 2 ],
                                    "destination": [ "obj-29", 0 ],
                                    "midpoints": [ 491.6666666666667, 191.0, 1207.0, 191.0 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-30", 0 ],
                                    "destination": [ "obj-31", 0 ],
                                    "midpoints": [ 742.0, 246.0, 892.0, 246.0 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-31", 1 ],
                                    "destination": [ "obj-32", 0 ],
                                    "midpoints": [ 971.0, 281.0, 982.0, 281.0 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-32", 0 ],
                                    "destination": [ "obj-34", 0 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-34", 0 ],
                                    "destination": [ "obj-35", 0 ],
                                    "midpoints": [ 982.0, 371.0, 1072.0, 371.0 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-31", 0 ],
                                    "destination": [ "obj-33", 0 ],
                                    "midpoints": [ 892.0, 281.0, 1087.0, 281.0 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-33", 1 ],
                                    "destination": [ "obj-35", 0 ],
                                    "midpoints": [ 1159.0, 348.5, 1072.0, 348.5 ]
                                }
                            }
                        ],
                        "dependency_cache": [],
                        "autosave": 0
                    },
                    "saved_object_attributes": {
                        "description": "",
                        "digest": "",
                        "globalpatchername": "",
                        "tags": ""
                    }
                }
            },
            {
                "box": {
                    "maxclass": "dict.view",
                    "id": "obj-19",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "outlettype": [],
                    "patching_rect": [ 690.0, 990.0, 240, 436 ],
                    "parameter_enable": 0,
                    "presentation": 1,
                    "presentation_rect": [ 828.0, 62.0, 240.0, 436.0 ]
                }
            },
            {
                "box": {
                    "maxclass": "bpatcher",
                    "id": "obj-20",
                    "numinlets": 0,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 885.0, 1605.0, 300, 24 ],
                    "args": [ "x", "face.raw.x", "face.x", "face.cfg.x", 0.2, 0.8, 0.0, 1.0 ],
                    "bgmode": 0,
                    "border": 0,
                    "clickthrough": 0,
                    "enablehscroll": 0,
                    "enablevscroll": 0,
                    "lockeddragscroll": 0,
                    "offset": [ 0.0, 0.0 ],
                    "viewvisibility": 1,
                    "name": "ft.feature.maxpat",
                    "presentation": 1,
                    "presentation_rect": [ 512.0, 266.0, 300.0, 24.0 ]
                }
            },
            {
                "box": {
                    "maxclass": "bpatcher",
                    "id": "obj-21",
                    "numinlets": 0,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 885.0, 1650.0, 300, 24 ],
                    "args": [ "y", "face.raw.y", "face.y", "face.cfg.y", 0.2, 0.8, 0.0, 1.0 ],
                    "bgmode": 0,
                    "border": 0,
                    "clickthrough": 0,
                    "enablehscroll": 0,
                    "enablevscroll": 0,
                    "lockeddragscroll": 0,
                    "offset": [ 0.0, 0.0 ],
                    "viewvisibility": 1,
                    "name": "ft.feature.maxpat",
                    "presentation": 1,
                    "presentation_rect": [ 512.0, 292.0, 300.0, 24.0 ]
                }
            },
            {
                "box": {
                    "maxclass": "bpatcher",
                    "id": "obj-22",
                    "numinlets": 0,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 885.0, 1710.0, 300, 24 ],
                    "args": [ "size", "face.raw.size", "face.size", "face.cfg.size", 0.05, 0.3, 0.0, 1.0 ],
                    "bgmode": 0,
                    "border": 0,
                    "clickthrough": 0,
                    "enablehscroll": 0,
                    "enablevscroll": 0,
                    "lockeddragscroll": 0,
                    "offset": [ 0.0, 0.0 ],
                    "viewvisibility": 1,
                    "name": "ft.feature.maxpat",
                    "presentation": 1,
                    "presentation_rect": [ 512.0, 318.0, 300.0, 24.0 ]
                }
            },
            {
                "box": {
                    "maxclass": "bpatcher",
                    "id": "obj-23",
                    "numinlets": 0,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 885.0, 1755.0, 300, 24 ],
                    "args": [ "mouth", "face.raw.mouth", "face.mouth", "face.cfg.mouth", 0.5, 1.0, 0.0, 1.0 ],
                    "bgmode": 0,
                    "border": 0,
                    "clickthrough": 0,
                    "enablehscroll": 0,
                    "enablevscroll": 0,
                    "lockeddragscroll": 0,
                    "offset": [ 0.0, 0.0 ],
                    "viewvisibility": 1,
                    "name": "ft.feature.maxpat",
                    "presentation": 1,
                    "presentation_rect": [ 512.0, 344.0, 300.0, 24.0 ]
                }
            },
            {
                "box": {
                    "maxclass": "bpatcher",
                    "id": "obj-24",
                    "numinlets": 0,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 885.0, 1815.0, 300, 24 ],
                    "args": [ "blinkL", "face.raw.blinkL", "face.blinkL", "face.cfg.blinkL", 0.0, 1.0, 0.0, 1.0 ],
                    "bgmode": 0,
                    "border": 0,
                    "clickthrough": 0,
                    "enablehscroll": 0,
                    "enablevscroll": 0,
                    "lockeddragscroll": 0,
                    "offset": [ 0.0, 0.0 ],
                    "viewvisibility": 1,
                    "name": "ft.feature.maxpat",
                    "presentation": 1,
                    "presentation_rect": [ 512.0, 370.0, 300.0, 24.0 ]
                }
            },
            {
                "box": {
                    "maxclass": "bpatcher",
                    "id": "obj-25",
                    "numinlets": 0,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 1290.0, 1485.0, 300, 24 ],
                    "args": [ "blinkR", "face.raw.blinkR", "face.blinkR", "face.cfg.blinkR", 0.0, 1.0, 0.0, 1.0 ],
                    "bgmode": 0,
                    "border": 0,
                    "clickthrough": 0,
                    "enablehscroll": 0,
                    "enablevscroll": 0,
                    "lockeddragscroll": 0,
                    "offset": [ 0.0, 0.0 ],
                    "viewvisibility": 1,
                    "name": "ft.feature.maxpat",
                    "presentation": 1,
                    "presentation_rect": [ 512.0, 396.0, 300.0, 24.0 ]
                }
            },
            {
                "box": {
                    "maxclass": "bpatcher",
                    "id": "obj-26",
                    "numinlets": 0,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 1290.0, 1545.0, 300, 24 ],
                    "args": [ "yaw", "face.raw.yaw", "face.yaw", "face.cfg.yaw", -0.4, 0.4, -1.0, 1.0 ],
                    "bgmode": 0,
                    "border": 0,
                    "clickthrough": 0,
                    "enablehscroll": 0,
                    "enablevscroll": 0,
                    "lockeddragscroll": 0,
                    "offset": [ 0.0, 0.0 ],
                    "viewvisibility": 1,
                    "name": "ft.feature.maxpat",
                    "presentation": 1,
                    "presentation_rect": [ 512.0, 422.0, 300.0, 24.0 ]
                }
            },
            {
                "box": {
                    "maxclass": "bpatcher",
                    "id": "obj-27",
                    "numinlets": 0,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 1290.0, 1590.0, 300, 24 ],
                    "args": [ "pitch", "face.raw.pitch", "face.pitch", "face.cfg.pitch", 0.2, 0.7, -1.0, 1.0 ],
                    "bgmode": 0,
                    "border": 0,
                    "clickthrough": 0,
                    "enablehscroll": 0,
                    "enablevscroll": 0,
                    "lockeddragscroll": 0,
                    "offset": [ 0.0, 0.0 ],
                    "viewvisibility": 1,
                    "name": "ft.feature.maxpat",
                    "presentation": 1,
                    "presentation_rect": [ 512.0, 448.0, 300.0, 24.0 ]
                }
            },
            {
                "box": {
                    "maxclass": "bpatcher",
                    "id": "obj-28",
                    "numinlets": 0,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 1290.0, 1650.0, 300, 24 ],
                    "args": [ "roll", "face.raw.roll", "face.roll", "face.cfg.roll", -30.0, 30.0, -1.0, 1.0 ],
                    "bgmode": 0,
                    "border": 0,
                    "clickthrough": 0,
                    "enablehscroll": 0,
                    "enablevscroll": 0,
                    "lockeddragscroll": 0,
                    "offset": [ 0.0, 0.0 ],
                    "viewvisibility": 1,
                    "name": "ft.feature.maxpat",
                    "presentation": 1,
                    "presentation_rect": [ 512.0, 474.0, 300.0, 24.0 ]
                }
            },
            {
                "box": {
                    "maxclass": "umenu",
                    "id": "obj-29",
                    "numinlets": 1,
                    "numoutlets": 3,
                    "outlettype": [ "", "", "" ],
                    "patching_rect": [ 150.0, 90.0, 200, 22.0 ],
                    "parameter_enable": 0,
                    "presentation": 1,
                    "presentation_rect": [ 612.0, 62.0, 200.0, 22.0 ],
                    "items": [ "face (fast, CoreML)", ",", "facemesh (rich, web)" ]
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-30",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 615.0, 30.0, 87.5, 22.0 ],
                    "text": "loadmess 0",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-31",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "" ],
                    "patching_rect": [ 150.0, 120.0, 93.0, 22.0 ],
                    "text": "trigger i i",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-32",
                    "numinlets": 3,
                    "numoutlets": 3,
                    "outlettype": [ "", "", "" ],
                    "patching_rect": [ 405.0, 165.0, 86.0, 22.0 ],
                    "text": "select 0 1",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "message",
                    "id": "obj-33",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 600.0, 225.0, 230.0, 204.0 ],
                    "text": ";\rft.face.ctl debugdraw 1;\rft.mesh.ctl debugdraw 0;\rface.cfg.x range 0.2 0.8;\rface.cfg.y range 0.2 0.8;\rface.cfg.size range 0.05 0.3;\rface.cfg.mouth range 0.5 1.;\rface.cfg.blinkL range 0. 1.;\rface.cfg.blinkR range 0. 1.;\rface.cfg.yaw range -0.4 0.4;\rface.cfg.pitch range 0.2 0.7;\rface.cfg.roll range -30. 30.;\rface.raw.blinkL 0.;\rface.raw.blinkR 0.",
                    "fontname": "Arial",
                    "fontsize": 12.0,
                    "linecount": 14
                }
            },
            {
                "box": {
                    "maxclass": "message",
                    "id": "obj-34",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 885.0, 225.0, 230.0, 176.0 ],
                    "text": ";\rft.face.ctl debugdraw 0;\rft.mesh.ctl debugdraw 1;\rface.cfg.x range 0.2 0.8;\rface.cfg.y range 0.2 0.8;\rface.cfg.size range 0.15 0.6;\rface.cfg.mouth range 0. 0.6;\rface.cfg.blinkL range 0. 0.8;\rface.cfg.blinkR range 0. 0.8;\rface.cfg.yaw range -40. 40.;\rface.cfg.pitch range -25. 25.;\rface.cfg.roll range -30. 30.",
                    "fontname": "Arial",
                    "fontsize": 12.0,
                    "linecount": 12
                }
            },
            {
                "box": {
                    "maxclass": "comment",
                    "id": "obj-35",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "outlettype": [],
                    "patching_rect": [ 840.0, 225.0, 260.0, 20.0 ],
                    "text": "per-tracker overlay + default input ranges for every feature (tracker units differ)",
                    "fontname": "Arial",
                    "fontsize": 12.0,
                    "textcolor": [ 0.8, 0.8, 0.82, 1.0 ]
                }
            },
            {
                "box": {
                    "maxclass": "toggle",
                    "id": "obj-36",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 30.0, 90.0, 24.0, 24.0 ],
                    "parameter_enable": 0,
                    "presentation": 1,
                    "presentation_rect": [ 612.0, 88.0, 20.0, 20.0 ]
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-37",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 465.0, 30.0, 87.5, 22.0 ],
                    "text": "loadmess 1",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-38",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "" ],
                    "patching_rect": [ 30.0, 120.0, 93.0, 22.0 ],
                    "text": "trigger i i",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "message",
                    "id": "obj-39",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 285.0, 165.0, 79.0, 22.0 ],
                    "text": "mirror $1",
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
                    "patching_rect": [ 30.0, 165.0, 230.0, 50.0 ],
                    "text": ";\rft.face.ctl mirrored $1;\rft.mesh.ctl mirrored $1",
                    "fontname": "Arial",
                    "fontsize": 12.0,
                    "linecount": 3
                }
            },
            {
                "box": {
                    "maxclass": "comment",
                    "id": "obj-41",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "outlettype": [],
                    "patching_rect": [ 135.0, 120.0, 260.0, 20.0 ],
                    "text": "one switch flips the camera image and tells both trackers (keeps L/R the subject's own)",
                    "fontname": "Arial",
                    "fontsize": 12.0,
                    "textcolor": [ 0.8, 0.8, 0.82, 1.0 ]
                }
            },
            {
                "box": {
                    "maxclass": "toggle",
                    "id": "obj-42",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 1455.0, 90.0, 24.0, 24.0 ],
                    "parameter_enable": 0,
                    "presentation": 1,
                    "presentation_rect": [ 612.0, 112.0, 20.0, 20.0 ]
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-43",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 1455.0, 30.0, 87.5, 22.0 ],
                    "text": "loadmess 0",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-44",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 1455.0, 120.0, 107.0, 22.0 ],
                    "text": "prepend async",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-45",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "outlettype": [],
                    "patching_rect": [ 1455.0, 165.0, 128.0, 22.0 ],
                    "text": "send ft.face.ctl",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "flonum",
                    "id": "obj-46",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "" ],
                    "patching_rect": [ 240.0, 1530.0, 50.0, 22.0 ],
                    "parameter_enable": 0,
                    "presentation": 1,
                    "presentation_rect": [ 612.0, 136.0, 60.0, 22.0 ],
                    "minimum": 0.0,
                    "maximum": 0.99,
                    "numdecimalplaces": 2
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-47",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 240.0, 1485.0, 93.0, 22.0 ],
                    "text": "loadmess 0.",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "message",
                    "id": "obj-48",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 240.0, 1560.0, 230.0, 50.0 ],
                    "text": ";\rft.face.ctl smooth $1;\rft.mesh.ctl smooth $1",
                    "fontname": "Arial",
                    "fontsize": 12.0,
                    "linecount": 3
                }
            },
            {
                "box": {
                    "maxclass": "flonum",
                    "id": "obj-49",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "" ],
                    "patching_rect": [ 30.0, 1530.0, 50.0, 22.0 ],
                    "parameter_enable": 0,
                    "presentation": 1,
                    "presentation_rect": [ 612.0, 162.0, 60.0, 22.0 ],
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "numdecimalplaces": 2
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-50",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 30.0, 1485.0, 93.0, 22.0 ],
                    "text": "loadmess 0.",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-51",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 30.0, 1560.0, 163.0, 22.0 ],
                    "text": "prepend minconfidence",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-52",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "outlettype": [],
                    "patching_rect": [ 30.0, 1605.0, 128.0, 22.0 ],
                    "text": "send ft.face.ctl",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "toggle",
                    "id": "obj-53",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 510.0, 1545.0, 24.0, 24.0 ],
                    "parameter_enable": 0,
                    "presentation": 1,
                    "presentation_rect": [ 612.0, 190.0, 20.0, 20.0 ]
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-54",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 510.0, 1485.0, 87.5, 22.0 ],
                    "text": "loadmess 0",
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
                    "patching_rect": [ 510.0, 1575.0, 121.0, 22.0 ],
                    "text": "send face.learn",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "button",
                    "id": "obj-56",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 570.0, 30.0, 24.0, 24.0 ],
                    "parameter_enable": 0,
                    "presentation": 1,
                    "presentation_rect": [ 612.0, 214.0, 20.0, 20.0 ]
                }
            },
            {
                "box": {
                    "maxclass": "comment",
                    "id": "obj-57",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "outlettype": [],
                    "patching_rect": [ 600.0, 30.0, 260.0, 20.0 ],
                    "text": "reset ranges = re-send the current tracker's defaults",
                    "fontname": "Arial",
                    "fontsize": 12.0,
                    "textcolor": [ 0.8, 0.8, 0.82, 1.0 ]
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-58",
                    "numinlets": 0,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 675.0, 1485.0, 163.0, 22.0 ],
                    "text": "receive face.detected",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "toggle",
                    "id": "obj-59",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 675.0, 1530.0, 24.0, 24.0 ],
                    "parameter_enable": 0,
                    "presentation": 1,
                    "presentation_rect": [ 370.0, 320.0, 20.0, 20.0 ],
                    "ignoreclick": 1
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-60",
                    "numinlets": 2,
                    "numoutlets": 0,
                    "outlettype": [],
                    "patching_rect": [ 1200.0, 225.0, 86.0, 22.0 ],
                    "text": "p sonify",
                    "fontname": "Arial",
                    "fontsize": 12.0,
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
                        "rect": [ 100.0, 100.0, 400.0, 300.0 ],
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
                                    "maxclass": "inlet",
                                    "id": "obj-1",
                                    "numinlets": 0,
                                    "numoutlets": 1,
                                    "outlettype": [ "" ],
                                    "patching_rect": [ 30.0, 30.0, 30.0, 30.0 ],
                                    "parameter_enable": 0,
                                    "comment": "audio on/off (0/1)"
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "inlet",
                                    "id": "obj-2",
                                    "numinlets": 0,
                                    "numoutlets": 1,
                                    "outlettype": [ "" ],
                                    "patching_rect": [ 75.0, 30.0, 30.0, 30.0 ],
                                    "parameter_enable": 0,
                                    "comment": "master gain 0-1"
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "newobj",
                                    "id": "obj-3",
                                    "numinlets": 2,
                                    "numoutlets": 0,
                                    "outlettype": [],
                                    "patching_rect": [ 285.0, 420.0, 72.0, 22.0 ],
                                    "text": "dac~ 1 2",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "message",
                                    "id": "obj-4",
                                    "numinlets": 2,
                                    "numoutlets": 1,
                                    "outlettype": [ "" ],
                                    "patching_rect": [ 75.0, 75.0, 51.0, 22.0 ],
                                    "text": "$1 50",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "newobj",
                                    "id": "obj-5",
                                    "numinlets": 2,
                                    "numoutlets": 2,
                                    "outlettype": [ "signal", "" ],
                                    "patching_rect": [ 75.0, 120.0, 51.0, 22.0 ],
                                    "text": "line~",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "newobj",
                                    "id": "obj-6",
                                    "numinlets": 0,
                                    "numoutlets": 1,
                                    "outlettype": [ "" ],
                                    "patching_rect": [ 915.0, 30.0, 142.0, 22.0 ],
                                    "text": "receive face.mouth",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "newobj",
                                    "id": "obj-7",
                                    "numinlets": 1,
                                    "numoutlets": 1,
                                    "outlettype": [ "" ],
                                    "patching_rect": [ 915.0, 75.0, 184.0, 22.0 ],
                                    "text": "expr 200.*pow(20.\\, $f1)",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "message",
                                    "id": "obj-8",
                                    "numinlets": 2,
                                    "numoutlets": 1,
                                    "outlettype": [ "" ],
                                    "patching_rect": [ 1215.0, 120.0, 51.0, 22.0 ],
                                    "text": "$1 40",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "newobj",
                                    "id": "obj-9",
                                    "numinlets": 2,
                                    "numoutlets": 2,
                                    "outlettype": [ "signal", "" ],
                                    "patching_rect": [ 1215.0, 165.0, 51.0, 22.0 ],
                                    "text": "line~",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "newobj",
                                    "id": "obj-10",
                                    "numinlets": 0,
                                    "numoutlets": 1,
                                    "outlettype": [ "" ],
                                    "patching_rect": [ 1080.0, 30.0, 142.0, 22.0 ],
                                    "text": "receive face.pitch",
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
                                    "patching_rect": [ 1125.0, 75.0, 205.0, 22.0 ],
                                    "text": "expr 110.*pow(2.\\, $f1/12.)",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "message",
                                    "id": "obj-12",
                                    "numinlets": 2,
                                    "numoutlets": 1,
                                    "outlettype": [ "" ],
                                    "patching_rect": [ 1305.0, 120.0, 51.0, 22.0 ],
                                    "text": "$1 40",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "newobj",
                                    "id": "obj-13",
                                    "numinlets": 2,
                                    "numoutlets": 2,
                                    "outlettype": [ "signal", "" ],
                                    "patching_rect": [ 1305.0, 165.0, 51.0, 22.0 ],
                                    "text": "line~",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "newobj",
                                    "id": "obj-14",
                                    "numinlets": 2,
                                    "numoutlets": 1,
                                    "outlettype": [ "signal" ],
                                    "patching_rect": [ 345.0, 30.0, 72.0, 22.0 ],
                                    "text": "saw~ 110",
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
                                    "patching_rect": [ 1305.0, 210.0, 72.0, 22.0 ],
                                    "text": "saw~ 110",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "newobj",
                                    "id": "obj-16",
                                    "numinlets": 3,
                                    "numoutlets": 1,
                                    "outlettype": [ "signal" ],
                                    "patching_rect": [ 945.0, 255.0, 144.5, 22.0 ],
                                    "text": "lores~ 1000 0.5",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "newobj",
                                    "id": "obj-17",
                                    "numinlets": 2,
                                    "numoutlets": 1,
                                    "outlettype": [ "signal" ],
                                    "patching_rect": [ 945.0, 285.0, 58.0, 22.0 ],
                                    "text": "*~ 0.2",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "newobj",
                                    "id": "obj-18",
                                    "numinlets": 0,
                                    "numoutlets": 1,
                                    "outlettype": [ "" ],
                                    "patching_rect": [ 750.0, 30.0, 149.0, 22.0 ],
                                    "text": "receive face.blinkL",
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
                                    "patching_rect": [ 750.0, 75.0, 72.0, 22.0 ],
                                    "text": "past 0.5",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "message",
                                    "id": "obj-20",
                                    "numinlets": 2,
                                    "numoutlets": 1,
                                    "outlettype": [ "" ],
                                    "patching_rect": [ 1095.0, 120.0, 79.0, 22.0 ],
                                    "text": "1, 0. 400",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "newobj",
                                    "id": "obj-21",
                                    "numinlets": 2,
                                    "numoutlets": 2,
                                    "outlettype": [ "signal", "" ],
                                    "patching_rect": [ 1095.0, 165.0, 51.0, 22.0 ],
                                    "text": "line~",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "newobj",
                                    "id": "obj-22",
                                    "numinlets": 2,
                                    "numoutlets": 1,
                                    "outlettype": [ "signal" ],
                                    "patching_rect": [ 240.0, 30.0, 86.0, 22.0 ],
                                    "text": "cycle~ 880",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "newobj",
                                    "id": "obj-23",
                                    "numinlets": 2,
                                    "numoutlets": 1,
                                    "outlettype": [ "signal" ],
                                    "patching_rect": [ 690.0, 210.0, 42.0, 22.0 ],
                                    "text": "*~",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "newobj",
                                    "id": "obj-24",
                                    "numinlets": 2,
                                    "numoutlets": 1,
                                    "outlettype": [ "signal" ],
                                    "patching_rect": [ 690.0, 255.0, 65.0, 22.0 ],
                                    "text": "*~ 0.15",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "newobj",
                                    "id": "obj-25",
                                    "numinlets": 0,
                                    "numoutlets": 1,
                                    "outlettype": [ "" ],
                                    "patching_rect": [ 585.0, 30.0, 149.0, 22.0 ],
                                    "text": "receive face.blinkR",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "newobj",
                                    "id": "obj-26",
                                    "numinlets": 1,
                                    "numoutlets": 1,
                                    "outlettype": [ "" ],
                                    "patching_rect": [ 585.0, 75.0, 72.0, 22.0 ],
                                    "text": "past 0.5",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "message",
                                    "id": "obj-27",
                                    "numinlets": 2,
                                    "numoutlets": 1,
                                    "outlettype": [ "" ],
                                    "patching_rect": [ 975.0, 120.0, 79.0, 22.0 ],
                                    "text": "1, 0. 400",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "newobj",
                                    "id": "obj-28",
                                    "numinlets": 2,
                                    "numoutlets": 2,
                                    "outlettype": [ "signal", "" ],
                                    "patching_rect": [ 975.0, 165.0, 51.0, 22.0 ],
                                    "text": "line~",
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
                                    "outlettype": [ "signal" ],
                                    "patching_rect": [ 120.0, 30.0, 93.0, 22.0 ],
                                    "text": "cycle~ 1320",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "newobj",
                                    "id": "obj-30",
                                    "numinlets": 2,
                                    "numoutlets": 1,
                                    "outlettype": [ "signal" ],
                                    "patching_rect": [ 540.0, 210.0, 42.0, 22.0 ],
                                    "text": "*~",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "newobj",
                                    "id": "obj-31",
                                    "numinlets": 2,
                                    "numoutlets": 1,
                                    "outlettype": [ "signal" ],
                                    "patching_rect": [ 540.0, 255.0, 65.0, 22.0 ],
                                    "text": "*~ 0.15",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "newobj",
                                    "id": "obj-32",
                                    "numinlets": 0,
                                    "numoutlets": 1,
                                    "outlettype": [ "" ],
                                    "patching_rect": [ 435.0, 30.0, 128.0, 22.0 ],
                                    "text": "receive face.yaw",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "newobj",
                                    "id": "obj-33",
                                    "numinlets": 1,
                                    "numoutlets": 2,
                                    "outlettype": [ "", "" ],
                                    "patching_rect": [ 435.0, 75.0, 93.0, 22.0 ],
                                    "text": "trigger f f",
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
                                    "outlettype": [ "" ],
                                    "patching_rect": [ 750.0, 120.0, 205.0, 22.0 ],
                                    "text": "expr cos(($f1+1.)*0.785398)",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "newobj",
                                    "id": "obj-35",
                                    "numinlets": 1,
                                    "numoutlets": 1,
                                    "outlettype": [ "" ],
                                    "patching_rect": [ 525.0, 120.0, 205.0, 22.0 ],
                                    "text": "expr sin(($f1+1.)*0.785398)",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "message",
                                    "id": "obj-36",
                                    "numinlets": 2,
                                    "numoutlets": 1,
                                    "outlettype": [ "" ],
                                    "patching_rect": [ 840.0, 165.0, 51.0, 22.0 ],
                                    "text": "$1 40",
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
                                    "patching_rect": [ 615.0, 165.0, 51.0, 22.0 ],
                                    "text": "$1 40",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "newobj",
                                    "id": "obj-38",
                                    "numinlets": 2,
                                    "numoutlets": 2,
                                    "outlettype": [ "signal", "" ],
                                    "patching_rect": [ 840.0, 210.0, 51.0, 22.0 ],
                                    "text": "line~",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "newobj",
                                    "id": "obj-39",
                                    "numinlets": 2,
                                    "numoutlets": 2,
                                    "outlettype": [ "signal", "" ],
                                    "patching_rect": [ 615.0, 210.0, 51.0, 22.0 ],
                                    "text": "line~",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "newobj",
                                    "id": "obj-40",
                                    "numinlets": 2,
                                    "numoutlets": 1,
                                    "outlettype": [ "signal" ],
                                    "patching_rect": [ 765.0, 330.0, 42.0, 22.0 ],
                                    "text": "*~",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "newobj",
                                    "id": "obj-41",
                                    "numinlets": 2,
                                    "numoutlets": 1,
                                    "outlettype": [ "signal" ],
                                    "patching_rect": [ 705.0, 330.0, 42.0, 22.0 ],
                                    "text": "*~",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "newobj",
                                    "id": "obj-42",
                                    "numinlets": 2,
                                    "numoutlets": 1,
                                    "outlettype": [ "signal" ],
                                    "patching_rect": [ 450.0, 375.0, 42.0, 22.0 ],
                                    "text": "*~",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "newobj",
                                    "id": "obj-43",
                                    "numinlets": 2,
                                    "numoutlets": 1,
                                    "outlettype": [ "signal" ],
                                    "patching_rect": [ 390.0, 375.0, 42.0, 22.0 ],
                                    "text": "*~",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "comment",
                                    "id": "obj-44",
                                    "numinlets": 1,
                                    "numoutlets": 0,
                                    "outlettype": [],
                                    "patching_rect": [ 1095.0, 255.0, 260.0, 20.0 ],
                                    "text": "mouth -> cutoff 200-4000 Hz, pitch -> detune +/-1 semitone, yaw -> constant-power pan, blink L/R -> pings",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "comment",
                                    "id": "obj-45",
                                    "numinlets": 1,
                                    "numoutlets": 0,
                                    "outlettype": [],
                                    "patching_rect": [ 960.0, 120.0, 296.0, 20.0 ],
                                    "text": "pan~ is RNBO-only: cos/sin gains instead",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            }
                        ],
                        "lines": [
                            {
                                "patchline": {
                                    "source": [ "obj-1", 0 ],
                                    "destination": [ "obj-3", 0 ],
                                    "midpoints": [ 37.0, 66.0, 292.0, 66.0 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-2", 0 ],
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
                                    "source": [ "obj-6", 0 ],
                                    "destination": [ "obj-7", 0 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-7", 0 ],
                                    "destination": [ "obj-8", 0 ],
                                    "midpoints": [ 922.0, 108.5, 1222.0, 108.5 ]
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
                                    "source": [ "obj-9", 0 ],
                                    "destination": [ "obj-16", 1 ],
                                    "midpoints": [ 1222.0, 193.0, 1017.25, 193.0 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-10", 0 ],
                                    "destination": [ "obj-11", 0 ],
                                    "midpoints": [ 1087.0, 58.0, 1132.0, 58.0 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-11", 0 ],
                                    "destination": [ "obj-12", 0 ],
                                    "midpoints": [ 1132.0, 103.0, 1312.0, 103.0 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-12", 0 ],
                                    "destination": [ "obj-13", 0 ]
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
                                    "destination": [ "obj-16", 0 ],
                                    "midpoints": [ 352.0, 146.0, 952.0, 146.0 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-15", 0 ],
                                    "destination": [ "obj-16", 0 ],
                                    "midpoints": [ 1312.0, 238.0, 952.0, 238.0 ]
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
                                    "source": [ "obj-18", 0 ],
                                    "destination": [ "obj-19", 0 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-19", 0 ],
                                    "destination": [ "obj-20", 0 ],
                                    "midpoints": [ 757.0, 108.5, 1102.0, 108.5 ]
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
                                    "source": [ "obj-22", 0 ],
                                    "destination": [ "obj-23", 0 ],
                                    "midpoints": [ 247.0, 146.0, 697.0, 146.0 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-21", 0 ],
                                    "destination": [ "obj-23", 1 ],
                                    "midpoints": [ 1102.0, 193.0, 725.0, 193.0 ]
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
                                    "source": [ "obj-25", 0 ],
                                    "destination": [ "obj-26", 0 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-26", 0 ],
                                    "destination": [ "obj-27", 0 ],
                                    "midpoints": [ 592.0, 108.5, 982.0, 108.5 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-27", 0 ],
                                    "destination": [ "obj-28", 0 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-29", 0 ],
                                    "destination": [ "obj-30", 0 ],
                                    "midpoints": [ 127.0, 58.0, 339.0, 58.0, 339.0, 204.0, 547.0, 204.0 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-28", 0 ],
                                    "destination": [ "obj-30", 1 ],
                                    "midpoints": [ 982.0, 193.0, 575.0, 193.0 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-30", 0 ],
                                    "destination": [ "obj-31", 0 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-32", 0 ],
                                    "destination": [ "obj-33", 0 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-33", 1 ],
                                    "destination": [ "obj-35", 0 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-33", 0 ],
                                    "destination": [ "obj-34", 0 ],
                                    "midpoints": [ 442.0, 103.0, 757.0, 103.0 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-34", 0 ],
                                    "destination": [ "obj-36", 0 ],
                                    "midpoints": [ 757.0, 153.5, 847.0, 153.5 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-36", 0 ],
                                    "destination": [ "obj-38", 0 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-35", 0 ],
                                    "destination": [ "obj-37", 0 ],
                                    "midpoints": [ 532.0, 153.5, 622.0, 153.5 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-37", 0 ],
                                    "destination": [ "obj-39", 0 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-17", 0 ],
                                    "destination": [ "obj-40", 0 ],
                                    "midpoints": [ 952.0, 318.5, 772.0, 318.5 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-17", 0 ],
                                    "destination": [ "obj-41", 0 ],
                                    "midpoints": [ 952.0, 315.0, 712.0, 315.0 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-24", 0 ],
                                    "destination": [ "obj-40", 0 ],
                                    "midpoints": [ 697.0, 281.0, 772.0, 281.0 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-24", 0 ],
                                    "destination": [ "obj-41", 0 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-31", 0 ],
                                    "destination": [ "obj-40", 0 ],
                                    "midpoints": [ 547.0, 281.0, 772.0, 281.0 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-31", 0 ],
                                    "destination": [ "obj-41", 0 ],
                                    "midpoints": [ 547.0, 281.0, 712.0, 281.0 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-38", 0 ],
                                    "destination": [ "obj-40", 1 ],
                                    "midpoints": [ 847.0, 281.0, 800.0, 281.0 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-39", 0 ],
                                    "destination": [ "obj-41", 1 ],
                                    "midpoints": [ 622.0, 281.0, 740.0, 281.0 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-40", 0 ],
                                    "destination": [ "obj-42", 0 ],
                                    "midpoints": [ 772.0, 358.0, 457.0, 358.0 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-41", 0 ],
                                    "destination": [ "obj-43", 0 ],
                                    "midpoints": [ 712.0, 358.0, 397.0, 358.0 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-5", 0 ],
                                    "destination": [ "obj-42", 1 ],
                                    "midpoints": [ 82.0, 146.0, 485.0, 146.0 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-5", 0 ],
                                    "destination": [ "obj-43", 1 ],
                                    "midpoints": [ 82.0, 258.5, 425.0, 258.5 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-42", 0 ],
                                    "destination": [ "obj-3", 0 ],
                                    "midpoints": [ 457.0, 403.0, 292.0, 403.0 ]
                                }
                            },
                            {
                                "patchline": {
                                    "source": [ "obj-43", 0 ],
                                    "destination": [ "obj-3", 1 ],
                                    "midpoints": [ 397.0, 408.5, 350.0, 408.5 ]
                                }
                            }
                        ],
                        "dependency_cache": [],
                        "autosave": 0
                    },
                    "saved_object_attributes": {
                        "description": "",
                        "digest": "",
                        "globalpatchername": "",
                        "tags": ""
                    }
                }
            },
            {
                "box": {
                    "maxclass": "toggle",
                    "id": "obj-61",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 1200.0, 195.0, 24.0, 24.0 ],
                    "parameter_enable": 0,
                    "presentation": 1,
                    "presentation_rect": [ 16.0, 408.0, 20.0, 20.0 ]
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-62",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 1320.0, 30.0, 87.5, 22.0 ],
                    "text": "loadmess 0",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "slider",
                    "id": "obj-63",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 1245.0, 75.0, 20.0, 140.0 ],
                    "parameter_enable": 0,
                    "presentation": 1,
                    "presentation_rect": [ 120.0, 410.0, 150.0, 18.0 ],
                    "floatoutput": 1,
                    "size": 1.0,
                    "orientation": 1
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-64",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 1200.0, 30.0, 100.0, 22.0 ],
                    "text": "loadmess 0.5",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "comment",
                    "id": "obj-65",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "outlettype": [],
                    "patching_rect": [ 75.0, 225.0, 471.0, 20.0 ],
                    "text": "face-tracker  ·  jit.vis face tracking (Vision package, Max 9.2+)",
                    "fontname": "Arial",
                    "fontsize": 16.0,
                    "presentation": 1,
                    "presentation_rect": [ 16.0, 8.0, 600.0, 24.0 ],
                    "textcolor": [ 0.8, 0.8, 0.82, 1.0 ]
                }
            },
            {
                "box": {
                    "maxclass": "comment",
                    "id": "obj-66",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "outlettype": [],
                    "patching_rect": [ 75.0, 225.0, 107.0, 20.0 ],
                    "text": "face detected",
                    "fontname": "Arial",
                    "fontsize": 12.0,
                    "presentation": 1,
                    "presentation_rect": [ 394.0, 320.0, 100.0, 20.0 ],
                    "textcolor": [ 0.8, 0.8, 0.82, 1.0 ]
                }
            },
            {
                "box": {
                    "maxclass": "comment",
                    "id": "obj-67",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "outlettype": [],
                    "patching_rect": [ 75.0, 225.0, 107.0, 20.0 ],
                    "text": "SONIFY (demo)",
                    "fontname": "Arial",
                    "fontsize": 12.0,
                    "presentation": 1,
                    "presentation_rect": [ 16.0, 384.0, 200.0, 20.0 ],
                    "textcolor": [ 0.8, 0.8, 0.82, 1.0 ]
                }
            },
            {
                "box": {
                    "maxclass": "comment",
                    "id": "obj-68",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "outlettype": [],
                    "patching_rect": [ 75.0, 225.0, 72.0, 20.0 ],
                    "text": "audio on",
                    "fontname": "Arial",
                    "fontsize": 12.0,
                    "presentation": 1,
                    "presentation_rect": [ 40.0, 408.0, 70.0, 20.0 ],
                    "textcolor": [ 0.8, 0.8, 0.82, 1.0 ]
                }
            },
            {
                "box": {
                    "maxclass": "comment",
                    "id": "obj-69",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "outlettype": [],
                    "patching_rect": [ 75.0, 225.0, 44.0, 20.0 ],
                    "text": "gain",
                    "fontname": "Arial",
                    "fontsize": 12.0,
                    "presentation": 1,
                    "presentation_rect": [ 276.0, 408.0, 40.0, 20.0 ],
                    "textcolor": [ 0.8, 0.8, 0.82, 1.0 ]
                }
            },
            {
                "box": {
                    "maxclass": "comment",
                    "id": "obj-70",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "outlettype": [],
                    "patching_rect": [ 75.0, 225.0, 485.0, 20.0 ],
                    "text": "mouth -> filter · yaw -> pan · pitch -> detune · blink L/R -> pings",
                    "fontname": "Arial",
                    "fontsize": 12.0,
                    "presentation": 1,
                    "presentation_rect": [ 16.0, 434.0, 480.0, 20.0 ],
                    "textcolor": [ 0.8, 0.8, 0.82, 1.0 ]
                }
            },
            {
                "box": {
                    "maxclass": "comment",
                    "id": "obj-71",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "outlettype": [],
                    "patching_rect": [ 75.0, 225.0, 480, 20.0 ],
                    "text": "receive face.x face.y face.size face.mouth face.blinkL face.blinkR face.yaw face.pitch face.roll (0-1, angles -1..1) · face.raw.<name> = tracker units · face.bs.<blendshape> (facemesh) · face.detected",
                    "fontname": "Arial",
                    "fontsize": 12.0,
                    "presentation": 1,
                    "presentation_rect": [ 16.0, 464.0, 480.0, 48.0 ],
                    "textcolor": [ 0.8, 0.8, 0.82, 1.0 ]
                }
            },
            {
                "box": {
                    "maxclass": "comment",
                    "id": "obj-72",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "outlettype": [],
                    "patching_rect": [ 75.0, 225.0, 65.0, 20.0 ],
                    "text": "TRACKER",
                    "fontname": "Arial",
                    "fontsize": 12.0,
                    "presentation": 1,
                    "presentation_rect": [ 512.0, 40.0, 200.0, 20.0 ],
                    "textcolor": [ 0.8, 0.8, 0.82, 1.0 ]
                }
            },
            {
                "box": {
                    "maxclass": "comment",
                    "id": "obj-73",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "outlettype": [],
                    "patching_rect": [ 75.0, 225.0, 65.0, 20.0 ],
                    "text": "tracker",
                    "fontname": "Arial",
                    "fontsize": 12.0,
                    "presentation": 1,
                    "presentation_rect": [ 512.0, 62.0, 96.0, 20.0 ],
                    "textcolor": [ 0.8, 0.8, 0.82, 1.0 ]
                }
            },
            {
                "box": {
                    "maxclass": "comment",
                    "id": "obj-74",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "outlettype": [],
                    "patching_rect": [ 75.0, 225.0, 121.0, 20.0 ],
                    "text": "mirror (selfie)",
                    "fontname": "Arial",
                    "fontsize": 12.0,
                    "presentation": 1,
                    "presentation_rect": [ 512.0, 88.0, 96.0, 20.0 ],
                    "textcolor": [ 0.8, 0.8, 0.82, 1.0 ]
                }
            },
            {
                "box": {
                    "maxclass": "comment",
                    "id": "obj-75",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "outlettype": [],
                    "patching_rect": [ 75.0, 225.0, 128.0, 20.0 ],
                    "text": "async (adds lag)",
                    "fontname": "Arial",
                    "fontsize": 12.0,
                    "presentation": 1,
                    "presentation_rect": [ 512.0, 112.0, 96.0, 20.0 ],
                    "textcolor": [ 0.8, 0.8, 0.82, 1.0 ]
                }
            },
            {
                "box": {
                    "maxclass": "comment",
                    "id": "obj-76",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "outlettype": [],
                    "patching_rect": [ 75.0, 225.0, 107.0, 20.0 ],
                    "text": "smooth 0-0.99",
                    "fontname": "Arial",
                    "fontsize": 12.0,
                    "presentation": 1,
                    "presentation_rect": [ 512.0, 136.0, 96.0, 20.0 ],
                    "textcolor": [ 0.8, 0.8, 0.82, 1.0 ]
                }
            },
            {
                "box": {
                    "maxclass": "comment",
                    "id": "obj-77",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "outlettype": [],
                    "patching_rect": [ 75.0, 225.0, 114.0, 20.0 ],
                    "text": "min confidence",
                    "fontname": "Arial",
                    "fontsize": 12.0,
                    "presentation": 1,
                    "presentation_rect": [ 512.0, 162.0, 96.0, 20.0 ],
                    "textcolor": [ 0.8, 0.8, 0.82, 1.0 ]
                }
            },
            {
                "box": {
                    "maxclass": "comment",
                    "id": "obj-78",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "outlettype": [],
                    "patching_rect": [ 75.0, 225.0, 100.0, 20.0 ],
                    "text": "learn ranges",
                    "fontname": "Arial",
                    "fontsize": 12.0,
                    "presentation": 1,
                    "presentation_rect": [ 512.0, 190.0, 96.0, 20.0 ],
                    "textcolor": [ 0.8, 0.8, 0.82, 1.0 ]
                }
            },
            {
                "box": {
                    "maxclass": "comment",
                    "id": "obj-79",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "outlettype": [],
                    "patching_rect": [ 75.0, 225.0, 100.0, 20.0 ],
                    "text": "reset ranges",
                    "fontname": "Arial",
                    "fontsize": 12.0,
                    "presentation": 1,
                    "presentation_rect": [ 512.0, 214.0, 96.0, 20.0 ],
                    "textcolor": [ 0.8, 0.8, 0.82, 1.0 ]
                }
            },
            {
                "box": {
                    "maxclass": "comment",
                    "id": "obj-80",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "outlettype": [],
                    "patching_rect": [ 75.0, 225.0, 436.0, 20.0 ],
                    "text": "FEATURES          raw              normalized -> face.<name>",
                    "fontname": "Arial",
                    "fontsize": 12.0,
                    "presentation": 1,
                    "presentation_rect": [ 512.0, 244.0, 300.0, 20.0 ],
                    "textcolor": [ 0.8, 0.8, 0.82, 1.0 ]
                }
            },
            {
                "box": {
                    "maxclass": "comment",
                    "id": "obj-81",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "outlettype": [],
                    "patching_rect": [ 75.0, 225.0, 296.0, 20.0 ],
                    "text": "BLENDSHAPES (facemesh) -> face.bs.<name>",
                    "fontname": "Arial",
                    "fontsize": 12.0,
                    "presentation": 1,
                    "presentation_rect": [ 828.0, 40.0, 260.0, 20.0 ],
                    "textcolor": [ 0.8, 0.8, 0.82, 1.0 ]
                }
            }
        ],
        "lines": [
            {
                "patchline": {
                    "source": [ "obj-2", 0 ],
                    "destination": [ "obj-1", 0 ],
                    "midpoints": [ 37.0, 138.5, 82.0, 138.5 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-1", 0 ],
                    "destination": [ "obj-3", 0 ],
                    "midpoints": [ 82.0, 372.5, 172.0, 372.5 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-3", 1 ],
                    "destination": [ "obj-6", 1 ],
                    "midpoints": [ 251.0, 498.5, 845.0, 498.5 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-3", 0 ],
                    "destination": [ "obj-4", 0 ],
                    "midpoints": [ 172.0, 498.5, 37.0, 498.5 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-4", 0 ],
                    "destination": [ "obj-5", 0 ],
                    "midpoints": [ 37.0, 543.5, 172.0, 543.5 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-6", 0 ],
                    "destination": [ "obj-8", 0 ],
                    "midpoints": [ 787.0, 693.5, 37.0, 693.5 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-6", 1 ],
                    "destination": [ "obj-9", 0 ],
                    "midpoints": [ 845.0, 543.5, 667.0, 543.5 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-10", 0 ],
                    "destination": [ "obj-8", 0 ],
                    "midpoints": [ 307.0, 56.0, 24.0, 56.0, 24.0, 847.0, 37.0, 847.0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-11", 0 ],
                    "destination": [ "obj-9", 0 ],
                    "midpoints": [ 142.0, 56.0, 24.0, 56.0, 24.0, 549.0, 667.0, 549.0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-8", 0 ],
                    "destination": [ "obj-13", 0 ],
                    "midpoints": [ 37.0, 888.5, 307.0, 888.5 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-13", 1 ],
                    "destination": [ "obj-12", 0 ],
                    "midpoints": [ 386.0, 928.0, 502.0, 928.0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-9", 0 ],
                    "destination": [ "obj-14", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-14", 1 ],
                    "destination": [ "obj-12", 0 ],
                    "midpoints": [ 746.0, 928.0, 502.0, 928.0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-13", 0 ],
                    "destination": [ "obj-17", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-14", 0 ],
                    "destination": [ "obj-18", 0 ],
                    "midpoints": [ 667.0, 933.5, 742.0, 933.5 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-9", 1 ],
                    "destination": [ "obj-18", 1 ],
                    "midpoints": [ 899.0, 761.0, 877.0, 761.0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-18", 0 ],
                    "destination": [ "obj-19", 0 ],
                    "midpoints": [ 742.0, 978.5, 697.0, 978.5 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-30", 0 ],
                    "destination": [ "obj-29", 0 ],
                    "midpoints": [ 622.0, 71.0, 157.0, 71.0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-29", 0 ],
                    "destination": [ "obj-31", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-31", 1 ],
                    "destination": [ "obj-32", 0 ],
                    "midpoints": [ 236.0, 153.5, 412.0, 153.5 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-32", 0 ],
                    "destination": [ "obj-33", 0 ],
                    "midpoints": [ 412.0, 193.0, 607.0, 193.0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-32", 1 ],
                    "destination": [ "obj-34", 0 ],
                    "midpoints": [ 448.0, 206.0, 892.0, 206.0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-31", 0 ],
                    "destination": [ "obj-7", 0 ],
                    "midpoints": [ 157.0, 153.5, 517.0, 153.5 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-7", 0 ],
                    "destination": [ "obj-6", 0 ],
                    "midpoints": [ 517.0, 348.5, 787.0, 348.5 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-37", 0 ],
                    "destination": [ "obj-36", 0 ],
                    "midpoints": [ 472.0, 56.0, 37.0, 56.0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-36", 0 ],
                    "destination": [ "obj-38", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-38", 1 ],
                    "destination": [ "obj-40", 0 ],
                    "midpoints": [ 116.0, 153.5, 37.0, 153.5 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-38", 0 ],
                    "destination": [ "obj-39", 0 ],
                    "midpoints": [ 37.0, 146.0, 292.0, 146.0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-39", 0 ],
                    "destination": [ "obj-1", 0 ],
                    "midpoints": [ 292.0, 206.0, 82.0, 206.0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-43", 0 ],
                    "destination": [ "obj-42", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-42", 0 ],
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
                    "source": [ "obj-47", 0 ],
                    "destination": [ "obj-46", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-46", 0 ],
                    "destination": [ "obj-48", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-50", 0 ],
                    "destination": [ "obj-49", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-49", 0 ],
                    "destination": [ "obj-51", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-51", 0 ],
                    "destination": [ "obj-52", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-54", 0 ],
                    "destination": [ "obj-53", 0 ]
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
                    "source": [ "obj-56", 0 ],
                    "destination": [ "obj-29", 0 ],
                    "midpoints": [ 577.0, 58.0, 157.0, 58.0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-58", 0 ],
                    "destination": [ "obj-59", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-62", 0 ],
                    "destination": [ "obj-61", 0 ],
                    "midpoints": [ 1327.0, 56.0, 1207.0, 56.0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-61", 0 ],
                    "destination": [ "obj-60", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-64", 0 ],
                    "destination": [ "obj-63", 0 ],
                    "midpoints": [ 1207.0, 63.5, 1252.0, 63.5 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-63", 0 ],
                    "destination": [ "obj-60", 1 ],
                    "midpoints": [ 1252.0, 220.0, 1279.0, 220.0 ]
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