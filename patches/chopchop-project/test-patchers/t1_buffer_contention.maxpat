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
          "text": "buffer~ tbuf 6000 2",
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
          "text": "T1  --  does groove~ glitch while record~ writes the SAME buffer?  (rolling-karmaB contention)",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            40.0,
            10.0,
            760.0,
            20.0
          ],
          "id": "obj-1"
        }
      },
      {
        "box": {
          "maxclass": "newobj",
          "text": "cycle~ 180",
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
          "maxclass": "toggle",
          "numinlets": 1,
          "numoutlets": 1,
          "patching_rect": [
            240.0,
            100.0,
            45.0,
            45.0
          ],
          "id": "obj-5"
        }
      },
      {
        "box": {
          "maxclass": "newobj",
          "text": "record~ tbuf 2",
          "numinlets": 3,
          "numoutlets": 1,
          "outlettype": [
            "signal"
          ],
          "patching_rect": [
            240.0,
            140.0,
            120.0,
            22.0
          ],
          "id": "obj-6"
        }
      },
      {
        "box": {
          "maxclass": "comment",
          "text": "2) record ON",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            240.0,
            80.0,
            120.0,
            20.0
          ],
          "id": "obj-7"
        }
      },
      {
        "box": {
          "maxclass": "flonum",
          "numinlets": 1,
          "numoutlets": 1,
          "patching_rect": [
            440.0,
            100.0,
            45.0,
            45.0
          ],
          "id": "obj-8"
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
            440.0,
            140.0,
            120.0,
            22.0
          ],
          "id": "obj-9"
        }
      },
      {
        "box": {
          "maxclass": "newobj",
          "text": "groove~ tbuf 2",
          "numinlets": 3,
          "numoutlets": 2,
          "outlettype": [
            "signal",
            "signal"
          ],
          "patching_rect": [
            440.0,
            190.0,
            120.0,
            22.0
          ],
          "id": "obj-10"
        }
      },
      {
        "box": {
          "maxclass": "message",
          "text": "0",
          "numinlets": 2,
          "numoutlets": 1,
          "outlettype": [
            ""
          ],
          "patching_rect": [
            600.0,
            150.0,
            120.0,
            22.0
          ],
          "id": "obj-11"
        }
      },
      {
        "box": {
          "maxclass": "message",
          "text": "6000",
          "numinlets": 2,
          "numoutlets": 1,
          "outlettype": [
            ""
          ],
          "patching_rect": [
            640.0,
            150.0,
            120.0,
            22.0
          ],
          "id": "obj-12"
        }
      },
      {
        "box": {
          "maxclass": "message",
          "text": "startloop",
          "numinlets": 2,
          "numoutlets": 1,
          "outlettype": [
            ""
          ],
          "patching_rect": [
            560.0,
            120.0,
            120.0,
            22.0
          ],
          "id": "obj-13"
        }
      },
      {
        "box": {
          "maxclass": "comment",
          "text": "3) rate 1.  then  4) startloop   5) listen for zipper/dropout while rec runs",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            440.0,
            90.0,
            420.0,
            20.0
          ],
          "id": "obj-14"
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
            440.0,
            240.0,
            120.0,
            22.0
          ],
          "id": "obj-15"
        }
      },
      {
        "box": {
          "maxclass": "meter~",
          "numinlets": 1,
          "numoutlets": 1,
          "patching_rect": [
            620.0,
            240.0,
            45.0,
            45.0
          ],
          "id": "obj-16"
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
            440.0,
            300.0,
            120.0,
            22.0
          ],
          "id": "obj-17"
        }
      },
      {
        "box": {
          "maxclass": "comment",
          "text": "1) click ezdac (DSP on)",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            440.0,
            340.0,
            220.0,
            20.0
          ],
          "id": "obj-18"
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
            "obj-9",
            0
          ],
          "destination": [
            "obj-10",
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
            "obj-10",
            1
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
            "obj-10",
            2
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
            "obj-10",
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
            "obj-15",
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
            "obj-16",
            0
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
            "obj-17",
            0
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
            "obj-17",
            1
          ]
        }
      }
    ]
  }
}