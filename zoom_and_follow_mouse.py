
from math import sqrt
from platform import system
import os
import json
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

    def __init__(self, cwd, settings_dir, settings_file_name):
        log("Run ZoomSettings init")
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

    def save(self, settings):
        try:
            log(f"Saving to {self.file_path}")
            f = open(self.file_path, "w" if os.path.exists(self.file_path) else "a")
            f.write(str(json.dumps(
                json.loads(obs.obs_data_get_json(settings)),
                sort_keys=True,
                indent=4
            )))
            f.close()
        except Exception as e:
            print(e, "Cannot write settings to file")

    def load(self):
        try:
            log("Loading settings")
            if not os.path.exists(self.file_path):
                self.create()
            f = open(self.file_path)
            d = json.load(f)
            f.close()
            return d
        except Exception as e:
            print(e, "Cannot load settings from file")


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

    lock = False  # Activate zoom mode?
    track = True  # Follow mouse cursor while in zoom mode?
    update = True  # Animating between zoom in and out?
    ticking = False  # To prevent subscribing to timer multiple times
    zi_timer = zo_timer = 0  # Frames spent on zoom in/out animations
    windows = window_titles = monitor = window = window_handle \
        = window_name = ''
    monitors = pwc.getAllScreens()
    monitors_key = list(dict.keys(monitors))
    monitor_override = manual_offset = monitor_size_override = False
    monitor_override_id = ''
    zoom_x = zoom_y = 0  # Zoomed-in window top left location
    zoom_x_target = zoom_y_target = 0  # Interpolate the above towards these
    # Actual source (window or monitor) location and dimensions from the system
    source_w_raw = source_h_raw = source_x_raw = source_y_raw = 0
    # Overriden source location and dimensions from settings
    source_x_offset = source_y_offset \
        = source_w_override = source_h_override = 0
    # Computed source location and dimensions that depend on whether override
    # settings are enabled.
    source_x = source_y = source_w = source_h = 0
    source_load = False
    refresh_rate = 16
    source_name = source_type = ''
    zoom_w = 1280
    zoom_h = 720
    active_border = 0.15
    max_speed = 160
    smooth = 1.0
    zoom_time = 300

    def update_sources(self, settings_update = False):
        """
        Update the list of Windows and Monitors from PyWinCtl
        """
        if not (sys == "Darwin") or not settings_update:
            self.windows = pwc.getAllWindows()
            self.monitors = pwc.getAllScreens()
            self.monitors_key = list(dict.keys(self.monitors))


# -------------------------------------------------------------------
class Callbacks:
    log("Create Callbacks")


# -------------------------------------------------------------------
zs = ZoomSettings(cwd, settings_dir, settings_file_name)
zoom = CursorWindow()
cb = Callbacks()


# -------------------------------------------------------------------
def populate_list_property_with_source_names(list_property):
    """
    Updates Zoom Source's available options.

    Checks a source against SOURCES to determine availability.
    """
    global new_source

    log("Updating Source List")
    zoom.update_sources()
    sources = obs.obs_enum_sources()
    log(f"System: {sys}")
    if sources is not None:
        obs.obs_property_list_clear(list_property)
        obs.obs_property_list_add_string(list_property, "", "")
        for source in sources:
            if sys == "Darwin":
                log(f"{obs.obs_source_get_name(source)} | {source}")
            # Print this value if a source isn't showing in the UI as expected
            # and add it to SOURCES above for either window or monitor capture.
            source_type = obs.obs_source_get_id(source)
            if source_type in SOURCES.all_sources():
                name_val = name = obs.obs_source_get_name(source)
                obs.obs_property_list_add_string(list_property, name_val, name)
        zoom.source_load = True
    obs.source_list_release(sources)
    new_source = True
    log(f"New source: {str(new_source)}")


# -------------------------------------------------------------------
def script_description():
    return description


def script_defaults(settings):
    log("Run script_defaults")


def script_update(settings):
    log("Run script_update")
    ZoomSettings.save(zs, settings)


def script_properties():
    log("Run script_properties")

    global props
    props = obs.obs_properties_create()

    sources = obs.obs_properties_add_list(
        props,
        "source",
        "Zoom Source",
        obs.OBS_COMBO_TYPE_LIST,
        obs.OBS_COMBO_FORMAT_STRING,
    )

    populate_list_property_with_source_names(sources)

    return props


def script_load(settings):
    log("Run script_load")

    setting_pairs = {
        "source": "source_name",
    }

    settings_import = zs.load()

    for setting in settings_import.keys():
        if setting in setting_pairs.keys():
            match = setting_pairs.get(setting)
            if match in dir(zoom):
                setattr(zoom, match, settings_import[setting])
    


def script_unload():
    log("Run script_unload")


def script_save(settings):
    log("Run script_save")