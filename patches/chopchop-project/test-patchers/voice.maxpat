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
          "text": "poly~ voice -- bang plays 1000..1250 ms of tbuf once, frees on line~ done",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            40.0,
            10.0,
            600.0,
            20.0
          ],
          "id": "obj-1"
        }
      },
      {
        "box": {
          "maxclass": "newobj",
          "text": "in 1",
          "numinlets": 1,
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
          "maxclass": "newobj",
          "text": "thispoly~",
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "signal",
            "signal"
          ],
          "patching_rect": [
            340.0,
            50.0,
            120.0,
            22.0
          ],
          "id": "obj-3"
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
            40.0,
            90.0,
            120.0,
            22.0
          ],
          "id": "obj-4"
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
            210.0,
            90.0,
            120.0,
            22.0
          ],
          "id": "obj-5"
        }
      },
      {
        "box": {
          "maxclass": "message",
          "text": "1000, 1250 250",
          "numinlets": 2,
          "numoutlets": 1,
          "outlettype": [
            ""
          ],
          "patching_rect": [
            40.0,
            130.0,
            120.0,
            22.0
          ],
          "w": 150,
          "id": "obj-6"
        }
      },
      {
        "box": {
          "maxclass": "newobj",
          "text": "line~",
          "numinlets": 2,
          "numoutlets": 2,
          "outlettype": [
            "signal",
            "bang"
          ],
          "patching_rect": [
            40.0,
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
          "text": "play~ tbuf 2",
          "numinlets": 1,
          "numoutlets": 3,
          "outlettype": [
            "signal",
            "signal",
            "bang"
          ],
          "patching_rect": [
            40.0,
            210.0,
            120.0,
            22.0
          ],
          "id": "obj-8"
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
            210.0,
            250.0,
            120.0,
            22.0
          ],
          "id": "obj-9"
        }
      },
      {
        "box": {
          "maxclass": "newobj",
          "text": "out 3",
          "numinlets": 1,
          "numoutlets": 0,
          "outlettype": [
            ""
          ],
          "patching_rect": [
            340.0,
            130.0,
            120.0,
            22.0
          ],
          "id": "obj-10"
        }
      },
      {
        "box": {
          "maxclass": "newobj",
          "text": "out~ 1",
          "numinlets": 1,
          "numoutlets": 0,
          "outlettype": [
            ""
          ],
          "patching_rect": [
            40.0,
            260.0,
            120.0,
            22.0
          ],
          "id": "obj-11"
        }
      },
      {
        "box": {
          "maxclass": "newobj",
          "text": "out~ 2",
          "numinlets": 1,
          "numoutlets": 0,
          "outlettype": [
            ""
          ],
          "patching_rect": [
            150.0,
            260.0,
            120.0,
            22.0
          ],
          "id": "obj-12"
        }
      }
    ],
    "lines": [
      {
        "patchline": {
          "source": [
            "obj-2",
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
            1
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
            "obj-10",
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
            "obj-7",
            1
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
            "obj-3",
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
            "obj-11",
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
            "obj-12",
            0
          ]
        }
      }
    ]
  }
}