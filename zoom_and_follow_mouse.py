from json import loads
from math import sqrt
from platform import system
import os
import pywinctl as pwc
import obspython as obs

version = "v.2023.09.01"
debug = True
sys= system()
cwd = os.path.dirname(os.path.realpath(__file__))
file_name = os.path.basename(__file__).removesuffix(".py")
settings_dir = "settings"
settings_file_name = f"{file_name}.json"
zoom_id_tog = None
follow_id_tog = None
load_sources_hk = None
load_monitors_hk = None
new_source = True
props = None

ZOOM_NAME_TOG = f"{file_name}.zoom.toggle"
FOLLOW_NAME_TOG = f"{file_name}.follow.toggle"
LOAD_SOURCES_NAME_HK = f"{file_name}.sources.hk"
LOAD_MONITORS_NAME_HK = f"{file_name}.monitors.hk"
ZOOM_DESC_TOG = "Enable/Disable Mouse Zoom"
FOLLOW_DESC_TOG = "Enable/Disable Mouse Follow"
LOAD_SOURCES_DESC_HK = "Load Sources"
LOAD_MONITORS_DESC_HK = "Load Monitors"
USE_MANUAL_MONITOR_SIZE = "Manual Monitor Size"
CROP_FILTER_NAME = f"ZoomCrop_{file_name}"

"""
This script is intended to be called from OBS Studio. Provides
mouse-based zoom and tracking for desktop/monitor/window/game sources.
For more information please visit:
https://github.com/tryptech/obs-zoom-and-follow
"""

description = (
    "Crops and resizes a source to simulate a zoomed in tracked to"
    " the mouse.\n\n"
    + "Set activation hotkey in Settings.\n\n"
    + "Active Border enables lazy/smooth tracking; border size"
    "calculated as percent of smallest dimension. "
    + "Border of 50% keeps mouse locked in the center of the zoom"
    " frame\n\n"
    + "Manual Monitor Dimensions constrain the zoom to just the area in the"
    " defined size. Useful for only zooming in a smaller area in ultrawide"
    " monitors, for instance.\n\n"
    + "Manual Offset will move, relative to the top left of the monitor/source,"
    " the constrained zoom area. In the ultrawide monitor example, this can be"
    " used to offset the constrained area to be at the right of the screen,"
    " preventing the zoom from following the cursor to the left side.\n\n"
    + "By tryptech (@yo_tryptech / tryptech#1112)\n\n"
    + f"{version}"
)

def get_cursor_position():
    return pwc.getMousePos()

def log(s):
    global debug
    if debug:
        print(s)


# -------------------------------------------------------------------
class ZoomSettings:
    log("Create ZoomSettings")

    file_dir = ""
    file_name = ""
    file_path = ""

    def __init__(self):
        self.file_dir = os.path.join(cwd,settings_dir)
        self.file_name = settings_file_name
        self.file_path = os.path.join(self.file_dir,self.file_name)

        if settings_dir:
            log(f"Checking settings directory: {os.path.join(cwd,settings_dir)}")
            if not os.path.exists(self.file_dir):
                log("Settings directory does not exist")
                log("Creating settings directory")
                os.makedirs(self.file_dir)
            log("Settings directory found")

    def save(self):
        try:
            log("a")
        except Exception as e:
            print(e, "Cannot write settings to file")

    def load(self):
        try:
            log("a")
        except Exception as e:
            print(e, "Cannot load settings from file")

    def create(self):
        if not os.path.exists(self.file_path):
            log("Making new settings file")
        else:
            log("Settings file already exists")


# -------------------------------------------------------------------
class WindowCaptureSources:
    def __init__(self, sources):
        self.sources = sources


class MonitorCaptureSources:
    def __init__(self, windows, macos, linux):
        self.windows = windows
        self.macos = macos
        self.linux = linux

    def all_sources(self):
        return self.windows | self.macos | self.linux


class AppleSiliconCaptureSources:
    def __init__(self, sources):
        self.sources = sources


class CaptureSources:
    def __init__(self, window, monitor, applesilicon):
        self.window = window
        self.monitor = monitor
        self.applesilicon = applesilicon

    def all_sources(self):
        return self.window.sources | self.monitor.all_sources() | self.applesilicon.sources


# Matches against values returned by obs.obs_source_get_id(source).
# See populate_list_property_with_source_names() below.
SOURCES = CaptureSources(
    window=WindowCaptureSources({'window_capture', 'game_capture'}),
    monitor=MonitorCaptureSources(
        windows={'monitor_capture'},
        macos={'display_capture'},
        linux={'monitor_capture', 'xshm_input',
               'pipewire-desktop-capture-source'}
    ),
    applesilicon=AppleSiliconCaptureSources({'screen_capture','screen_capture'})
)


class CursorWindow:
    log("Create CursorWindow")


# -------------------------------------------------------------------
class Callbacks:
    log("Create Callbacks")

# -------------------------------------------------------------------
zs = ZoomSettings()
zoom = CursorWindow()
cb = Callbacks()

# -------------------------------------------------------------------
def script_description():
    return description


def script_defaults(settings):
    log("Run script_defaults")


def script_update(settings):
    log("Run script_updates")


def script_properties():
    log("Run script_properties")


def script_load(settings):
    log("Run script_load")

    settings = zs.load()


def script_unload():
    log("Run script_unload")


def script_save(settings):
    log("Run script_save")