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
          "text": "buffer~ src 8000 2",
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "float",
            "bang"
          ],
          "patching_rect": [
            40.0,
            40.0,
            150.0,
            22.0
          ],
          "id": "obj-1"
        }
      },
      {
        "box": {
          "maxclass": "newobj",
          "text": "buffer~ dst 8000 2",
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "float",
            "bang"
          ],
          "patching_rect": [
            210.0,
            40.0,
            150.0,
            22.0
          ],
          "id": "obj-2"
        }
      },
      {
        "box": {
          "maxclass": "comment",
          "text": "A.  Click FILL SRC, wait ~8 s (auto-stops). Fills src with a 200 Hz sine.",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            40.0,
            90.0,
            200.0,
            20.0
          ],
          "id": "obj-3"
        }
      },
      {
        "box": {
          "maxclass": "button",
          "numinlets": 1,
          "numoutlets": 1,
          "patching_rect": [
            40.0,
            115.0,
            24.0,
            24.0
          ],
          "outlettype": [
            "bang"
          ],
          "id": "obj-4"
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
            150.0,
            60.0,
            22.0
          ],
          "id": "obj-5"
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
            185.0,
            40.0,
            22.0
          ],
          "id": "obj-6"
        }
      },
      {
        "box": {
          "maxclass": "newobj",
          "text": "delay 8000",
          "numinlets": 2,
          "numoutlets": 1,
          "outlettype": [
            "bang"
          ],
          "patching_rect": [
            120.0,
            150.0,
            90.0,
            22.0
          ],
          "id": "obj-7"
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
            120.0,
            185.0,
            40.0,
            22.0
          ],
          "id": "obj-8"
        }
      },
      {
        "box": {
          "maxclass": "newobj",
          "text": "cycle~ 200",
          "numinlets": 2,
          "numoutlets": 1,
          "outlettype": [
            "signal"
          ],
          "patching_rect": [
            240.0,
            150.0,
            90.0,
            22.0
          ],
          "id": "obj-9"
        }
      },
      {
        "box": {
          "maxclass": "newobj",
          "text": "record~ src 2",
          "numinlets": 2,
          "numoutlets": 1,
          "outlettype": [
            "signal"
          ],
          "patching_rect": [
            240.0,
            220.0,
            150.0,
            22.0
          ],
          "id": "obj-10"
        }
      },
      {
        "box": {
          "maxclass": "comment",
          "text": "B.  Click RENDER 8x. Renders src -> dst through karma at 8x, then auditions at 1x.",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            40.0,
            270.0,
            200.0,
            20.0
          ],
          "id": "obj-11"
        }
      },
      {
        "box": {
          "maxclass": "button",
          "numinlets": 1,
          "numoutlets": 1,
          "patching_rect": [
            40.0,
            295.0,
            24.0,
            24.0
          ],
          "outlettype": [
            "bang"
          ],
          "id": "obj-12"
        }
      },
      {
        "box": {
          "maxclass": "newobj",
          "text": "t b b b b b b",
          "numinlets": 1,
          "numoutlets": 6,
          "outlettype": [
            "bang",
            "bang",
            "bang",
            "bang",
            "bang",
            "bang"
          ],
          "patching_rect": [
            40.0,
            330.0,
            150.0,
            22.0
          ],
          "id": "obj-13"
        }
      },
      {
        "box": {
          "maxclass": "message",
          "text": "loop 1",
          "numinlets": 2,
          "numoutlets": 1,
          "outlettype": [
            ""
          ],
          "patching_rect": [
            40.0,
            365.0,
            60.0,
            22.0
          ],
          "id": "obj-14"
        }
      },
      {
        "box": {
          "maxclass": "message",
          "text": "8. 0",
          "numinlets": 2,
          "numoutlets": 1,
          "outlettype": [
            ""
          ],
          "patching_rect": [
            110.0,
            365.0,
            50.0,
            22.0
          ],
          "id": "obj-15"
        }
      },
      {
        "box": {
          "maxclass": "message",
          "text": "8. 0",
          "numinlets": 2,
          "numoutlets": 1,
          "outlettype": [
            ""
          ],
          "patching_rect": [
            170.0,
            365.0,
            50.0,
            22.0
          ],
          "id": "obj-16"
        }
      },
      {
        "box": {
          "maxclass": "message",
          "text": "stop",
          "numinlets": 2,
          "numoutlets": 1,
          "outlettype": [
            ""
          ],
          "patching_rect": [
            230.0,
            365.0,
            50.0,
            22.0
          ],
          "id": "obj-17"
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
            290.0,
            365.0,
            40.0,
            22.0
          ],
          "id": "obj-18"
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
            340.0,
            365.0,
            60.0,
            22.0
          ],
          "id": "obj-19"
        }
      },
      {
        "box": {
          "maxclass": "message",
          "text": "report 400",
          "numinlets": 2,
          "numoutlets": 1,
          "outlettype": [
            ""
          ],
          "patching_rect": [
            410.0,
            365.0,
            80.0,
            22.0
          ],
          "id": "obj-20"
        }
      },
      {
        "box": {
          "maxclass": "newobj",
          "text": "delay 1000",
          "numinlets": 2,
          "numoutlets": 1,
          "outlettype": [
            "bang"
          ],
          "patching_rect": [
            500.0,
            365.0,
            90.0,
            22.0
          ],
          "id": "obj-21"
        }
      },
      {
        "box": {
          "maxclass": "newobj",
          "text": "t b b b",
          "numinlets": 1,
          "numoutlets": 3,
          "outlettype": [
            "bang",
            "bang",
            "bang"
          ],
          "patching_rect": [
            500.0,
            400.0,
            90.0,
            22.0
          ],
          "id": "obj-22"
        }
      },
      {
        "box": {
          "maxclass": "message",
          "text": "play",
          "numinlets": 2,
          "numoutlets": 1,
          "outlettype": [
            ""
          ],
          "patching_rect": [
            500.0,
            435.0,
            50.0,
            22.0
          ],
          "id": "obj-23"
        }
      },
      {
        "box": {
          "maxclass": "message",
          "text": "1. 20",
          "numinlets": 2,
          "numoutlets": 1,
          "outlettype": [
            ""
          ],
          "patching_rect": [
            560.0,
            435.0,
            50.0,
            22.0
          ],
          "id": "obj-24"
        }
      },
      {
        "box": {
          "maxclass": "message",
          "text": "0. 20",
          "numinlets": 2,
          "numoutlets": 1,
          "outlettype": [
            ""
          ],
          "patching_rect": [
            620.0,
            435.0,
            50.0,
            22.0
          ],
          "id": "obj-25"
        }
      },
      {
        "box": {
          "maxclass": "comment",
          "text": "D.  Click RENDER 1x for the known-good real-time reference (8 s pass).",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            40.0,
            470.0,
            200.0,
            20.0
          ],
          "id": "obj-26"
        }
      },
      {
        "box": {
          "maxclass": "button",
          "numinlets": 1,
          "numoutlets": 1,
          "patching_rect": [
            40.0,
            495.0,
            24.0,
            24.0
          ],
          "outlettype": [
            "bang"
          ],
          "id": "obj-27"
        }
      },
      {
        "box": {
          "maxclass": "newobj",
          "text": "t b b b b b",
          "numinlets": 1,
          "numoutlets": 5,
          "outlettype": [
            "bang",
            "bang",
            "bang",
            "bang",
            "bang"
          ],
          "patching_rect": [
            40.0,
            530.0,
            150.0,
            22.0
          ],
          "id": "obj-28"
        }
      },
      {
        "box": {
          "maxclass": "message",
          "text": "loop 1",
          "numinlets": 2,
          "numoutlets": 1,
          "outlettype": [
            ""
          ],
          "patching_rect": [
            40.0,
            565.0,
            60.0,
            22.0
          ],
          "id": "obj-29"
        }
      },
      {
        "box": {
          "maxclass": "message",
          "text": "1. 0",
          "numinlets": 2,
          "numoutlets": 1,
          "outlettype": [
            ""
          ],
          "patching_rect": [
            110.0,
            565.0,
            50.0,
            22.0
          ],
          "id": "obj-30"
        }
      },
      {
        "box": {
          "maxclass": "message",
          "text": "1. 0",
          "numinlets": 2,
          "numoutlets": 1,
          "outlettype": [
            ""
          ],
          "patching_rect": [
            170.0,
            565.0,
            50.0,
            22.0
          ],
          "id": "obj-31"
        }
      },
      {
        "box": {
          "maxclass": "message",
          "text": "stop",
          "numinlets": 2,
          "numoutlets": 1,
          "outlettype": [
            ""
          ],
          "patching_rect": [
            230.0,
            565.0,
            50.0,
            22.0
          ],
          "id": "obj-32"
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
            290.0,
            565.0,
            40.0,
            22.0
          ],
          "id": "obj-33"
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
            340.0,
            565.0,
            60.0,
            22.0
          ],
          "id": "obj-34"
        }
      },
      {
        "box": {
          "maxclass": "newobj",
          "text": "delay 8000",
          "numinlets": 2,
          "numoutlets": 1,
          "outlettype": [
            "bang"
          ],
          "patching_rect": [
            410.0,
            565.0,
            90.0,
            22.0
          ],
          "id": "obj-35"
        }
      },
      {
        "box": {
          "maxclass": "message",
          "text": "play",
          "numinlets": 2,
          "numoutlets": 1,
          "outlettype": [
            ""
          ],
          "patching_rect": [
            410.0,
            600.0,
            50.0,
            22.0
          ],
          "id": "obj-36"
        }
      },
      {
        "box": {
          "maxclass": "newobj",
          "text": "line~ 1.",
          "numinlets": 2,
          "numoutlets": 2,
          "outlettype": [
            "signal",
            "bang"
          ],
          "patching_rect": [
            700.0,
            300.0,
            70.0,
            22.0
          ],
          "id": "obj-37"
        }
      },
      {
        "box": {
          "maxclass": "newobj",
          "text": "line~ 1.",
          "numinlets": 2,
          "numoutlets": 2,
          "outlettype": [
            "signal",
            "bang"
          ],
          "patching_rect": [
            780.0,
            300.0,
            70.0,
            22.0
          ],
          "id": "obj-38"
        }
      },
      {
        "box": {
          "maxclass": "newobj",
          "text": "groove~ src 2",
          "numinlets": 3,
          "numoutlets": 3,
          "outlettype": [
            "signal",
            "signal",
            "signal"
          ],
          "patching_rect": [
            700.0,
            360.0,
            150.0,
            22.0
          ],
          "id": "obj-39"
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
            870.0,
            330.0,
            40.0,
            22.0
          ],
          "id": "obj-40"
        }
      },
      {
        "box": {
          "maxclass": "message",
          "text": "8000",
          "numinlets": 2,
          "numoutlets": 1,
          "outlettype": [
            ""
          ],
          "patching_rect": [
            920.0,
            330.0,
            50.0,
            22.0
          ],
          "id": "obj-41"
        }
      },
      {
        "box": {
          "maxclass": "newobj",
          "text": "karma~ dst 2",
          "numinlets": 3,
          "numoutlets": 3,
          "outlettype": [
            "signal",
            "signal",
            ""
          ],
          "patching_rect": [
            700.0,
            430.0,
            150.0,
            22.0
          ],
          "id": "obj-42"
        }
      },
      {
        "box": {
          "maxclass": "newobj",
          "text": "loadbang",
          "numinlets": 1,
          "numoutlets": 1,
          "outlettype": [
            "bang"
          ],
          "patching_rect": [
            870.0,
            295.0,
            70.0,
            22.0
          ],
          "id": "obj-43"
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
            870.0,
            300.0,
            60.0,
            22.0
          ],
          "id": "obj-44"
        }
      },
      {
        "box": {
          "maxclass": "comment",
          "text": "C.  RESULT after B:  end ms ~= 8000  AND  window ms ~= 8000  AND  play=1, rec=0.",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            40.0,
            640.0,
            200.0,
            20.0
          ],
          "id": "obj-45"
        }
      },
      {
        "box": {
          "maxclass": "comment",
          "text": "    Audio: 200 Hz sine, loops every 8 s -- must match D. FAIL if end ms ~= 1000 or tone is high / loops ~1 s.",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            40.0,
            660.0,
            200.0,
            20.0
          ],
          "id": "obj-46"
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
            700.0,
            500.0,
            150.0,
            22.0
          ],
          "id": "obj-47"
        }
      },
      {
        "box": {
          "maxclass": "number",
          "numinlets": 1,
          "numoutlets": 2,
          "patching_rect": [
            700.0,
            530.0,
            90.0,
            22.0
          ],
          "outlettype": [
            "",
            "bang"
          ],
          "id": "obj-48"
        }
      },
      {
        "box": {
          "maxclass": "comment",
          "text": "pos 0-1",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            800.0,
            532.0,
            200.0,
            20.0
          ],
          "id": "obj-49"
        }
      },
      {
        "box": {
          "maxclass": "number",
          "numinlets": 1,
          "numoutlets": 2,
          "patching_rect": [
            700.0,
            556.0,
            90.0,
            22.0
          ],
          "outlettype": [
            "",
            "bang"
          ],
          "id": "obj-50"
        }
      },
      {
        "box": {
          "maxclass": "comment",
          "text": "play",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            800.0,
            558.0,
            200.0,
            20.0
          ],
          "id": "obj-51"
        }
      },
      {
        "box": {
          "maxclass": "number",
          "numinlets": 1,
          "numoutlets": 2,
          "patching_rect": [
            700.0,
            582.0,
            90.0,
            22.0
          ],
          "outlettype": [
            "",
            "bang"
          ],
          "id": "obj-52"
        }
      },
      {
        "box": {
          "maxclass": "comment",
          "text": "rec",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            800.0,
            584.0,
            200.0,
            20.0
          ],
          "id": "obj-53"
        }
      },
      {
        "box": {
          "maxclass": "number",
          "numinlets": 1,
          "numoutlets": 2,
          "patching_rect": [
            700.0,
            608.0,
            90.0,
            22.0
          ],
          "outlettype": [
            "",
            "bang"
          ],
          "id": "obj-54"
        }
      },
      {
        "box": {
          "maxclass": "comment",
          "text": "start ms",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            800.0,
            610.0,
            200.0,
            20.0
          ],
          "id": "obj-55"
        }
      },
      {
        "box": {
          "maxclass": "number",
          "numinlets": 1,
          "numoutlets": 2,
          "patching_rect": [
            700.0,
            634.0,
            90.0,
            22.0
          ],
          "outlettype": [
            "",
            "bang"
          ],
          "id": "obj-56"
        }
      },
      {
        "box": {
          "maxclass": "comment",
          "text": "end ms",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            800.0,
            636.0,
            200.0,
            20.0
          ],
          "id": "obj-57"
        }
      },
      {
        "box": {
          "maxclass": "number",
          "numinlets": 1,
          "numoutlets": 2,
          "patching_rect": [
            700.0,
            660.0,
            90.0,
            22.0
          ],
          "outlettype": [
            "",
            "bang"
          ],
          "id": "obj-58"
        }
      },
      {
        "box": {
          "maxclass": "comment",
          "text": "window ms",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            800.0,
            662.0,
            200.0,
            20.0
          ],
          "id": "obj-59"
        }
      },
      {
        "box": {
          "maxclass": "newobj",
          "text": "print k",
          "numinlets": 1,
          "numoutlets": 0,
          "outlettype": [
            ""
          ],
          "patching_rect": [
            900.0,
            500.0,
            60.0,
            22.0
          ],
          "id": "obj-60"
        }
      },
      {
        "box": {
          "maxclass": "comment",
          "text": "E.  CLICK EZDAC ON FIRST (turn on audio).",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            40.0,
            810.0,
            200.0,
            20.0
          ],
          "id": "obj-61"
        }
      },
      {
        "box": {
          "maxclass": "newobj",
          "text": "*~ 0.4",
          "numinlets": 2,
          "numoutlets": 1,
          "outlettype": [
            "signal"
          ],
          "patching_rect": [
            700.0,
            600.0,
            60.0,
            22.0
          ],
          "id": "obj-62"
        }
      },
      {
        "box": {
          "maxclass": "newobj",
          "text": "*~ 0.4",
          "numinlets": 2,
          "numoutlets": 1,
          "outlettype": [
            "signal"
          ],
          "patching_rect": [
            770.0,
            600.0,
            60.0,
            22.0
          ],
          "id": "obj-63"
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
            700.0,
            640.0,
            90.0,
            22.0
          ],
          "id": "obj-64"
        }
      },
      {
        "box": {
          "maxclass": "newobj",
          "text": "scope~",
          "numinlets": 2,
          "numoutlets": 0,
          "outlettype": [
            ""
          ],
          "patching_rect": [
            820.0,
            600.0,
            130.0,
            22.0
          ],
          "id": "obj-65"
        }
      },
      {
        "box": {
          "maxclass": "button",
          "numinlets": 1,
          "numoutlets": 1,
          "patching_rect": [
            560.0,
            295.0,
            24.0,
            24.0
          ],
          "outlettype": [
            "bang"
          ],
          "id": "obj-66"
        }
      },
      {
        "box": {
          "maxclass": "message",
          "text": "stop",
          "numinlets": 2,
          "numoutlets": 1,
          "outlettype": [
            ""
          ],
          "patching_rect": [
            560.0,
            260.0,
            50.0,
            22.0
          ],
          "id": "obj-67"
        }
      },
      {
        "box": {
          "maxclass": "comment",
          "text": "stop",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            590.0,
            297.0,
            200.0,
            20.0
          ],
          "id": "obj-68"
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
            "obj-5",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "obj-5",
            1
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
            "obj-7",
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
            "obj-10",
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
            "obj-10",
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
            "obj-13",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "obj-13",
            5
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
            4
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
            "obj-13",
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
            "obj-13",
            3
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
            "obj-13",
            2
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
            "obj-13",
            1
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
            "obj-13",
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
            "obj-13",
            0
          ],
          "destination": [
            "obj-21",
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
            "obj-22",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "obj-22",
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
            "obj-22",
            1
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
            "obj-22",
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
            "obj-27",
            0
          ],
          "destination": [
            "obj-28",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "obj-28",
            4
          ],
          "destination": [
            "obj-29",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "obj-28",
            3
          ],
          "destination": [
            "obj-30",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "obj-28",
            3
          ],
          "destination": [
            "obj-31",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "obj-28",
            2
          ],
          "destination": [
            "obj-32",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "obj-28",
            1
          ],
          "destination": [
            "obj-33",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "obj-28",
            0
          ],
          "destination": [
            "obj-34",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "obj-28",
            0
          ],
          "destination": [
            "obj-35",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "obj-35",
            0
          ],
          "destination": [
            "obj-36",
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
            "obj-37",
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
            "obj-37",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "obj-30",
            0
          ],
          "destination": [
            "obj-37",
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
            "obj-38",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "obj-25",
            0
          ],
          "destination": [
            "obj-38",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "obj-31",
            0
          ],
          "destination": [
            "obj-38",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "obj-38",
            0
          ],
          "destination": [
            "obj-39",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "obj-37",
            0
          ],
          "destination": [
            "obj-42",
            2
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "obj-40",
            0
          ],
          "destination": [
            "obj-39",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "obj-41",
            0
          ],
          "destination": [
            "obj-39",
            2
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
            "obj-39",
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
            "obj-39",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "obj-29",
            0
          ],
          "destination": [
            "obj-39",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "obj-33",
            0
          ],
          "destination": [
            "obj-39",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "obj-39",
            0
          ],
          "destination": [
            "obj-42",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "obj-39",
            1
          ],
          "destination": [
            "obj-42",
            1
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
            "obj-42",
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
            "obj-42",
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
            "obj-42",
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
            "obj-42",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "obj-32",
            0
          ],
          "destination": [
            "obj-42",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "obj-34",
            0
          ],
          "destination": [
            "obj-42",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "obj-36",
            0
          ],
          "destination": [
            "obj-42",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "obj-43",
            0
          ],
          "destination": [
            "obj-44",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "obj-44",
            1
          ],
          "destination": [
            "obj-40",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "obj-44",
            0
          ],
          "destination": [
            "obj-41",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "obj-42",
            2
          ],
          "destination": [
            "obj-47",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "obj-47",
            0
          ],
          "destination": [
            "obj-48",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "obj-47",
            1
          ],
          "destination": [
            "obj-50",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "obj-47",
            2
          ],
          "destination": [
            "obj-52",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "obj-47",
            3
          ],
          "destination": [
            "obj-54",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "obj-47",
            4
          ],
          "destination": [
            "obj-56",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "obj-47",
            5
          ],
          "destination": [
            "obj-58",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "obj-42",
            2
          ],
          "destination": [
            "obj-60",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "obj-42",
            0
          ],
          "destination": [
            "obj-62",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "obj-42",
            1
          ],
          "destination": [
            "obj-63",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "obj-62",
            0
          ],
          "destination": [
            "obj-64",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "obj-63",
            0
          ],
          "destination": [
            "obj-64",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "obj-42",
            0
          ],
          "destination": [
            "obj-65",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "obj-66",
            0
          ],
          "destination": [
            "obj-67",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "obj-67",
            0
          ],
          "destination": [
            "obj-42",
            0
          ]
        }
      }
    ]
  }
}