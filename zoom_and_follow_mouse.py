from inspect import ismethod, isfunction
from math import sqrt
from platform import system
import os
import json
import pywinctl as pwc
import obspython as obs

version = "v.2023.09.01"
debug = False
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
ZOOM_DESC_TOG = f"Enable/Disable Mouse Zoom ({file_name})"
FOLLOW_DESC_TOG = f"Enable/Disable Mouse Follow ({file_name})"
LOAD_SOURCES_DESC_HK = f"Load Sources ({file_name})"
LOAD_MONITORS_DESC_HK = f"Load Monitors ({file_name})"
USE_MANUAL_MONITOR_SIZE = "Manual Monitor Size"
CROP_FILTER_NAME = f"ZoomCrop_{file_name}"

"""
This script is intended to be called from OBS Studio. Provides
mouse-based zoom and tracking for desktop/monitor/window/game sources.
For more information please visit:
https://github.com/tryptech/obs-zoom-and-follow
"""

description = (f"""Crops and resizes a source to simulate a zoomed in tracked to the mouse.=n
Set activation hotkey in Settings.\n
Active Border enables lazy/smooth tracking; border size calculated as percent of smallest dimension. Border of 50% keeps mouse locked in the center of the zoom frame.\n
Manual Monitor Dimensions constrain the zoom to just the area in the defined size; useful for restricting zooming to a small area in large format monitors.\n
Manual Offset will move, relative to the top left of the monitor/source, the constrained zoom area. In the large format monitor example, this can be used to offset the constrained area to be on the right of the screen, preventing the zoom from following the cursor to the left side.\n
By tryptech
{version}""")

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

    def save(self, settings, *args, **kwargs):
        log(f"Saving to {self.file_path}")
        try:
            f = open(self.file_path,
                     "w" if os.path.exists(self.file_path)
                     else "a")
            output = json.loads(obs.obs_data_get_json(settings))
            if kwargs:
                for key, value in kwargs.items():              
                    skipped_values = ["windows", "monitors"]
                    new_keys = [i for i in dir(value)
                                if not i.startswith("_")
                                and i not in skipped_values
                                and not ismethod(getattr(value, i))
                                and not isfunction(getattr(value, i))]
                    new_values = [getattr(value, i) for i in new_keys]
                    new_dict = dict(zip(new_keys, new_values))
                    output[key] = new_dict
            log(output)
            f.write(str(json.dumps(output,
                sort_keys=True,
                indent=4
            )))
            f.close()
        except Exception as e:
            log(f"{e}: Cannot write settings to file")

    def load(self):
        log("Loading settings")
        try:
            if not os.path.exists(self.file_path):
                self.create()
            f = open(self.file_path)
            d = json.load(f)
            f.close()
            return d
        except Exception as e:
            log(f"{e}: Cannot load settings from file")
            return None


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
    """
    Attributes

    lock                    |   Toggles zoom
    track                   |   Toggles follow
    update                  |   Animation status
    ticking                 |   Timer subscribe lock
    active_border           |   Ratio of smallest CaptureWindow dimension to track
    manual_offset           |   
    max_speed               |   Maximum CaptureWindow movement per frame (px)
    monitor                 |   
    monitor_override        |   
    monitor_override_id     |   
    monitor_size_override   |   
    monitors                |   Cached list of monitor objects as reported by PyWinCtl
    monitors_key            |   Cached list of monitors as reported by PyWinCtl
    refresh_rate            |   OBS frame rate
    smooth                  |   Smoothing factor for CaptureWindow movement (0.0 - 1.0)
    source_load             |   
    source_name             |   Name of source to be modified
    source_type             |   Type of source to be modified
    source_w_raw            |   Source width as reported by PyWinCtl
    source_h_raw            |   Source height as reported by PyWinCtl
    source_x_raw            |   Source x position as reported by PyWinCtl
    source_y_raw            |   Source y position as reported by PyWinCtl 
    source_w_override       |   Custom source width
    source_h_override       |   Custom source height
    source_x_offset         |   Custom source x offset relative to source_x_raw
    source_y_offset         |   Custom source y offset relative to source_y_raw
    source_w                |   Final computed source width
    source_h                |   Final computed source height
    source_x                |   Final computed source x position
    source_y                |   Final computed source y position
    window                  |   
    window_handle           |   
    window_name             |   
    windows                 |   
    zi_timer                |   Zoom in animation frame timer
    zo_timer                |   Zoom out animation frame timer
    zoom_time               |   Zoom animation length (ms)
    zoom_h                  |   CaptureWindow Height
    zoom_w                  |   CaptureWindow Width
    zoom_x                  |   CaptureWindow x position (relative to source)
    zoom_y                  |   CaptureWindow y position (relative to source)
    zoom_x_target           |   CaptureWindow x interpolation target
    zoom_y_target           |   CaptureWindow y interpolation target

    """
    log("Create CursorWindow")

    lock = False
    track = True
    update = True
    ticking = False
    zi_timer = zo_timer = 0
    windows = monitor = window = window_handle = window_name = ''
    monitors = pwc.getAllScreens()
    monitors_key = list(dict.keys(monitors))
    monitor_override = manual_offset = monitor_size_override = False
    monitor_override_id = ''
    zoom_x = zoom_y = 0
    zoom_x_target = zoom_y_target = 0
    source_w_raw = source_h_raw = source_x_raw = source_y_raw = 0
    source_x_offset = source_y_offset \
        = source_w_override = source_h_override = 0
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

    def update_window_dim(self, window):
        """
        Update the stored window dimensions to those of the selected
        window

        :param window: Window with new dimensions
        """
        log("Updating stored dimensions to match current dimensions")
        if window != None:
            # FIXME: on macos get window bounds results in an error and
            # does not work
            # NSInternalInconsistencyException - NSWindow drag regions
            # should only be invalidated on the Main Thread!
            window_dim = window.getClientFrame()
            if (self.source_w_raw != window_dim.right - window_dim.left
                or self.source_h_raw != window_dim.bottom - window_dim.top
                or self.source_x_raw != window_dim.left
                    or self.source_y_raw != window_dim.top):
                log("OLD")
                log("Width, Height, X, Y")
                log(f"{self.source_w_raw}, {self.source_h_raw}, {self.source_x_raw},"
                      f" {self.source_y_raw}")
                self.source_w_raw = window_dim.right - window_dim.left
                self.source_h_raw = window_dim.bottom - window_dim.top
                self.source_x_raw = window_dim.left
                self.source_y_raw = window_dim.top
                log("NEW")
                log("Width, Height, X, Y")
                log(f"{self.source_w_raw}, {self.source_h_raw}, {self.source_x_raw},"
                      f" {self.source_y_raw}")
            else:
                log("Dimensions did not change")

    def update_monitor_dim(self, monitor):
        """
        Update the stored dimensions based on the selected monitor

        :param monitor: Single monitor as returned from the PyWinCtl
            Monitor function getAllScreens()
        """
        log(
            f"Updating stored dimensions to match monitor's dimensions | {monitor}")
        if (self.source_w_raw != monitor['size'].width
            or self.source_h_raw != monitor['size'].height
            or self.source_x_raw != monitor['pos'].x
                or self.source_y_raw != monitor['pos'].y):
            log("OLD")
            log("Width, Height, X, Y")
            log(f"{self.source_w_raw}, {self.source_h_raw}, {self.source_x_raw}, \
                {self.source_y_raw}")
            self.source_w_raw = monitor['size'].width
            self.source_h_raw = monitor['size'].height
            self.source_x_raw = monitor['pos'].x
            self.source_y_raw = monitor['pos'].y
            log("NEW")
            log("Width, Height, X, Y")
            log(f"{self.source_w_raw}, {self.source_h_raw}, {self.source_x_raw}, \
                {self.source_y_raw}")
        else:
            log("Dimensions did not change")

    def window_capture_gen(self, data):
        """
        TODO: More Linux testing, specifically with handles Windows
        capture for Windows and Linux. In Windows, application data is
        stored as "Title:WindowClass:Executable"
        """
        global new_source

        try:
            # Assuming the OBS data is formatted correctly, we should
            # be able to identify the window
            # If New Source/Init
            # If Handle Exists
            # Else
            if new_source:
                # If new source selected / OBS initialize
                # Build window, window_handle, and
                # window_name
                log("New Source")
                log("Retrieving target window info from OBS")
                self.window_name = data['window'].split(":")[0]
                log(f"Searching for: {self.window_name}")
                for w in self.windows:
                    if w.title == self.window_name:
                        window_match = w
                        self.window_handle = w.getHandle()
                new_source = False
                log(f"Window Match: {window_match.title}")
                log("Window Match Handle:"
                      f" {str(self.window_handle)}")
            if self.window_handle != '':
                # If window handle is already stored
                # Get window based on handle
                # Check if name needs changing
                log(f"Handle exists: {str(self.window_handle)}")
                handle_match = False
                for w in self.windows:
                    if w.getHandle() == self.window_handle:
                        handle_match = True
                        log(
                            f"Found Handle: {str(w.getHandle())} | {self.window}")
                        window_match = w
                        if window_match.title != self.window:
                            log("Changing target title")
                            log(f"Old Title: {self.window_name}")
                            self.window_name = w.title
                            log(f"New Title: {self.window_name}")
                if handle_match == False:
                    # TODO: If the handle no longer exists,
                    # eg. Window or App closed
                    raise
            else:
                log("I don't know how it gets here.")
                window_match = None
                # TODO:
        except:
            log(f"Source {self.source_name} has changed."
                  " Select new source window")
            window_match = None
        return window_match

    def monitor_capture_gen(self, data):
        """
        If monitor override, update with monitor override
        Else if no monitor ID, monitor does not exist
        Else search for the monitor and update
        """
        monitor_id = data.get('monitor', None)
        if len(self.monitors.items()) == 1:
            log("Only one monitor detected. Forcing override.")
            for monitor in self.monitors.items():
                self.update_monitor_dim(monitor[1])
        elif self.monitor_override is True:
            log(f"Monitor Override: {self.monitor_override}")
            for monitor in self.monitors.items():
                if monitor[0] == self.monitors_key[
                        self.monitor_override_id]:
                    self.update_monitor_dim(monitor[1])
        elif monitor_id == None:
            log(f"Key 'monitor' does not exist in {data}")
        else:
            log(f"Searching for monitor {monitor_id}")
            for monitor in self.monitors.items():
                if (monitor[1]['id'] == monitor_id):
                    log(f"Found monitor {monitor[1]['id']} | {monitor}")
                    self.update_monitor_dim(monitor[1])

    def window_capture_mac(self, data):
        """
        Window capture for macOS
        macos uses an exclusive property 'window_name' pywinctl does not
        report application windows correctly for macos yet, so we must
        capture based on the actual window name and not based on the
        application like we do for windows.
        """

        self.window_name = data.get('window_name')
        # TODO: implement

    def screen_capture_mac(self, data):
        """
        From macOS 12.5+, OBS reports all window and display captures
        as the same type.

        data.type is in {0, 1, 2} where:
            DISPLAY = 0
            WINDOW = 1
            APPLICATION = 2
        
        Use is expected to be for DISPLAY or WINDOW
        """
        log("Apple Silicon")
        screen_capture_type = data.get('type')
        if (screen_capture_type == 0):
            monitor_id = data.get('display')
            for monitor in self.monitors.items():
                if (monitor[1]['id'] == monitor_id):
                    log(f"Found monitor {monitor[1]['id']} | {monitor[0]}")
                    self.update_monitor_dim(monitor[1])

    def monitor_capture_mac(self, data):
        """
        The 'display' property is an index value and not the true
        monitor id. It is only returned when there is more than one
        monitor on your system. We will assume that the order of the
        monitors returned from pywinctl are in the same order that OBS
        is assigning the display index value.
        """
        monitor_index = data.get('display', 0)
        log(f"Retrieving monitor {monitor_index}")
        for monitor in self.monitors.items():
            if (monitor['id'] == monitor_index):
                log(f"Found monitor {monitor['id']} | {monitor}")
                self.update_monitor_dim(monitor)

    def update_computed_source_values(self):
        """
        Compute source location and size with optional overrides applied
        """
        if self.manual_offset:
            self.source_x = self.source_x_raw + self.source_x_offset
            self.source_y = self.source_y_raw + self.source_y_offset
        else:
            self.source_x = self.source_x_raw
            self.source_y = self.source_y_raw

        if self.monitor_size_override:
            self.source_w = self.source_w_override
            self.source_h = self.source_h_override
        else:
            self.source_w = self.source_w_raw
            self.source_h = self.source_h_raw

    def update_source_size(self):
        """
        Adjusts the source size variables based on the source given
        """
        global new_source

        try:
            # Try to pull the data for the source object
            # OBS stores the monitor index/window target in the
            # window/game/display sources settings
            # Info is stored in a JSON format
            source = obs.obs_get_source_by_name(self.source_name)
            source_settings = obs.obs_source_get_settings(source)
            data = json.loads(obs.obs_data_get_json(source_settings))
        except:
            # If it cannot be pulled, it is likely one of the following:
            #   The source no longer exists
            #   The source's name has changed
            #   OBS does not have the sources loaded yet when launching
            #       the script on start

            log("Source '" + self.source_name + "' not found.")
            log(obs.obs_get_source_by_name(self.source_name))
        else:
            # If the source data is pulled, it exists. Therefore other
            # information must also exists. Source Type is pulled to
            # determine if the source is a display, game, or window

            log(f"Source loaded successfully: {self.source_type}")
            self.source_type = obs.obs_source_get_id(source)
            log(f"Source Type: {self.source_type}")
            if (self.source_type in SOURCES.window.sources):
                window_match = ''
                if 'window_name' in data:
                    self.window_capture_mac(data)
                elif 'window' in data:
                    window_match = self.window_capture_gen(data)
                if window_match is not None:
                    log("Proceeding to resize")
                    self.window = pwc.getWindowsWithTitle(self.window_name)[0]
                    self.update_window_dim(self.window)
            elif (self.source_type in SOURCES.monitor.windows | SOURCES.monitor.linux):
                self.monitor_capture_gen(data)
            elif (self.source_type in SOURCES.applesilicon.sources):
                self.screen_capture_mac(data)
            elif (self.source_type in SOURCES.monitor.macos):
                self.monitor_capture_mac(data)

            self.update_computed_source_values()

    @staticmethod
    def cubic_in_out(p):
        """
        Cubic in/out easing function. Accelerates until halfway, then
        decelerates.

        :param p: Linear temporal percent progress through easing from
            0 to 1
        :return: Adjusted percent progress
        """
        if p < 0.5:
            return 4 * p * p * p
        else:
            f = (2 * p) - 2
            return 0.5 * f * f * f + 1

    @staticmethod
    def check_offset(arg1, arg2, smooth):
        """
        Checks if a given value is offset from pivot value and provides
        an adjustment towards the pivot based on a smoothing factor

        :param arg1: Pivot value
        :param arg2: Checked value
        :param smooth: Smoothing factor; larger values adjusts more smoothly
        :return: Adjustment value
        """
        return round((arg1 - arg2) / smooth)

    def follow(self, mousePos):
        """
        Updates the position of the zoom window.

        :param mousePos: [x,y] position of the mouse on the canvas of
            all connected displays
        :return: If the zoom window was moved
        """
        track = False

        # Don't follow cursor when it is outside the source in both dimensions
        if (mousePos.x > (self.source_x + self.source_w)
            or mousePos.x < self.source_x) \
                and (mousePos.y > (self.source_y + self.source_h)
                     or mousePos.y < self.source_y):
            return False

        # When the mouse goes to the left edge or top edge of a Mac display, the cursor is set to 0,0
        # This attempts to ignore the mouse coordinates are set to that value on Mac only.
        if sys == 'Darwin' and (mousePos[0] == 0 or mousePos[1] == 0):
            return False

        # Get active zone edges relative to the source
        use_lazy_tracking = self.active_border < 0.5
        if use_lazy_tracking:
            # Find border size in pixels from shortest dimension (usually height)
            border_size = int(min(self.zoom_w, self.zoom_h) * self.active_border)
            zoom_edge_left = self.zoom_x_target + border_size
            zoom_edge_right = self.zoom_x_target + self.zoom_w - border_size
            zoom_edge_top = self.zoom_y_target + border_size
            zoom_edge_bottom = self.zoom_y_target + self.zoom_h - border_size
        else:
            # Active zone edges are at the center of the zoom window to keep
            # the cursor there at all times
            zoom_edge_left = zoom_edge_right = \
                self.zoom_x_target + int(self.zoom_w * 0.5)
            zoom_edge_top = zoom_edge_bottom = \
                self.zoom_y_target + int(self.zoom_h * 0.5)

        # Cursor relative to the source, because the crop values are relative
        source_mouse_x = mousePos.x - self.source_x_raw
        source_mouse_y = mousePos.y - self.source_y_raw

        if source_mouse_x < zoom_edge_left:
            self.zoom_x_target += source_mouse_x - zoom_edge_left
        elif source_mouse_x > zoom_edge_right:
            self.zoom_x_target += source_mouse_x - zoom_edge_right

        if source_mouse_y < zoom_edge_top:
            self.zoom_y_target += source_mouse_y - zoom_edge_top
        elif source_mouse_y > zoom_edge_bottom:
            self.zoom_y_target += source_mouse_y - zoom_edge_bottom

        # Only constrain zoom window to source when not centering mouse cursor
        if use_lazy_tracking:
            self.check_pos()

        # Set smoothing values
        smoothFactor = 1.0 if self.update else \
            max(1.0, self.smooth * 40 / self.refresh_rate)

        # Set x and y zoom offset
        offset_x = (self.zoom_x_target - self.zoom_x) / smoothFactor
        offset_y = (self.zoom_y_target - self.zoom_y) / smoothFactor

        # Max speed clamp. Don't clamp if animating zoom in/out or
        # if keeping cursor in center of zoom window
        if (not self.update) or use_lazy_tracking:
            speed_squared = (offset_x * offset_x) + (offset_y * offset_y)
            if speed_squared > (self.max_speed * self.max_speed):
                # Only spend CPU on sqrt if we really need it
                speed_factor = self.max_speed / sqrt(speed_squared)
                offset_x *= speed_factor
                offset_y *= speed_factor

        # Interpolate the values we apply to the crop filter
        self.zoom_x += offset_x
        self.zoom_y += offset_y

        return offset_x != 0 or offset_y != 0

    def check_pos(self):
        """
        Checks if zoom window exceeds window dimensions and clamps it if true
        """
        x_min = self.source_x
        x_max = self.source_w + self.source_x - self.zoom_w
        y_min = self.source_y
        y_max = self.source_h + self.source_y - self.zoom_h

        if self.zoom_x_target < x_min:
            self.zoom_x_target = x_min
        elif self.zoom_x_target > x_max:
            self.zoom_x_target = x_max
        if self.zoom_y_target < y_min:
            self.zoom_y_target = y_min
        elif self.zoom_y_target > y_max:
            self.zoom_y_target = y_max

    def center_on_cursor(self):
        """
        Instantly sets the zoom window target location to have the cursor at its
        center. If completely zoomed out (not interpolating) also sets the
        current location, so there's no visible travel from where the previous
        known location was when zooming in again.
        """
        mousePos = get_cursor_position()
        self.zoom_x_target = mousePos.x - self.zoom_w * 0.5
        self.zoom_y_target = mousePos.y - self.zoom_h * 0.5
        # Clamp to a valid location inside the source limits
        self.check_pos()

        # Are we fully zoomed out?
        if self.zi_timer == 0:
            # Synchronize the current crop zoom location
            self.zoom_x = self.zoom_x_target
            self.zoom_y = self.zoom_y_target
            log("Skip to cursor location")

    def obs_set_crop_settings(self, left, top, width, height):
        """
        Interfaces with OBS to set dimensions of the crop filter used for
        zooming, creating the filter if necessary.

        :param left: crop filter new left edge location in pixels
        :param top: crop filter new top edge location in pixels
        :param width: crop filter new width in pixels
        :param height: crop filter new height in pixels
        """
        source = obs.obs_get_source_by_name(self.source_name)
        crop = obs.obs_source_get_filter_by_name(source, CROP_FILTER_NAME)

        if crop is None:  # create filter
            obs_data = obs.obs_data_create()
            obs.obs_data_set_bool(obs_data, "relative", False)
            obs_crop_filter = obs.obs_source_create_private(
                "crop_filter",
                CROP_FILTER_NAME,
                obs_data)
            obs.obs_source_filter_add(source, obs_crop_filter)
            obs.obs_source_release(obs_crop_filter)
            obs.obs_data_release(obs_data)

        crop_settings = obs.obs_source_get_settings(crop)

        def set_crop_setting(name, value):
            obs.obs_data_set_int(crop_settings, name, value)

        set_crop_setting("left", left)
        set_crop_setting("top", top)
        set_crop_setting("cx", width)
        set_crop_setting("cy", height)

        obs.obs_source_update(crop, crop_settings)

        obs.obs_data_release(crop_settings)
        obs.obs_source_release(source)
        obs.obs_source_release(crop)

    def set_crop(self):
        """
        Compute rectangle of the zoom window, interpolating for zoom in and out
        transitions and update the crop filter used for zooming in the source.
        """
        totalFrames = int(self.zoom_time / self.refresh_rate)
        crop_left = crop_top = crop_width = crop_height = 0

        if not self.lock:
            # Zooming out
            if self.zo_timer < totalFrames:
                self.zo_timer += 1
                # Zoom in will start from same animation position
                self.zi_timer = totalFrames - self.zo_timer
                time = self.cubic_in_out(self.zo_timer / totalFrames)
                crop_left = int(((1 - time) * self.zoom_x))
                crop_top = int(((1 - time) * self.zoom_y))
                crop_width = self.zoom_w + int(time * (self.source_w_raw - self.zoom_w))
                crop_height = self.zoom_h + int(time * (self.source_h_raw - self.zoom_h))
                self.update = True
            else:
                # Leave crop left and top as 0
                crop_width = self.source_w_raw
                crop_height = self.source_h_raw
                self.update = False
        else:
            # Zooming in
            if self.zi_timer < totalFrames:
                self.zi_timer += 1
                # Zoom out will start from same animation position
                self.zo_timer = totalFrames - self.zi_timer
                time = self.cubic_in_out(self.zi_timer / totalFrames)
                crop_left = int(time * self.zoom_x)
                crop_top = int(time * self.zoom_y)
                crop_width = self.source_w_raw - int(time * (self.source_w_raw - self.zoom_w))
                crop_height = self.source_h_raw - int(time * (self.source_h_raw - self.zoom_h))
                self.update = True if time < 0.8 else False
            else:
                crop_left = int(self.zoom_x)
                crop_top = int(self.zoom_y)
                crop_width = int(self.zoom_w)
                crop_height = int(self.zoom_h)
                self.update = False

        self.obs_set_crop_settings(crop_left, crop_top, crop_width, crop_height)

        # Stop ticking when zoom out is complete or
        # when zoomed in and not following the cursor
        if ((not self.lock) and (self.zo_timer >= totalFrames)) \
                or (self.lock and (not self.track) and (self.zi_timer >= totalFrames)):
            self.tick_disable()

    def tick_enable(self):
        if self.ticking:
            return

        # Update refresh rate in case user has changed settings. Otherwise
        # animations will feel slower/faster
        self.refresh_rate = int(obs.obs_get_frame_interval_ns() / 1000000)

        obs.timer_add(self.tick, self.refresh_rate)
        self.ticking = True
        log(f"Ticking: {self.ticking}")

    def tick_disable(self):
        obs.remove_current_callback()
        self.ticking = False
        log(f"Ticking: {self.ticking}")

    def tracking(self):
        """
        Tracking state function
        """
        if self.lock:
            if self.track or self.update:
                self.follow(get_cursor_position())
        self.set_crop()

    def tick(self):
        """
        Containing function that is run every frame
        """
        self.tracking()



# -------------------------------------------------------------------
zs = ZoomSettings(cwd, settings_dir, settings_file_name)
zoom = CursorWindow()


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


def populate_list_property_with_monitors(list_property):
    log("Updating Monitor List")
    if zoom.monitors is not None:
        obs.obs_property_list_clear(list_property)
        obs.obs_property_list_add_int(list_property, "", -1)
        monitor_index = 0
        for monitor in zoom.monitors:
            screen_size = pwc.getScreenSize(monitor)
            obs.obs_property_list_add_int(list_property,
                                          f"{monitor}: {screen_size.width} x {screen_size.height}",
                                          monitor_index)
            monitor_index += 1
    log("Monitor override list updated")


# -------------------------------------------------------------------
def script_description():
    return description


def script_defaults(settings):
    log("Run script_defaults")

    obs.obs_data_set_default_string(settings, "source", "")
    obs.obs_data_set_default_bool(settings,
                                  "Manual Monitor Override", False)
    obs.obs_data_set_default_bool(settings, "Manual Offset", False)
    obs.obs_data_set_default_int(settings, "Width", 1280)
    obs.obs_data_set_default_int(settings, "Height", 720)
    obs.obs_data_set_default_double(settings, "Border", 0.15)
    obs.obs_data_set_default_int(settings, "Speed", 160)
    obs.obs_data_set_default_double(settings, "Smooth", 1.0)
    obs.obs_data_set_default_int(settings, "Zoom", 300)
    obs.obs_data_set_default_int(settings, "Manual X Offset", 0)
    obs.obs_data_set_default_int(settings, "Manual Y Offset", 0)
    obs.obs_data_set_default_bool(settings, "debug", False)


def script_update(settings):
    log("Run script_update")
    ZoomSettings.save(zs, settings, CursorWindow=zoom)


def callback(props, prop, *args):
    log("Triggered callback")

    prop_name = obs.obs_property_name(prop)
    
    monitor = obs.obs_properties_get(props, "monitor")
    monitor_override = obs.obs_properties_get(props, "Manual Monitor Override")
    monitor_size_override = obs.obs_properties_get(props, "Manual Monitor Dim")
    refresh_monitor = obs.obs_properties_get(props, "Refresh monitors")
    source_type = zoom.source_type

    global debug
    debug = obs.obs_properties_get(props, "debug")
    
    if prop_name == "source":
        if sys != 'Darwin':
            populate_list_property_with_source_names(prop)
        if source_type in SOURCES.monitor.all_sources():
            obs.obs_property_set_visible(monitor_override, True)
            obs.obs_property_set_visible(refresh_monitor, True)
            obs.obs_property_set_visible(monitor_size_override, True)
            zoom.update_source_size()
        else:
            obs.obs_property_set_visible(monitor_override, False)
            obs.obs_property_set_visible(refresh_monitor, False)
            obs.obs_property_set_visible(monitor_size_override, False)

    if prop_name == "Refresh monitors":
        populate_list_property_with_monitors(prop)

    obs.obs_property_set_visible(
        obs.obs_properties_get(props, "Monitor Width"),
        zoom.monitor_size_override)
    obs.obs_property_set_visible(
        obs.obs_properties_get(props, "Monitor Height"),
        zoom.monitor_size_override)
    obs.obs_property_set_visible(
        obs.obs_properties_get(props, "Manual X Offset"),
        zoom.manual_offset)
    obs.obs_property_set_visible(
        obs.obs_properties_get(props, "Manual Y Offset"),
        zoom.manual_offset)
    obs.obs_property_set_visible(monitor, zoom.monitor_override
                                 and obs.obs_property_visible(monitor_override))
    
    return True


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

    ls = obs.obs_properties_add_button(props,
                                       "Reload sources",
                                       "Reload list of sources",
                                       lambda props, prop: True if callback(props, sources) else True)

    monitor_override = obs.obs_properties_add_bool(props,
                                                   "Manual Monitor Override",
                                                   "Enable Monitor Override")

    m = obs.obs_properties_add_list(
        props,
        "monitor",
        "Monitor Override",
        obs.OBS_COMBO_TYPE_LIST,
        obs.OBS_COMBO_FORMAT_INT,
    )

    populate_list_property_with_monitors(m)

    rm = obs.obs_properties_add_button(props,
                                       "Refresh monitors",
                                       "Refresh list of monitors",
                                       lambda props, prop: True if callback(props, m) else True)

    mon_size = obs.obs_properties_add_bool(props,
                                           "Manual Monitor Dim", "Enable Manual Monitor Dimensions")

    mon_w = obs.obs_properties_add_int(props,
                                       "Monitor Width", "Manual Monitor Width", -8000, 8000, 1)
    mon_h = obs.obs_properties_add_int(props,
                                       "Monitor Height", "Manual Monitor Height", -8000, 8000, 1)

    offset = obs.obs_properties_add_bool(props,
                                         "Manual Offset", "Enable Manual Offset")

    mx = obs.obs_properties_add_int(props,
                                    "Manual X Offset", "Manual X Offset", -8000, 8000, 1)
    my = obs.obs_properties_add_int(props,
                                    "Manual Y Offset", "Manual Y Offset", -8000, 8000, 1)

    obs.obs_properties_add_int(props,
                               "Width", "Zoom Window Width", 320, 3840, 1)
    obs.obs_properties_add_int(props,
                               "Height", "Zoom Window Height", 240, 3840, 1)
    obs.obs_properties_add_float_slider(props,
                                        "Border", "Active Border", 0, 0.5, 0.01)
    obs.obs_properties_add_int(props,
                               "Speed", "Max Scroll Speed", 0, 540, 10)
    obs.obs_properties_add_float_slider(props,
                                        "Smooth", "Smooth", 0, 10, 0.1)
    obs.obs_properties_add_int_slider(props,
                                      "Zoom", "Zoom Duration (ms)", 0, 1000, 1)

    debug_tog = obs.obs_properties_add_bool(props,
                                           "debug",
                                           "Enable debug logging")

    mon_show = (
        True if zoom.source_type in SOURCES.monitor.all_sources() else False)
    
    obs.obs_property_set_visible(monitor_override, mon_show)
    obs.obs_property_set_visible(m, zoom.monitor_override)
    obs.obs_property_set_visible(rm, zoom.monitor_override)
    obs.obs_property_set_visible(mon_h, zoom.monitor_size_override)
    obs.obs_property_set_visible(mon_w, zoom.monitor_size_override)
    obs.obs_property_set_visible(mx, zoom.manual_offset)
    obs.obs_property_set_visible(my, zoom.manual_offset)

    obs.obs_property_set_modified_callback(sources, callback)
    obs.obs_property_set_modified_callback(monitor_override, callback)
    obs.obs_property_set_modified_callback(mon_size, callback)
    obs.obs_property_set_modified_callback(offset, callback)
    obs.obs_property_set_modified_callback(debug_tog, callback)
    return props


def script_load(settings):
    log("Run script_load")

    setting_pairs = {
        "source": "source_name",
    }

    settings_updated = []

    settings_import = zs.load()

    if settings_import:
        for setting in settings_import.keys():
            match setting:
                case "CursorWindow":
                    for value in settings_import[setting]:
                        setattr(zoom, value, settings_import[setting][value])
                        settings_updated.append(f"zoom.{value}")
                case _:
                    if setting in setting_pairs.keys():
                        match = setting_pairs.get(setting)
                        if match in dir(zoom):
                            setattr(zoom, match, settings_import[setting])
                            settings_updated.append(setting)
    
    
    global zoom_id_tog
    zoom_id_tog = obs.obs_hotkey_register_frontend(
        ZOOM_NAME_TOG, ZOOM_DESC_TOG, toggle_zoom
    )
    hotkey_save_array = obs.obs_data_get_array(settings, ZOOM_NAME_TOG)
    obs.obs_hotkey_load(zoom_id_tog, hotkey_save_array)
    obs.obs_data_array_release(hotkey_save_array)

    global follow_id_tog
    follow_id_tog = obs.obs_hotkey_register_frontend(
        FOLLOW_NAME_TOG, FOLLOW_DESC_TOG, toggle_follow
    )
    hotkey_save_array = obs.obs_data_get_array(settings, FOLLOW_NAME_TOG)
    obs.obs_hotkey_load(follow_id_tog, hotkey_save_array)
    obs.obs_data_array_release(hotkey_save_array)

    if sys == 'Darwin':
        global load_sources_hk
        load_sources_hk = obs.obs_hotkey_register_frontend(
            LOAD_SOURCES_NAME_HK, LOAD_SOURCES_DESC_HK, press_load_sources
        )
        hotkey_save_array = obs.obs_data_get_array(settings, LOAD_SOURCES_NAME_HK)
        obs.obs_hotkey_load(load_sources_hk, hotkey_save_array)
        obs.obs_data_array_release(hotkey_save_array)
        
        global load_monitors_hk
        load_monitors_hk = obs.obs_hotkey_register_frontend(
            LOAD_MONITORS_NAME_HK, LOAD_MONITORS_DESC_HK, press_load_monitors
        )
        hotkey_save_array = obs.obs_data_get_array(settings, LOAD_MONITORS_NAME_HK)
        obs.obs_hotkey_load(load_monitors_hk, hotkey_save_array)
        obs.obs_data_array_release(hotkey_save_array)

    log(f"Loaded settings: {settings_updated}")
    

def script_unload():
    log("Run script_unload")

    obs.obs_hotkey_unregister(toggle_zoom)
    obs.obs_hotkey_unregister(toggle_follow)
    if sys == 'Darwin':
        obs.obs_hotkey_unregister(press_load_sources)
        obs.obs_hotkey_unregister(press_load_monitors)


def script_save(settings):
    log("Run script_save")

    hotkey_save_array = obs.obs_hotkey_save(zoom_id_tog)
    obs.obs_data_set_array(settings, ZOOM_NAME_TOG, hotkey_save_array)
    obs.obs_data_array_release(hotkey_save_array)


# -------------------------------------------------------------------
def toggle_zoom(pressed):
    if pressed:
        if new_source:
            zoom.update_sources()
        if zoom.source_name != "" and not zoom.lock:
            for attr in ['source_w_raw', 'source_h_raw','source_x_raw','source_y_raw']:
                try:
                    getattr(zoom,attr)
                except:
                    log("reinit source params")
                    log(zoom.__dict__)
                    zoom.update_source_size()
                    log(zoom.__dict__)
                    break
            if zoom.source_type not in SOURCES.monitor.all_sources():
                zoom.update_source_size()
            zoom.center_on_cursor()
            zoom.lock = True
            zoom.tick_enable()
            log(f"Mouse position: {get_cursor_position()}")
        elif zoom.lock:
            zoom.lock = False
            zoom.tick_enable()  # For the zoom out transition
        log(f"Zoom: {zoom.lock}")


def toggle_follow(pressed):
    if pressed:
        if zoom.track:
            zoom.track = False
        elif not zoom.track:
            zoom.track = True
            # Tick if zoomed in, to enable follow updates
            if zoom.lock:
                zoom.tick_enable()
        log(f"Tracking: {zoom.track}")


def press_load_sources(pressed):
    if pressed:
        global props
        source_list = obs.obs_properties_get(props, "source")
        populate_list_property_with_source_names(source_list)
    

def press_load_monitors(pressed):
    if pressed:
        global props
        monitor_list = obs.obs_properties_get(props, "monitor")
        populate_list_property_with_monitors(monitor_list)