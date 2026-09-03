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
          "maxclass": "comment",
          "text": "T6  --  exactly one bang per armed bar edge, transport-locked, no drift. Arm, watch the counter tick once per bar; leave running for minutes.",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            40.0,
            10.0,
            840.0,
            20.0
          ],
          "id": "obj-1"
        }
      },
      {
        "box": {
          "maxclass": "newobj",
          "text": "transport",
          "numinlets": 2,
          "numoutlets": 9,
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
          "maxclass": "message",
          "text": "1",
          "numinlets": 2,
          "numoutlets": 1,
          "outlettype": [
            ""
          ],
          "patching_rect": [
            40.0,
            90.0,
            120.0,
            22.0
          ],
          "id": "obj-3"
        }
      },
      {
        "box": {
          "maxclass": "comment",
          "text": "1) transport 1",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            40.0,
            120.0,
            120.0,
            20.0
          ],
          "id": "obj-4"
        }
      },
      {
        "box": {
          "maxclass": "newobj",
          "text": "phasor~ @frequency 1n @lock 1",
          "numinlets": 2,
          "numoutlets": 1,
          "outlettype": [
            "signal"
          ],
          "patching_rect": [
            220.0,
            90.0,
            120.0,
            22.0
          ],
          "id": "obj-5"
        }
      },
      {
        "box": {
          "maxclass": "newobj",
          "text": "delta~",
          "numinlets": 1,
          "numoutlets": 1,
          "outlettype": [
            "signal"
          ],
          "patching_rect": [
            220.0,
            130.0,
            120.0,
            22.0
          ],
          "id": "obj-6"
        }
      },
      {
        "box": {
          "maxclass": "newobj",
          "text": "<~ -0.5",
          "numinlets": 2,
          "numoutlets": 1,
          "outlettype": [
            "signal"
          ],
          "patching_rect": [
            220.0,
            170.0,
            120.0,
            22.0
          ],
          "id": "obj-7"
        }
      },
      {
        "box": {
          "maxclass": "newobj",
          "text": "edge~",
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "bang",
            "bang"
          ],
          "patching_rect": [
            220.0,
            210.0,
            120.0,
            22.0
          ],
          "id": "obj-8"
        }
      },
      {
        "box": {
          "maxclass": "newobj",
          "text": "onebang",
          "numinlets": 2,
          "numoutlets": 2,
          "outlettype": [
            "bang",
            "bang"
          ],
          "patching_rect": [
            220.0,
            250.0,
            120.0,
            22.0
          ],
          "id": "obj-9"
        }
      },
      {
        "box": {
          "maxclass": "button",
          "numinlets": 1,
          "numoutlets": 1,
          "patching_rect": [
            400.0,
            210.0,
            45.0,
            45.0
          ],
          "id": "obj-10"
        }
      },
      {
        "box": {
          "maxclass": "comment",
          "text": "2) click to arm -- expect ONE tick on the next bar line",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            400.0,
            180.0,
            380.0,
            20.0
          ],
          "id": "obj-11"
        }
      },
      {
        "box": {
          "maxclass": "message",
          "text": "bang",
          "numinlets": 2,
          "numoutlets": 1,
          "outlettype": [
            ""
          ],
          "patching_rect": [
            400.0,
            250.0,
            120.0,
            22.0
          ],
          "id": "obj-12"
        }
      },
      {
        "box": {
          "maxclass": "newobj",
          "text": "counter",
          "numinlets": 5,
          "numoutlets": 4,
          "outlettype": [
            "int",
            "",
            "",
            ""
          ],
          "patching_rect": [
            220.0,
            300.0,
            120.0,
            22.0
          ],
          "id": "obj-13"
        }
      },
      {
        "box": {
          "maxclass": "number",
          "numinlets": 1,
          "numoutlets": 1,
          "patching_rect": [
            220.0,
            340.0,
            45.0,
            45.0
          ],
          "w": 80,
          "id": "obj-14"
        }
      },
      {
        "box": {
          "maxclass": "newobj",
          "text": "t b b",
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "bang",
            "bang"
          ],
          "patching_rect": [
            360.0,
            290.0,
            120.0,
            22.0
          ],
          "id": "obj-15"
        }
      },
      {
        "box": {
          "maxclass": "newobj",
          "text": "timer",
          "numinlets": 2,
          "numoutlets": 1,
          "outlettype": [
            "float"
          ],
          "patching_rect": [
            360.0,
            300.0,
            120.0,
            22.0
          ],
          "id": "obj-16"
        }
      },
      {
        "box": {
          "maxclass": "flonum",
          "numinlets": 1,
          "numoutlets": 1,
          "patching_rect": [
            360.0,
            340.0,
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
          "text": "print BAR",
          "numinlets": 1,
          "numoutlets": 0,
          "outlettype": [
            ""
          ],
          "patching_rect": [
            360.0,
            380.0,
            120.0,
            22.0
          ],
          "id": "obj-18"
        }
      },
      {
        "box": {
          "maxclass": "comment",
          "text": "timer between ticks should read the bar length in ms and stay constant",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            360.0,
            420.0,
            420.0,
            20.0
          ],
          "id": "obj-19"
        }
      },
      {
        "box": {
          "maxclass": "newobj",
          "text": "*~ 0.",
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
          "id": "obj-20"
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
            340.0,
            120.0,
            22.0
          ],
          "id": "obj-21"
        }
      },
      {
        "box": {
          "maxclass": "comment",
          "text": "0) click ezdac (phasor~ @lock needs DSP + running transport)",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            40.0,
            380.0,
            420.0,
            20.0
          ],
          "id": "obj-22"
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
            "obj-2",
            0
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
            "obj-7",
            0
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
            "obj-8",
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
            "obj-9",
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
            "obj-9",
            1
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
            "obj-13",
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
            "obj-12",
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
            "obj-15",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "obj-15",
            1
          ],
          "destination": [
            "obj-16",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "obj-15",
            0
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
            "obj-12",
            0
          ],
          "destination": [
            "obj-9",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "obj-13",
            0
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
            "obj-16",
            0
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
            "obj-16",
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
            "obj-5",
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
            "obj-20",
            0
          ],
          "destination": [
            "obj-21",
            0
          ]
        }
      }
    ]
  }
}