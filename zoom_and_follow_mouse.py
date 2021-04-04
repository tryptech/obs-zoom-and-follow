import obspython as obs
from pynput.mouse import Controller  # python -m pip install pynput
from screeninfo import get_monitors  # python -m pip install screeninfo


c = Controller()
get_position = lambda: c.position
zoom_id_tog = None
follow_id_tog = None
ZOOM_NAME_TOG = "zoom.toggle"
FOLLOW_NAME_TOG = "follow.toggle"
ZOOM_DESC_TOG = "Enable/Disable Mouse Zoom"
FOLLOW_DESC_TOG = "Enable/Disable Mouse Follow"
USE_MANUAL_MONITOR_SIZE = "Manual Monitor Size"

# -------------------------------------------------------------------


class CursorWindow:
    flag = True
    zi_timer = 0
    zo_timer = 0
    lock = True
    track = True
    monitor_idx = 0
    d_w = get_monitors()[monitor_idx].width
    d_h = get_monitors()[monitor_idx].height
    d_w_override = get_monitors()[monitor_idx].width
    d_h_override = get_monitors()[monitor_idx].height
    z_x = 0
    z_y = 0
    refresh_rate = 16
    source_name = ""
    zoom_w = 1280
    zoom_h = 720
    active_border = 0.15
    max_speed = 160
    smooth = 1.0
    zoom_d = 300

    def update_monitor_size(self):
        monitors = get_monitors()
        if self.monitor_idx < len(monitors):
            monitor = get_monitors()[self.monitor_idx]
            self.d_w = monitor.width
            self.d_h = monitor.height
        else:
            self.d_w = self.d_w_override
            self.d_h = self.d_h_override

    def switch_to_monitor(self, monitor_name):
        for i, monitor in enumerate(get_monitors()):
            if monitor_name == monitor.name:
                self.monitor_idx = i
                return
        self.monitor_idx = len(get_monitors()) + 1000

    def resetZI(self):
        self.zi_timer = 0

    def resetZO(self):
        self.zo_timer = 0

    def cubic_in_out(self, p):
        if p < 0.5:
            return 4 * p * p * p
        else:
            f = (2 * p) - 2
            return 0.5 * f * f * f + 1

    def check_offset(self, arg1, arg2, smooth):
        result = round((arg1 - arg2) / smooth)
        return int(result)

    def follow(self, mousePos):
        # Updates Zoom window position

        # Find shortest dimension (usually height)
        if self.d_w > self.d_h:
            borderScale = self.d_h
        else:
            borderScale = self.d_w

        # Get active zone edges
        zoom_l = self.z_x + int(self.active_border * borderScale)
        zoom_r = self.z_x + self.zoom_w - int(self.active_border * borderScale)
        zoom_u = self.z_y + int(self.active_border * borderScale)
        zoom_d = self.z_y + self.zoom_h - int(self.active_border * borderScale)

        # Set smoothing values
        smoothFactor = int((self.smooth * 9) / 10 + 1)

        move = False

        # Get mouse location
        x_o = mousePos[0]
        y_o = mousePos[1]

        # Set x and y zoom offset
        offset_x = 0
        offset_y = 0

        if x_o < zoom_l:
            offset_x = self.check_offset(x_o, zoom_l, smoothFactor)
            move = True
        elif x_o > zoom_r:
            offset_x = self.check_offset(x_o, zoom_r, smoothFactor)
            move = True

        if y_o < zoom_u:
            offset_y = self.check_offset(y_o, zoom_u, smoothFactor)
            move = True
        elif y_o > zoom_d:
            offset_y = self.check_offset(y_o, zoom_d, smoothFactor)
            move = True

        # Max speed clamp
        if abs(offset_x) > self.max_speed:
            offset_x = int(offset_x * self.max_speed / abs(offset_x))
        if abs(offset_y) > self.max_speed:
            offset_y = int(offset_y * self.max_speed / abs(offset_y))

        self.z_x += offset_x
        self.z_y += offset_y
        self.check_pos()

        return move

    def check_pos(self):
        # Checks if zoom window exceeds window dimensions and clamps it if true
        if self.z_x < 0:
            self.z_x = 0
        elif self.z_x > self.d_w - self.zoom_w:
            self.z_x = self.d_w - self.zoom_w
        if self.z_y < 0:
            self.z_y = 0
        elif self.z_y > self.d_h - self.zoom_h:
            self.z_y = self.d_h - self.zoom_h

    def set_crop(self, inOut):
        # Set crop filter dimensions
        totalFrames = int(self.zoom_d / self.refresh_rate)

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
                i(s, "left", int(((1 - time) * self.z_x)))
                i(s, "top", int(((1 - time) * self.z_y)))
                i(
                    s, "cx", self.zoom_w + int(time * (self.d_w - self.zoom_w)),
                )
                i(
                    s, "cy", self.zoom_h + int(time * (self.d_h - self.zoom_h)),
                )
            else:
                i(s, "left", 0)
                i(s, "top", 0)
                i(s, "cx", self.d_w)
                i(s, "cy", self.d_h)
        else:
            self.zo_timer = 0
            if self.zi_timer < totalFrames:
                self.zi_timer += 1
                time = self.cubic_in_out(self.zi_timer / totalFrames)
                i(s, "left", int(time * self.z_x))
                i(s, "top", int(time * self.z_y))
                i(
                    s, "cx", self.d_w - int(time * (self.d_w - self.zoom_w)),
                )
                i(
                    s, "cy", self.d_h - int(time * (self.d_h - self.zoom_h)),
                )
            else:
                i(s, "left", self.z_x)
                i(s, "top", self.z_y)
                i(s, "cx", self.zoom_w)
                i(s, "cy", self.zoom_h)

        obs.obs_source_update(crop, s)

        obs.obs_data_release(s)
        obs.obs_source_release(source)
        obs.obs_source_release(crop)

        if (inOut == 0) and (self.zo_timer >= totalFrames):
            obs.remove_current_callback()

    def reset_crop(self):
        # Resets crop filter dimensions and removes timer callback
        self.set_crop(0)

    def tracking(self):
        if self.lock:
            if self.track:
                self.follow(get_position())
            self.set_crop(1)
        else:
            self.reset_crop()

    def tick(self):
        # Containing function that is run every frame
        self.tracking()


zoom = CursorWindow()

# -------------------------------------------------------------------


def script_description():
    return (
        "Crops and resizes a display capture source to simulate a zoomed in mouse. Intended for use with one monitor or the primary monitor of a multi-monitor setup.\n\n"
        + "Set activation hotkey in Settings.\n\n"
        + "Active Border enables lazy tracking; calculated as percent of smallest dimension (Max of 33%)\n\n"
        + "By tryptech (@yo_tryptech)"
    )


def script_defaults(settings):
    obs.obs_data_set_default_int(settings, "interval", zoom.refresh_rate)
    obs.obs_data_set_default_int(settings, "Width", zoom.zoom_w)
    obs.obs_data_set_default_int(settings, "Height", zoom.zoom_h)
    obs.obs_data_set_default_double(settings, "Border", zoom.active_border)
    obs.obs_data_set_default_int(settings, "Speed", zoom.max_speed)
    obs.obs_data_set_default_double(settings, "Smooth", zoom.smooth)
    obs.obs_data_set_default_int(settings, "Zoom", int(zoom.zoom_d))
    obs.obs_data_set_default_string(settings, "Monitor", get_monitors()[0].name)
    obs.obs_data_set_default_int(settings, "Manual Monitor Width", get_monitors()[0].width)
    obs.obs_data_set_default_int(settings, "Manual Monitor Height", get_monitors()[0].height)


def script_update(settings):
    zoom.refresh_rate = obs.obs_data_get_int(settings, "interval")
    zoom.source_name = obs.obs_data_get_string(settings, "source")
    zoom.zoom_w = obs.obs_data_get_int(settings, "Width")
    zoom.zoom_h = obs.obs_data_get_int(settings, "Height")
    zoom.active_border = obs.obs_data_get_double(settings, "Border")
    zoom.max_speed = obs.obs_data_get_int(settings, "Speed")
    zoom.smooth = obs.obs_data_get_double(settings, "Smooth")
    zoom.zoom_d = obs.obs_data_get_double(settings, "Zoom")
    zoom.switch_to_monitor(obs.obs_data_get_string(settings, "Monitor"))
    zoom.d_w_override = obs.obs_data_get_int(settings, "Manual Monitor Width")
    zoom.d_h_override = obs.obs_data_get_int(settings, "Manual Monitor Height")


def script_properties():
    props = obs.obs_properties_create()

    obs.obs_properties_add_int(props, "interval", "Update Interval (ms)", 16, 300, 1)
    p = obs.obs_properties_add_list(
        props,
        "source",
        "Select display source",
        obs.OBS_COMBO_TYPE_EDITABLE,
        obs.OBS_COMBO_FORMAT_STRING,
    )
    sources = obs.obs_enum_sources()
    if sources is not None:
        for source in sources:
            name = obs.obs_source_get_name(source)
            obs.obs_property_list_add_string(p, name, name)
        obs.source_list_release(sources)

    monitors_prop_list = obs.obs_properties_add_list(
        props,
        "Monitor",
        "Select monitor to use base for zooming",
        obs.OBS_COMBO_TYPE_EDITABLE,
        obs.OBS_COMBO_FORMAT_STRING,
    )
    for monitor in get_monitors():
        obs.obs_property_list_add_string(monitors_prop_list, monitor.name, monitor.name)
    obs.obs_property_list_add_string(monitors_prop_list, USE_MANUAL_MONITOR_SIZE, USE_MANUAL_MONITOR_SIZE)
    obs.obs_properties_add_int(props, "Manual Monitor Width", "Manual Monitor Width", 320, 3840, 1)
    obs.obs_properties_add_int(props, "Manual Monitor Height", "Manual Monitor Height", 240, 3840, 1)

    obs.obs_properties_add_int(props, "Width", "Zoom Window Width", 320, 3840, 1)
    obs.obs_properties_add_int(props, "Height", "Zoom Window Height", 240, 3840, 1)
    obs.obs_properties_add_float_slider(props, "Border", "Active Border", 0, 0.33, 0.01)
    obs.obs_properties_add_int(props, "Speed", "Max Scroll Speed", 0, 540, 10)
    obs.obs_properties_add_float_slider(props, "Smooth", "Smooth", 0, 10, 0.01)
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
        if zoom.source_name != "" and zoom.flag:
            zoom.update_monitor_size()
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
