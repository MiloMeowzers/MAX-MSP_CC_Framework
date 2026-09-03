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
          "text": "buffer~ tbuf 4000 2",
          "numinlets": 2,
          "numoutlets": 1,
          "outlettype": [
            ""
          ],
          "patching_rect": [
            40.0,
            46.0,
            120.0,
            22.0
          ],
          "id": "obj-2"
        }
      },
      {
        "box": {
          "maxclass": "comment",
          "text": "T3  --  poly~ voice.maxpat 4.  Machine-gun the 6 notes -> only 4 sound at once (stealing).  'target 2, 1' then a note -> VOICE print reads 2.",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            40.0,
            10.0,
            940.0,
            20.0
          ],
          "id": "obj-1"
        }
      },
      {
        "box": {
          "maxclass": "button",
          "numinlets": 1,
          "numoutlets": 1,
          "patching_rect": [
            760.0,
            40.0,
            45.0,
            45.0
          ],
          "id": "obj-3"
        }
      },
      {
        "box": {
          "maxclass": "comment",
          "text": "2) fill buffer (16 clicks)",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            800.0,
            40.0,
            190.0,
            20.0
          ],
          "id": "obj-4"
        }
      },
      {
        "box": {
          "maxclass": "newobj",
          "text": "uzi 16 1",
          "numinlets": 2,
          "numoutlets": 3,
          "outlettype": [
            "bang",
            "bang",
            "int"
          ],
          "patching_rect": [
            760.0,
            80.0,
            120.0,
            22.0
          ],
          "id": "obj-5"
        }
      },
      {
        "box": {
          "maxclass": "newobj",
          "text": "- 1",
          "numinlets": 2,
          "numoutlets": 1,
          "outlettype": [
            ""
          ],
          "patching_rect": [
            760.0,
            114.0,
            120.0,
            22.0
          ],
          "id": "obj-6"
        }
      },
      {
        "box": {
          "maxclass": "newobj",
          "text": "* 11025",
          "numinlets": 2,
          "numoutlets": 1,
          "outlettype": [
            ""
          ],
          "patching_rect": [
            760.0,
            148.0,
            120.0,
            22.0
          ],
          "id": "obj-7"
        }
      },
      {
        "box": {
          "maxclass": "newobj",
          "text": "t b i",
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "bang",
            "int"
          ],
          "patching_rect": [
            760.0,
            182.0,
            120.0,
            22.0
          ],
          "id": "obj-8"
        }
      },
      {
        "box": {
          "maxclass": "message",
          "text": "1.",
          "numinlets": 2,
          "numoutlets": 1,
          "outlettype": [
            ""
          ],
          "patching_rect": [
            760.0,
            216.0,
            120.0,
            22.0
          ],
          "id": "obj-9"
        }
      },
      {
        "box": {
          "maxclass": "newobj",
          "text": "poke~ tbuf",
          "numinlets": 3,
          "numoutlets": 0,
          "outlettype": [
            ""
          ],
          "patching_rect": [
            760.0,
            250.0,
            120.0,
            22.0
          ],
          "id": "obj-10"
        }
      },
      {
        "box": {
          "maxclass": "comment",
          "text": "1) click ezdac",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            40.0,
            44.0,
            140.0,
            20.0
          ],
          "id": "obj-11"
        }
      },
      {
        "box": {
          "maxclass": "newobj",
          "text": "poly~ voice.maxpat 4",
          "numinlets": 1,
          "numoutlets": 3,
          "outlettype": [
            "signal",
            "signal",
            ""
          ],
          "patching_rect": [
            40.0,
            110.0,
            120.0,
            22.0
          ],
          "id": "obj-12"
        }
      },
      {
        "box": {
          "maxclass": "message",
          "text": "midinote 60 110",
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
          "id": "obj-13"
        }
      },
      {
        "box": {
          "maxclass": "message",
          "text": "midinote 62 110",
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
          "id": "obj-14"
        }
      },
      {
        "box": {
          "maxclass": "message",
          "text": "midinote 64 110",
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
          "id": "obj-15"
        }
      },
      {
        "box": {
          "maxclass": "message",
          "text": "midinote 65 110",
          "numinlets": 2,
          "numoutlets": 1,
          "outlettype": [
            ""
          ],
          "patching_rect": [
            40.0,
            194.0,
            120.0,
            22.0
          ],
          "id": "obj-16"
        }
      },
      {
        "box": {
          "maxclass": "message",
          "text": "midinote 67 110",
          "numinlets": 2,
          "numoutlets": 1,
          "outlettype": [
            ""
          ],
          "patching_rect": [
            200.0,
            194.0,
            120.0,
            22.0
          ],
          "id": "obj-17"
        }
      },
      {
        "box": {
          "maxclass": "message",
          "text": "midinote 69 110",
          "numinlets": 2,
          "numoutlets": 1,
          "outlettype": [
            ""
          ],
          "patching_rect": [
            360.0,
            194.0,
            120.0,
            22.0
          ],
          "id": "obj-18"
        }
      },
      {
        "box": {
          "maxclass": "comment",
          "text": "3) machine-gun these six",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            40.0,
            232.0,
            320.0,
            20.0
          ],
          "id": "obj-19"
        }
      },
      {
        "box": {
          "maxclass": "message",
          "text": "target 2, 1",
          "numinlets": 2,
          "numoutlets": 1,
          "outlettype": [
            ""
          ],
          "patching_rect": [
            40.0,
            270.0,
            120.0,
            22.0
          ],
          "w": 120,
          "id": "obj-20"
        }
      },
      {
        "box": {
          "maxclass": "message",
          "text": "midinote 72 110",
          "numinlets": 2,
          "numoutlets": 1,
          "outlettype": [
            ""
          ],
          "patching_rect": [
            180.0,
            270.0,
            120.0,
            22.0
          ],
          "id": "obj-21"
        }
      },
      {
        "box": {
          "maxclass": "comment",
          "text": "4) 'target 2, 1' then this -> VOICE = 2",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            40.0,
            300.0,
            420.0,
            20.0
          ],
          "id": "obj-22"
        }
      },
      {
        "box": {
          "maxclass": "newobj",
          "text": "print VOICE",
          "numinlets": 1,
          "numoutlets": 0,
          "outlettype": [
            ""
          ],
          "patching_rect": [
            340.0,
            270.0,
            120.0,
            22.0
          ],
          "id": "obj-23"
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
            340.0,
            120.0,
            22.0
          ],
          "id": "obj-24"
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
            390.0,
            120.0,
            22.0
          ],
          "id": "obj-25"
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
            "obj-5",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "obj-5",
            2
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
            "obj-13",
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
            "obj-14",
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
            "obj-15",
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
            "obj-16",
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
            "obj-17",
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
            "obj-18",
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
            "obj-20",
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
            "obj-21",
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
            2
          ],
          "destination": [
            "obj-23",
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
            "obj-24",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "obj-24",
            0
          ],
          "destination": [
            "obj-25",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "obj-24",
            0
          ],
          "destination": [
            "obj-25",
            1
          ]
        }
      }
    ]
  }
}