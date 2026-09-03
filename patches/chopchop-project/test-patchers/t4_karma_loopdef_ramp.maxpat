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
    "rect": [
      80.0,
      80.0,
      1200.0,
      800.0
    ],
    "bglocked": 0,
    "openinpresentation": 0,
    "default_fontsize": 12.0,
    "default_fontface": 0,
    "default_fontname": "Arial",
    "gridonopen": 1,
    "gridsize": [
      15.0,
      15.0
    ],
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
    "locked": 1,
    "boxes": [
      {
        "box": {
          "maxclass": "newobj",
          "text": "buffer~ tbuf 12000 2",
          "numinlets": 2,
          "numoutlets": 1,
          "outlettype": [
            ""
          ],
          "patching_rect": [
            40.0,
            50.0,
            120.0,
            22.0
          ],
          "id": "obj-2"
        }
      },
      {
        "box": {
          "maxclass": "comment",
          "text": "T4  --  a karma~ is recording a rolling capture. Define a shorter loop from it: compare  (a) window 0.5   vs   (b) stop -> position/window -> play.  Then sweep ramp/snramp 16 -> 200 and listen at the seam.",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            40.0,
            10.0,
            900.0,
            20.0
          ],
          "id": "obj-1"
        }
      },
      {
        "box": {
          "maxclass": "newobj",
          "text": "cycle~ 200",
          "numinlets": 2,
          "numoutlets": 1,
          "outlettype": [
            ""
          ],
          "patching_rect": [
            40.0,
            100.0,
            120.0,
            22.0
          ],
          "id": "obj-3"
        }
      },
      {
        "box": {
          "maxclass": "newobj",
          "text": "*~ 0.4",
          "numinlets": 2,
          "numoutlets": 1,
          "outlettype": [
            ""
          ],
          "patching_rect": [
            40.0,
            140.0,
            120.0,
            22.0
          ],
          "id": "obj-4"
        }
      },
      {
        "box": {
          "maxclass": "newobj",
          "text": "sig~ 1.",
          "numinlets": 1,
          "numoutlets": 1,
          "outlettype": [
            ""
          ],
          "patching_rect": [
            220.0,
            100.0,
            120.0,
            22.0
          ],
          "id": "obj-5"
        }
      },
      {
        "box": {
          "maxclass": "newobj",
          "text": "karma~ tbuf 2",
          "numinlets": 3,
          "numoutlets": 3,
          "outlettype": [
            "signal",
            "signal",
            ""
          ],
          "patching_rect": [
            220.0,
            200.0,
            120.0,
            22.0
          ],
          "id": "obj-6"
        }
      },
      {
        "box": {
          "maxclass": "message",
          "text": "record",
          "numinlets": 2,
          "numoutlets": 1,
          "outlettype": [
            ""
          ],
          "patching_rect": [
            220.0,
            140.0,
            120.0,
            22.0
          ],
          "id": "obj-7"
        }
      },
      {
        "box": {
          "maxclass": "message",
          "text": "report 300",
          "numinlets": 2,
          "numoutlets": 1,
          "outlettype": [
            ""
          ],
          "patching_rect": [
            340.0,
            140.0,
            120.0,
            22.0
          ],
          "id": "obj-8"
        }
      },
      {
        "box": {
          "maxclass": "message",
          "text": "ramp 16, snramp 16",
          "numinlets": 2,
          "numoutlets": 1,
          "outlettype": [
            ""
          ],
          "patching_rect": [
            460.0,
            100.0,
            120.0,
            22.0
          ],
          "id": "obj-9"
        }
      },
      {
        "box": {
          "maxclass": "message",
          "text": "ramp 200, snramp 200",
          "numinlets": 2,
          "numoutlets": 1,
          "outlettype": [
            ""
          ],
          "patching_rect": [
            460.0,
            140.0,
            120.0,
            22.0
          ],
          "id": "obj-10"
        }
      },
      {
        "box": {
          "maxclass": "message",
          "text": "window 0.5",
          "numinlets": 2,
          "numoutlets": 1,
          "outlettype": [
            ""
          ],
          "patching_rect": [
            220.0,
            260.0,
            120.0,
            22.0
          ],
          "id": "obj-11"
        }
      },
      {
        "box": {
          "maxclass": "message",
          "text": "stop, position 0., window 0.5, play",
          "numinlets": 2,
          "numoutlets": 1,
          "outlettype": [
            ""
          ],
          "patching_rect": [
            220.0,
            300.0,
            120.0,
            22.0
          ],
          "w": 260,
          "id": "obj-12"
        }
      },
      {
        "box": {
          "maxclass": "comment",
          "text": "1) ezdac  2) record  3) let it roll a few s  4a) window 0.5   OR   4b) stop/position/window/play   5) toggle ramp msgs",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            40.0,
            340.0,
            900.0,
            20.0
          ],
          "id": "obj-13"
        }
      },
      {
        "box": {
          "maxclass": "newobj",
          "text": "unpack f i i f f f",
          "numinlets": 1,
          "numoutlets": 6,
          "outlettype": [
            "float",
            "int",
            "int",
            "float",
            "float",
            "float"
          ],
          "patching_rect": [
            460.0,
            240.0,
            120.0,
            22.0
          ],
          "id": "obj-14"
        }
      },
      {
        "box": {
          "maxclass": "flonum",
          "numinlets": 1,
          "numoutlets": 1,
          "patching_rect": [
            460.0,
            290.0,
            45.0,
            45.0
          ],
          "w": 90,
          "id": "obj-15"
        }
      },
      {
        "box": {
          "maxclass": "flonum",
          "numinlets": 1,
          "numoutlets": 1,
          "patching_rect": [
            560.0,
            290.0,
            45.0,
            45.0
          ],
          "w": 90,
          "id": "obj-16"
        }
      },
      {
        "box": {
          "maxclass": "flonum",
          "numinlets": 1,
          "numoutlets": 1,
          "patching_rect": [
            660.0,
            290.0,
            45.0,
            45.0
          ],
          "w": 90,
          "id": "obj-17"
        }
      },
      {
        "box": {
          "maxclass": "newobj",
          "text": "print KARMA",
          "numinlets": 1,
          "numoutlets": 0,
          "outlettype": [
            ""
          ],
          "patching_rect": [
            460.0,
            330.0,
            120.0,
            22.0
          ],
          "id": "obj-18"
        }
      },
      {
        "box": {
          "maxclass": "newobj",
          "text": "*~ 0.5",
          "numinlets": 2,
          "numoutlets": 1,
          "outlettype": [
            ""
          ],
          "patching_rect": [
            40.0,
            300.0,
            120.0,
            22.0
          ],
          "id": "obj-19"
        }
      },
      {
        "box": {
          "maxclass": "newobj",
          "text": "ezdac~",
          "numinlets": 2,
          "numoutlets": 0,
          "outlettype": [
            ""
          ],
          "patching_rect": [
            40.0,
            360.0,
            120.0,
            22.0
          ],
          "id": "obj-20"
        }
      }
    ],
    "lines": [
      {
        "patchline": {
          "source": [
            "obj-3",
            0
          ],
          "destination": [
            "obj-4",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "obj-4",
            0
          ],
          "destination": [
            "obj-6",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "obj-4",
            0
          ],
          "destination": [
            "obj-6",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "obj-5",
            0
          ],
          "destination": [
            "obj-6",
            2
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "obj-7",
            0
          ],
          "destination": [
            "obj-6",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "obj-8",
            0
          ],
          "destination": [
            "obj-6",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "obj-9",
            0
          ],
          "destination": [
            "obj-6",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "obj-10",
            0
          ],
          "destination": [
            "obj-6",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "obj-11",
            0
          ],
          "destination": [
            "obj-6",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "obj-12",
            0
          ],
          "destination": [
            "obj-6",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "obj-6",
            2
          ],
          "destination": [
            "obj-14",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "obj-14",
            0
          ],
          "destination": [
            "obj-15",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "obj-14",
            4
          ],
          "destination": [
            "obj-16",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "obj-14",
            5
          ],
          "destination": [
            "obj-17",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "obj-14",
            0
          ],
          "destination": [
            "obj-18",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "obj-6",
            0
          ],
          "destination": [
            "obj-19",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "obj-19",
            0
          ],
          "destination": [
            "obj-20",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "obj-19",
            0
          ],
          "destination": [
            "obj-20",
            1
          ]
        }
      }
    ]
  }
}