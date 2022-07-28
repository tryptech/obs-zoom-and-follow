import obspython as obs 
import pywinctl as pwc # version >=0.0.38
from math import sqrt
from json import loads

c = pwc.getMousePos
get_position = lambda: [c().x, c().y]
zoom_id_tog = None
follow_id_tog = None
new_source = False
ZOOM_NAME_TOG = "zoom.toggle"
FOLLOW_NAME_TOG = "follow.toggle"
ZOOM_DESC_TOG = "Enable/Disable Mouse Zoom"
FOLLOW_DESC_TOG = "Enable/Disable Mouse Follow"
USE_MANUAL_MONITOR_SIZE = "Manual Monitor Size"


# -------------------------------------------------------------------

class CursorWindow:
    flag = lock = track = True
    zi_timer = zo_timer = 0
    windows = window_titles = monitor = window = window_handle = window_name = ''
    monitors = pwc.getAllScreens()
    monitors_key = list(dict.keys(monitors))
    source_w = source_h = source_x = source_y = zoom_x = zoom_y = source_x_override = source_y_override = 0
    refresh_rate = int(obs.obs_get_frame_interval_ns()/1000000)
    source_name = source_type = ""
    zoom_w = 1280
    zoom_h = 720
    active_border = 0.15
    max_speed = 160
    smooth = 1.0
    zoom_time = 300

    def update_sources(self):
        """
        Update the list of Windows and Monitors from PyWinCtl
        """
        self.windows = pwc.getAllWindows()
        self.monitors = pwc.getAllScreens()
        self.monitors_key = list(dict.keys(self.monitors))

    def update_window_dim(self, window):
        """
        Update the stored window dimensions to those of the selected window

        :param window: Window with new dimensions
        """
        print("Updating stored dimensions to match window's current dimensions")
        print("OLD")
        print("Width, Height, X, Y")
        print(f"{self.source_w}, {self.source_h}, {self.source_x}, {self.source_y}")
        if window != None:
            # FIXME: on macos get window bounds results in an error and does not work
            # NSInternalInconsistencyException - NSWindow drag regions should only be invalidated on the Main Thread!
            window_dim = window.getClientFrame()
            self.source_w = window_dim.right - window_dim.left
            self.source_h = window_dim.bottom - window_dim.top
            self.source_x = window_dim.left
            self.source_y = window_dim.top
        print("NEW")
        print("Width, Height, X, Y")
        print(f"{self.source_w}, {self.source_h}, {self.source_x}, {self.source_y}")

    def update_monitor_dim(self, monitor):
        """
        Update the stored dimensions based on the selected monitor

        :param monitor: Single monitor as returned from the PyWinCtl Monitor function getAllScreens()
        """
        self.source_w = monitor[1]['size'].width
        self.source_h = monitor[1]['size'].height
        self.source_x = monitor[1]['pos'].x
        self.source_y = monitor[1]['pos'].y

    def update_source_size(self):
        """
        Adjusts the source size variables based on the source given
        """
        global new_source

        try:
            # Try to pull the data for the source object
            # OBS stores the monitor index/window target in the window/game/display sources settings
            # Info is stored in a JSON format

            data = loads(obs.obs_data_get_json(obs.obs_source_get_settings(obs.obs_get_source_by_name(self.source_name))))
        except:
            # If it cannot be pulled, it is most likely one of the following: 
            #   The source no longer exists
            #   The source's name has changed
            #   OBS does not have the sources loaded yet when launching the script on start

            print("Source '" + self.source_name + "' not found.")
            if len(self.window_name) == 0:
                # OBS does not have the sources loaded yet when launching the script on start
                self.source_name = ''
            print(obs.obs_get_source_by_name(self.source_name))
        else:
            # If the source data is pulled, it exists. Therefore other information must also exists
            # Source Type is pulled to determine if the source is a display, game, or window

            self.source_type = obs.obs_source_get_id(obs.obs_get_source_by_name(self.source_name))
            print("Source Type: " + self.source_type)
            #self.window = None
            if (self.source_type in { 'window_capture', 'game_capture' }):
                window_match = ''
                if 'window_name' in data:
                    # Window capture for macOS
                    # macos has a 'window_name' property that windows does not have
                    # pywinctl does not report application windows correctly for macos yet, so we must capture based on
                    # the actual window name and not based on the application like we do for windows.
                    
                    self.window_name = data.get('window_name')
                elif 'window' in data:
                    # TODO: More Linux testing, specifically with handles
                    # Windows capture for Windows and Linux
                    # In Windows, application data is stored as "Title:WindowClass:Executable"
                    try:
                        # Assuming the OBS data is formatted correctly, we should be able to identify the window
                        # If New Source/Init
                        # If Handle Exists
                        # Else
                        if new_source:
                            # If new source selected / OBS initialize
                            # Build window, window_handle, and window_name
                            print("New Source")
                            print("Retrieving target window info from OBS")
                            self.window_name = data['window'].split(":")[0]
                            print(f"Searching for: {self.window_name}")
                            for w in self.windows:
                                if w.title == self.window_name:
                                    window_match = w
                                    self.window_handle = w.getHandle()
                            new_source = False
                            print(f"Window Match: {window_match.title}")
                            print(f"Window Match Handle: {str(self.window_handle)}")
                        if self.window_handle != '':
                            # If window handle is already stored
                            # Get window based on handle
                            # Check if name needs changing
                            print(f"Handle exists: {str(self.window_handle)}")
                            handle_match = False
                            for w in self.windows:
                                if w.getHandle() == self.window_handle:
                                    handle_match = True
                                    print(f"Found Handle Match: {str(w.getHandle())}")
                                    window_match = w
                                    print(self.window)
                                    if window_match.title != self.window:
                                        print("Changing target title")
                                        print(f"Old Title: {self.window_name}")                                    
                                        self.window_name = w.title
                                        print(f"New Title: {self.window_name}")
                            if handle_match == False:
                                # TODO: If the handle no longer exists, eg. Window or App closed
                                raise
                        else:
                            print("I don't know how it gets here.")
                            window_match = None
                            # TODO: 
                    except:
                        print(f"Source {self.source_name} has changed. Select new source window")
                        window_match = None
                if window_match is not None:
                    print("Proceeding to resize")
                    self.window = pwc.getWindowsWithTitle(self.window_name)[0]
                    self.update_window_dim(self.window)
            elif (self.source_type == 'monitor_capture'):
                monitor_id = data.get('monitor', None)
                if monitor_id == None:
                    print(f"Key 'monitor' does not exist in {data}")
                else:
                    for monitor in self.monitors.items():
                        if (monitor[1]['id'] == monitor_id):
                            self.update_monitor_dim(monitor)
            elif (self.source_type == 'display_capture'):
                # the 'display' property is an index value and not the true monitor id. 
                # it is only returned when there is more than one monitor on your system.
                # we will assume that the order of the monitors returned from pywinctl 
                # are in the same order that OBS is assigning the display index value.
                monitor_index = data.get('display', 0)
                if (monitor_index < len(self.monitors)):
                    self.update_monitor_dim(self.monitors[self.monitors_key[monitor_index]])
            if (self.source_x_override > 0):
                self.source_x += self.source_x_override
            if (self.source_y_override > 0):
                self.source_y += self.source_y_override

    def resetZI(self):
        """
        Reset the zoom-in timer
        """
        self.zi_timer = 0

    def resetZO(self):
        """
        Reset the zoom-out timer
        """
        self.zo_timer = 0

    def cubic_in_out(self, p):
        """
        Cubic in/out easing function. Accelerates until halfway, then decelerates.

        :param p: Linear temporal percent progress through easing from 0 to 1
        :return: Adjusted percent progress
        """
        if p < 0.5:
            return 4 * p * p * p
        else:
            f = (2 * p) - 2
            return 0.5 * f * f * f + 1

    def check_offset(self, arg1, arg2, smooth):
        """
        Checks if a given value is offset from pivot value and provides an adjustment towards the pivot based on a smoothing factor

        :param arg1: Pivot value
        :param arg2: Checked value
        :param smooth: Smoothing factor; larger values adjusts more smoothly 
        :return: Adjustment value
        """
        result = round((arg1 - arg2) / smooth + 1)
        return int(result)

    def follow(self, mousePos):
        """
        Updates the position of the zoom window.

        :param mousePos: [x,y] position of the mouse on the canvas of all connected displays
        :return: If the zoom window was moved
        """
        track = False

        if (mousePos[0] - (self.source_x + self.source_w) < 0) and (mousePos[0] - self.source_x > 0):
            if (mousePos[1] - (self.source_y + self.source_h) < 0) and (mousePos[1] - self.source_y > 0):
                    track = True

        if not track:
            return track

        move = False

        # Find shortest dimension (usually height)
        if self.zoom_w > self.zoom_h:
            borderScale = self.zoom_h
        else:
            borderScale = self.zoom_w
        # Get active zone edges
        zoom_edge_left = self.zoom_x + int(self.active_border * borderScale)
        zoom_edge_right = self.zoom_x + self.zoom_w - int(self.active_border * borderScale)
        zoom_edge_top = self.zoom_y + int(self.active_border * borderScale)
        zoom_edge_bottom = self.zoom_y + self.zoom_h - int(self.active_border * borderScale)

        # Clamp zone edges at center
        if zoom_edge_right < zoom_edge_left:
            zoom_edge_left = self.zoom_x + int(self.zoom_w/2.0)
            zoom_edge_right = zoom_edge_left

        if zoom_edge_bottom < zoom_edge_top:
            zoom_edge_top = self.zoom_y + int(self.zoom_h/2.0)
            zoom_edge_bottom = zoom_edge_top

        # Set smoothing values
        smoothFactor = int((self.smooth * 9) / 10 + 1)

        # Set x and y zoom offset
        x_o = mousePos[0] - self.source_x
        y_o = mousePos[1] - self.source_y

        # Set x and y zoom offset
        offset_x = offset_y = 0
        

        if x_o < zoom_edge_left:
            offset_x = self.check_offset(x_o, zoom_edge_left, smoothFactor)
            move = True
        elif x_o > zoom_edge_right:
            offset_x = self.check_offset(x_o, zoom_edge_right, smoothFactor)
            move = True

        if y_o < zoom_edge_top:
            offset_y = self.check_offset(y_o, zoom_edge_top, smoothFactor)
            move = True
        elif y_o > zoom_edge_bottom:
            offset_y = self.check_offset(y_o, zoom_edge_bottom, smoothFactor)
            move = True

        # Max speed clamp
        speed_h = sqrt((offset_x**2)+(offset_y**2))
        if (speed_h > self.max_speed):
            speed_factor = speed_h/float(self.max_speed)
            offset_x *= speed_factor
            offset_y *= speed_factor

        self.zoom_x += offset_x
        self.zoom_y += offset_y
        if (self.active_border < 0.5):
            self.check_pos()

        return move

    def check_pos(self):
        """
        Checks if zoom window exceeds window dimensions and clamps it if true
        """
        if self.zoom_x < 0:
            self.zoom_x = 0
        elif self.zoom_x > self.source_w - self.zoom_w:
            self.zoom_x = self.source_w - self.zoom_w
        if self.zoom_y < 0:
            self.zoom_y = 0
        elif self.zoom_y > self.source_h - self.zoom_h:
            self.zoom_y = self.source_h - self.zoom_h

    def set_crop(self, inOut):
        """
        Set dimensions of the crop filter used for zooming

        :param inOut: direction of the filter zoom, in or out
        """
        totalFrames = int(self.zoom_time / self.refresh_rate)

        source = obs.obs_get_source_by_name(self.source_name)
        crop = obs.obs_source_get_filter_by_name(source, "ZoomCrop")

        if crop is None:  # create filter
            _s = obs.obs_data_create()
            obs.obs_data_set_bool(_s, "relative", False)
            f = obs.obs_source_create_private("crop_filter", "ZoomCrop", _s)
            obs.obs_source_filter_add(source, f)
            obs.obs_source_release(f)
            obs.obs_data_release(_s)

        s = obs.obs_source_get_settings(crop)
        i = obs.obs_data_set_int

        if inOut == 0:
            self.zi_timer = 0
            if self.zo_timer < totalFrames:
                self.zo_timer += 1
                time = self.cubic_in_out(self.zo_timer / totalFrames)
                i(s, "left", int(((1 - time) * self.zoom_x)))
                i(s, "top", int(((1 - time) * self.zoom_y)))
                i(
                    s, "cx", self.zoom_w + int(time * (self.source_w - self.zoom_w)),
                )
                i(
                    s, "cy", self.zoom_h + int(time * (self.source_h - self.zoom_h)),
                )
            else:
                i(s, "left", 0)
                i(s, "top", 0)
                i(s, "cx", self.source_w)
                i(s, "cy", self.source_h)
        else:
            self.zo_timer = 0
            if self.zi_timer < totalFrames:
                self.zi_timer += 1
                time = self.cubic_in_out(self.zi_timer / totalFrames)
                i(s, "left", int(time * self.zoom_x))
                i(s, "top", int(time * self.zoom_y))
                i(
                    s, "cx", self.source_w - int(time * (self.source_w - self.zoom_w)),
                )
                i(
                    s, "cy", self.source_h - int(time * (self.source_h - self.zoom_h)),
                )
            else:
                i(s, "left", int(self.zoom_x))
                i(s, "top", int(self.zoom_y))
                i(s, "cx", int(self.zoom_w))
                i(s, "cy", int(self.zoom_h))

        obs.obs_source_update(crop, s)

        obs.obs_data_release(s)
        obs.obs_source_release(source)
        obs.obs_source_release(crop)

        if (inOut == 0) and (self.zo_timer >= totalFrames):
            obs.remove_current_callback()

    def reset_crop(self):
        """
        Resets crop filter dimensions and removes timer callback
        """
        self.set_crop(0)

    def tracking(self):
        """
        Tracking state function
        """
        if self.lock:
            if self.track:
                self.follow(get_position())
            self.set_crop(1)
        else:
            self.reset_crop()

    def tick(self):
        """
        Containing function that is run every frame
        """
        self.tracking()


zoom = CursorWindow()


# -------------------------------------------------------------------


def script_description():
    return (
        "Crops and resizes a source to simulate a zoomed in tracked to the mouse.\n\n"
        + "Set activation hotkey in Settings.\n\n"
        + "Active Border enables lazy tracking; border size calculated as percent of smallest dimension. "
        + "Border of 50% keeps mouse locked in the center of the zoom frame\n\n"
        + "By tryptech (@yo_tryptech)"
    )


def script_defaults(settings):
    obs.obs_data_set_default_string(settings, "source", "")
    obs.obs_data_set_default_int(settings, "Width", 1280)
    obs.obs_data_set_default_int(settings, "Height", 720)
    obs.obs_data_set_default_double(settings, "Border", 0.15)
    obs.obs_data_set_default_int(settings, "Speed", 160)
    obs.obs_data_set_default_double(settings, "Smooth", 1.0)
    obs.obs_data_set_default_int(settings, "Zoom", 300)
    obs.obs_data_set_default_int(settings, "Manual X Offset", 0)
    obs.obs_data_set_default_int(settings, "Manual Y Offset", 0)


def script_update(settings):
    global new_source

    if zoom.source_name != obs.obs_data_get_string(settings, "source"):
        zoom.source_name = obs.obs_data_get_string(settings, "source")
        new_source = True
    if new_source:
        print("Source update")
        zoom.update_sources()
        sources = obs.obs_enum_sources()
        if len(sources) == 0:
            print("No sources, likely OBS startup.")
    else:
        zoom.update_source_size()
        print("Non-initial update")
    print("Source Name: " + zoom.source_name)
    zoom.zoom_w = obs.obs_data_get_int(settings, "Width")
    zoom.zoom_h = obs.obs_data_get_int(settings, "Height")
    zoom.active_border = obs.obs_data_get_double(settings, "Border")
    zoom.max_speed = obs.obs_data_get_int(settings, "Speed")
    zoom.smooth = obs.obs_data_get_double(settings, "Smooth")
    zoom.zoom_time = obs.obs_data_get_double(settings, "Zoom")
    zoom.source_x_override = obs.obs_data_get_int(settings, "Manual X Offset")
    zoom.source_y_override = obs.obs_data_get_int(settings, "Manual Y Offset")


def populate_list_property_with_source_names(list_property):
    global new_source

    zoom.update_sources()
    sources = obs.obs_enum_sources()
    if sources is not None:
        obs.obs_property_list_clear(list_property)
        obs.obs_property_list_add_string(list_property, "", "")
        for source in sources:
            source_type = obs.obs_source_get_id(source)
            if source_type in { "monitor_capture", "window_capture", "game_capture", "display_capture" }:
                name = obs.obs_source_get_name(source)
                obs.obs_property_list_add_string(list_property, name, name)
    obs.source_list_release(sources)
    new_source = True
    print(f"New source: {str(new_source)}")


def script_properties():
    props = obs.obs_properties_create()

    p = obs.obs_properties_add_list(
        props,
        "source",
        "Zoom Source",
        obs.OBS_COMBO_TYPE_LIST,
        obs.OBS_COMBO_FORMAT_STRING,
    )
    populate_list_property_with_source_names(p)

    obs.obs_properties_add_button(props, "Refresh", "Refresh list of sources",
    lambda props,prop: True if populate_list_property_with_source_names(p) else True)

    obs.obs_properties_add_int(props, "Manual X Offset", "Manual X Offset", -8000, 8000, 1)
    obs.obs_properties_add_int(props, "Manual Y Offset", "Manual Y Offset", -8000, 8000, 1)

    obs.obs_properties_add_int(props, "Width", "Zoom Window Width", 320, 3840, 1)
    obs.obs_properties_add_int(props, "Height", "Zoom Window Height", 240, 3840, 1)
    obs.obs_properties_add_float_slider(props, "Border", "Active Border", 0, 0.5, 0.01)
    obs.obs_properties_add_int(props, "Speed", "Max Scroll Speed", 0, 540, 10)
    obs.obs_properties_add_float_slider(props, "Smooth", "Smooth", 0, 10, 1.00)
    obs.obs_properties_add_int_slider(props, "Zoom", "Zoom Duration (ms)", 0, 1000, 1)

    return props


def script_load(settings):
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
    zoom.update_sources()


def script_unload():
    obs.obs_hotkey_unregister(toggle_zoom)
    obs.obs_hotkey_unregister(toggle_follow)


def script_save(settings):
    hotkey_save_array = obs.obs_hotkey_save(zoom_id_tog)
    obs.obs_data_set_array(settings, ZOOM_NAME_TOG, hotkey_save_array)
    obs.obs_data_array_release(hotkey_save_array)

    hotkey_save_array = obs.obs_hotkey_save(follow_id_tog)
    obs.obs_data_set_array(settings, FOLLOW_NAME_TOG, hotkey_save_array)
    obs.obs_data_array_release(hotkey_save_array)


def toggle_zoom(pressed):
    if pressed:
        if new_source:
            zoom.update_sources()
        if zoom.source_name != "" and zoom.flag:
            zoom.update_source_size()
            obs.timer_add(zoom.tick, zoom.refresh_rate)
            zoom.lock = True
            zoom.flag = False
        elif not zoom.flag:
            zoom.flag = True
            zoom.lock = False


def toggle_follow(pressed):
    if pressed:
        if zoom.track:
            zoom.track = False
        elif not zoom.track:
            zoom.track = True
