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
          "text": "T2  --  does a pre-instantiated poly~/play~ voice fire tight enough to replace karma~ jump for slice triggering?  Fire repeatedly, watch the scope~ attack, judge by ear against the metronome.",
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
            720.0,
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
            760.0,
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
            720.0,
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
            720.0,
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
            720.0,
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
            720.0,
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
            720.0,
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
            720.0,
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
          "text": "metro 8n",
          "numinlets": 2,
          "numoutlets": 1,
          "outlettype": [
            "bang"
          ],
          "patching_rect": [
            300.0,
            80.0,
            120.0,
            22.0
          ],
          "id": "obj-12"
        }
      },
      {
        "box": {
          "maxclass": "toggle",
          "numinlets": 1,
          "numoutlets": 1,
          "patching_rect": [
            300.0,
            116.0,
            45.0,
            45.0
          ],
          "id": "obj-13"
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
            430.0,
            80.0,
            120.0,
            22.0
          ],
          "id": "obj-14"
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
            430.0,
            116.0,
            120.0,
            22.0
          ],
          "id": "obj-15"
        }
      },
      {
        "box": {
          "maxclass": "newobj",
          "text": "click~",
          "numinlets": 1,
          "numoutlets": 1,
          "outlettype": [
            "signal"
          ],
          "patching_rect": [
            300.0,
            156.0,
            120.0,
            22.0
          ],
          "id": "obj-16"
        }
      },
      {
        "box": {
          "maxclass": "comment",
          "text": "3) transport 1, metro toggle ON (reference grid)",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            300.0,
            46.0,
            420.0,
            20.0
          ],
          "id": "obj-17"
        }
      },
      {
        "box": {
          "maxclass": "button",
          "numinlets": 1,
          "numoutlets": 1,
          "patching_rect": [
            40.0,
            100.0,
            45.0,
            45.0
          ],
          "id": "obj-18"
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
            140.0,
            120.0,
            22.0
          ],
          "id": "obj-19"
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
            160.0,
            100.0,
            120.0,
            22.0
          ],
          "id": "obj-20"
        }
      },
      {
        "box": {
          "maxclass": "comment",
          "text": "4) hammer 'fire' -- attack should be instant, no lag vs the metro click",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            40.0,
            240.0,
            560.0,
            20.0
          ],
          "id": "obj-21"
        }
      },
      {
        "box": {
          "maxclass": "scope~",
          "numinlets": 2,
          "numoutlets": 0,
          "patching_rect": [
            40.0,
            270.0,
            45.0,
            45.0
          ],
          "w": 300,
          "h": 150,
          "id": "obj-22"
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
            440.0,
            120.0,
            22.0
          ],
          "id": "obj-23"
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
            490.0,
            120.0,
            22.0
          ],
          "id": "obj-24"
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
            "obj-15",
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
            "obj-12",
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
            "obj-18",
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
            "obj-22",
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
            "obj-23",
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
            "obj-23",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "obj-23",
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
            "obj-23",
            0
          ],
          "destination": [
            "obj-24",
            1
          ]
        }
      }
    ]
  }
}