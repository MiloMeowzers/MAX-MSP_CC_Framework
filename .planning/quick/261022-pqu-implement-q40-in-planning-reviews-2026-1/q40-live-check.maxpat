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
        "rect": [ 85.0, 104.0, 640.0, 480.0 ],
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
        "devicewidth": 372.0,
        "description": "",
        "digest": "",
        "tags": "",
        "style": "",
        "subpatcher_template": "",
        "assistshowspatchername": 0,
        "boxes": [
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-1",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "signal" ],
                    "patching_rect": [ 200.0, 200.0, 121.0, 22.0 ],
                    "text": "gen~",
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
                        "rect": [ 100.0, 100.0, 600.0, 450.0 ],
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
                                    "maxclass": "codebox",
                                    "id": "obj-1",
                                    "numinlets": 0,
                                    "numoutlets": 1,
                                    "outlettype": [ "" ],
                                    "patching_rect": [ 50.0, 80.0, 400.0, 200.0 ],
                                    "parameter_enable": 0,
                                    "code": "Param freq(220, min=20, max=2000);\nParam amp(0.5, min=0, max=1);\nParam gain(0, min=0, max=1);\nParam octave(0, min=-2, max=2);\nHistory one(1);\nk_freq = freq * one;\nk_oct = octave * one;\nk_amp = amp * one;\nk_gain = gain * one;\nout1 = cycle(k_freq * pow(2, k_oct)) * k_amp * k_gain;",
                                    "fontname": "Arial",
                                    "fontsize": 12.0
                                }
                            },
                            {
                                "box": {
                                    "maxclass": "newobj",
                                    "id": "obj-2",
                                    "numinlets": 1,
                                    "numoutlets": 0,
                                    "outlettype": [],
                                    "patching_rect": [ 50.0, 320.0, 30.0, 22.0 ],
                                    "text": "out 1",
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
                            }
                        ],
                        "dependency_cache": [],
                        "autosave": 0,
                        "bgcolor": [ 0.9, 0.9, 0.9, 1.0 ]
                    },
                    "varname": "synth"
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-2",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 200.0, 340.0, 58.0, 22.0 ],
                    "text": "midiin",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-3",
                    "numinlets": 2,
                    "numoutlets": 2,
                    "outlettype": [ "signal", "signal" ],
                    "patching_rect": [ 200.0, 400.0, 90.0, 22.0 ],
                    "text": "plugout~",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "live.dial",
                    "id": "obj-4",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "" ],
                    "patching_rect": [ 50.0, 100.0, 44.0, 66.0 ],
                    "parameter_enable": 1,
                    "presentation": 1,
                    "presentation_rect": [ 8.0, 8.0, 44.0, 48.0 ],
                    "varname": "freq",
                    "param_connect": "synth::freq",
                    "saved_attribute_attributes": {
                        "valueof": {
                            "parameter_initial": [ 220.0 ],
                            "parameter_initial_enable": 1,
                            "parameter_longname": "freq",
                            "parameter_shortname": "freq",
                            "parameter_mmin": 20.0,
                            "parameter_mmax": 2000.0,
                            "parameter_modmode": 4,
                            "parameter_type": 0,
                            "parameter_unitstyle": 3
                        }
                    },
                    "annotation": "freq control. Range: 20-2000 Hz",
                    "annotation_name": "freq"
                }
            },
            {
                "box": {
                    "maxclass": "live.dial",
                    "id": "obj-5",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "" ],
                    "patching_rect": [ 110.0, 100.0, 44.0, 66.0 ],
                    "parameter_enable": 1,
                    "presentation": 1,
                    "presentation_rect": [ 60.0, 8.0, 44.0, 48.0 ],
                    "varname": "amp",
                    "param_connect": "synth::amp",
                    "saved_attribute_attributes": {
                        "valueof": {
                            "parameter_initial": [ 0.5 ],
                            "parameter_initial_enable": 1,
                            "parameter_longname": "amp",
                            "parameter_shortname": "amp",
                            "parameter_mmin": 0.0,
                            "parameter_mmax": 1.0,
                            "parameter_modmode": 0,
                            "parameter_type": 0,
                            "parameter_unitstyle": 1
                        }
                    },
                    "annotation": "amp control. Range: 0-1",
                    "annotation_name": "amp"
                }
            },
            {
                "box": {
                    "maxclass": "live.dial",
                    "id": "obj-6",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "" ],
                    "patching_rect": [ 170.0, 100.0, 44.0, 66.0 ],
                    "parameter_enable": 1,
                    "presentation": 1,
                    "presentation_rect": [ 112.0, 8.0, 44.0, 48.0 ],
                    "varname": "out_gain",
                    "saved_attribute_attributes": {
                        "valueof": {
                            "parameter_initial": [ -12.0 ],
                            "parameter_initial_enable": 1,
                            "parameter_longname": "Out Gain",
                            "parameter_shortname": "Out Gain",
                            "parameter_mmin": -70.0,
                            "parameter_mmax": 0.0,
                            "parameter_modmode": 0,
                            "parameter_type": 0,
                            "parameter_unitstyle": 4
                        }
                    },
                    "annotation": "Out Gain control. Range: -70-0 dB",
                    "annotation_name": "Out Gain"
                }
            },
            {
                "box": {
                    "maxclass": "live.dial",
                    "id": "obj-7",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "" ],
                    "patching_rect": [ 230.0, 100.0, 44.0, 66.0 ],
                    "parameter_enable": 1,
                    "presentation": 1,
                    "presentation_rect": [ 164.0, 8.0, 44.0, 48.0 ],
                    "varname": "Octave",
                    "saved_attribute_attributes": {
                        "valueof": {
                            "parameter_initial": [ 0 ],
                            "parameter_initial_enable": 1,
                            "parameter_longname": "Octave",
                            "parameter_shortname": "Octave",
                            "parameter_mmin": -2,
                            "parameter_mmax": 2,
                            "parameter_modmode": 0,
                            "parameter_type": 1,
                            "parameter_unitstyle": 0
                        }
                    },
                    "annotation": "Octave control. Range: -2-2",
                    "annotation_name": "Octave"
                }
            },
            {
                "box": {
                    "maxclass": "live.dial",
                    "id": "obj-8",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "" ],
                    "patching_rect": [ 290.0, 100.0, 44.0, 66.0 ],
                    "parameter_enable": 1,
                    "presentation": 1,
                    "presentation_rect": [ 216.0, 8.0, 44.0, 48.0 ],
                    "varname": "Attack",
                    "saved_attribute_attributes": {
                        "valueof": {
                            "parameter_initial": [ 10.0 ],
                            "parameter_initial_enable": 1,
                            "parameter_longname": "Attack",
                            "parameter_shortname": "Attack",
                            "parameter_mmin": 1.0,
                            "parameter_mmax": 500.0,
                            "parameter_modmode": 0,
                            "parameter_type": 0,
                            "parameter_unitstyle": 2
                        }
                    },
                    "annotation": "Attack control. Range: 1-500 ms",
                    "annotation_name": "Attack"
                }
            },
            {
                "box": {
                    "maxclass": "live.dial",
                    "id": "obj-9",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "" ],
                    "patching_rect": [ 350.0, 100.0, 44.0, 66.0 ],
                    "parameter_enable": 1,
                    "presentation": 1,
                    "presentation_rect": [ 268.0, 8.0, 44.0, 48.0 ],
                    "varname": "filter_envelope_amount",
                    "saved_attribute_attributes": {
                        "valueof": {
                            "parameter_initial": [ 0.0 ],
                            "parameter_initial_enable": 1,
                            "parameter_longname": "Filter Envelope Amount",
                            "parameter_shortname": "Amount",
                            "parameter_mmin": 0.0,
                            "parameter_mmax": 1.0,
                            "parameter_modmode": 0,
                            "parameter_type": 0,
                            "parameter_unitstyle": 1
                        }
                    },
                    "annotation": "Filter Envelope Amount control. Range: 0-1",
                    "annotation_name": "Filter Envelope Amount"
                }
            },
            {
                "box": {
                    "maxclass": "live.dial",
                    "id": "obj-10",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "" ],
                    "patching_rect": [ 410.0, 100.0, 44.0, 66.0 ],
                    "parameter_enable": 1,
                    "presentation": 1,
                    "presentation_rect": [ 320.0, 8.0, 44.0, 48.0 ],
                    "varname": "pitch_envelope_amount",
                    "saved_attribute_attributes": {
                        "valueof": {
                            "parameter_initial": [ 0.0 ],
                            "parameter_initial_enable": 1,
                            "parameter_longname": "Pitch Envelope Amount",
                            "parameter_shortname": "Amount2",
                            "parameter_mmin": 0.0,
                            "parameter_mmax": 1.0,
                            "parameter_modmode": 0,
                            "parameter_type": 0,
                            "parameter_unitstyle": 1
                        }
                    },
                    "annotation": "Pitch Envelope Amount control. Range: 0-1",
                    "annotation_name": "Pitch Envelope Amount"
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-11",
                    "numinlets": 1,
                    "numoutlets": 3,
                    "outlettype": [ "", "", "" ],
                    "patching_rect": [ 50.0, 20.0, 121.0, 22.0 ],
                    "text": "live.thisdevice",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-12",
                    "numinlets": 1,
                    "numoutlets": 5,
                    "outlettype": [ "", "", "", "", "" ],
                    "patching_rect": [ 50.0, 60.0, 93.0, 22.0 ],
                    "text": "t b b b b b",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-13",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 350.0, 400.0, 86.0, 22.0 ],
                    "text": "live.banks",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-14",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 381.0, 180.0, 51.0, 22.0 ],
                    "text": "dbtoa",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-15",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 381.0, 225.0, 100.0, 22.0 ],
                    "text": "prepend gain",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            },
            {
                "box": {
                    "maxclass": "newobj",
                    "id": "obj-16",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 491.0, 180.0, 114.0, 22.0 ],
                    "text": "prepend octave",
                    "fontname": "Arial",
                    "fontsize": 12.0
                }
            }
        ],
        "lines": [
            {
                "patchline": {
                    "source": [ "obj-1", 0 ],
                    "destination": [ "obj-3", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-1", 0 ],
                    "destination": [ "obj-3", 1 ]
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
                    "source": [ "obj-12", 0 ],
                    "destination": [ "obj-6", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-12", 1 ],
                    "destination": [ "obj-7", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-12", 2 ],
                    "destination": [ "obj-8", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-12", 3 ],
                    "destination": [ "obj-9", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-12", 4 ],
                    "destination": [ "obj-10", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-6", 0 ],
                    "destination": [ "obj-14", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-14", 0 ],
                    "destination": [ "obj-15", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-15", 0 ],
                    "destination": [ "obj-1", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-7", 0 ],
                    "destination": [ "obj-16", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-16", 0 ],
                    "destination": [ "obj-1", 0 ]
                }
            }
        ],
        "dependency_cache": [],
        "autosave": 0,
        "parameters": {
            "parameterbanks": {
                "0": {
                    "index": 0,
                    "name": "Filter",
                    "parameters": [ "freq", "Filter Envelope Amount", "-", "-", "-", "-", "-", "-" ]
                },
                "1": {
                    "index": 1,
                    "name": "Amp",
                    "parameters": [ "amp", "Out Gain", "-", "-", "-", "-", "-", "-" ]
                },
                "2": {
                    "index": 2,
                    "name": "Pitch",
                    "parameters": [ "Octave", "Pitch Envelope Amount", "-", "-", "-", "-", "-", "-" ]
                },
                "3": {
                    "index": 3,
                    "name": "Envelope",
                    "parameters": [ "Attack", "-", "-", "-", "-", "-", "-", "-" ]
                }
            }
        },
        "openrect": [ 0.0, 0.0, 0.0, 169.0 ],
        "latency": 0
    }
}