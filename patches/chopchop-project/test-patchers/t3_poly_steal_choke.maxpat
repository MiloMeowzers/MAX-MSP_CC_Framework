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
          "text": "T3  --  poly~ @voices 16: does `target N` give a stable home voice, does `midinote` steal sanely, does a shared note in a choke group cut group-mates?",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            40.0,
            10.0,
            880.0,
            20.0
          ],
          "id": "obj-1"
        }
      },
      {
        "box": {
          "maxclass": "newobj",
          "text": "poly~ t2_voice.maxpat 16",
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "signal",
            "signal"
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
          "maxclass": "message",
          "text": "target 3, 1",
          "numinlets": 2,
          "numoutlets": 1,
          "outlettype": [
            ""
          ],
          "patching_rect": [
            40.0,
            160.0,
            120.0,
            22.0
          ],
          "id": "obj-4"
        }
      },
      {
        "box": {
          "maxclass": "message",
          "text": "midinote 60 100",
          "numinlets": 2,
          "numoutlets": 1,
          "outlettype": [
            ""
          ],
          "patching_rect": [
            200.0,
            160.0,
            120.0,
            22.0
          ],
          "id": "obj-5"
        }
      },
      {
        "box": {
          "maxclass": "message",
          "text": "midinote 62 100",
          "numinlets": 2,
          "numoutlets": 1,
          "outlettype": [
            ""
          ],
          "patching_rect": [
            360.0,
            160.0,
            120.0,
            22.0
          ],
          "id": "obj-6"
        }
      },
      {
        "box": {
          "maxclass": "message",
          "text": "midinote 64 100",
          "numinlets": 2,
          "numoutlets": 1,
          "outlettype": [
            ""
          ],
          "patching_rect": [
            520.0,
            160.0,
            120.0,
            22.0
          ],
          "id": "obj-7"
        }
      },
      {
        "box": {
          "maxclass": "comment",
          "text": "1) target then note -> voice 3    2) spam midinote past 16 -> watch steal    3) two notes same pitch -> choke?",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            40.0,
            200.0,
            880.0,
            20.0
          ],
          "id": "obj-8"
        }
      },
      {
        "box": {
          "maxclass": "kslider",
          "numinlets": 2,
          "numoutlets": 2,
          "patching_rect": [
            40.0,
            250.0,
            45.0,
            45.0
          ],
          "w": 320,
          "h": 80,
          "id": "obj-9"
        }
      },
      {
        "box": {
          "maxclass": "newobj",
          "text": "makenote 100 400",
          "numinlets": 3,
          "numoutlets": 2,
          "outlettype": [
            "",
            ""
          ],
          "patching_rect": [
            40.0,
            340.0,
            120.0,
            22.0
          ],
          "id": "obj-10"
        }
      },
      {
        "box": {
          "maxclass": "newobj",
          "text": "t l",
          "numinlets": 1,
          "numoutlets": 1,
          "outlettype": [
            ""
          ],
          "patching_rect": [
            40.0,
            380.0,
            120.0,
            22.0
          ],
          "id": "obj-11"
        }
      },
      {
        "box": {
          "maxclass": "newobj",
          "text": "prepend midinote",
          "numinlets": 2,
          "numoutlets": 1,
          "outlettype": [
            ""
          ],
          "patching_rect": [
            40.0,
            420.0,
            120.0,
            22.0
          ],
          "id": "obj-12"
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
            470.0,
            120.0,
            22.0
          ],
          "id": "obj-13"
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
            520.0,
            120.0,
            22.0
          ],
          "id": "obj-14"
        }
      },
      {
        "box": {
          "maxclass": "comment",
          "text": "0) click ezdac",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            200.0,
            520.0,
            140.0,
            20.0
          ],
          "id": "obj-15"
        }
      }
    ],
    "lines": [
      {
        "patchline": {
          "source": [
            "obj-4",
            0
          ],
          "destination": [
            "obj-3",
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
            "obj-3",
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
            "obj-3",
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
            "obj-3",
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
            "obj-9",
            1
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
            "obj-10",
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
            "obj-12",
            0
          ],
          "destination": [
            "obj-3",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "obj-3",
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
            "obj-13",
            0
          ],
          "destination": [
            "obj-14",
            1
          ]
        }
      }
    ]
  }
}