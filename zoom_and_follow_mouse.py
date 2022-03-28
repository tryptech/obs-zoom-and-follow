import obspython as obs 
import pywinctl as pwc # version >=0.0.30
from math import sqrt
from json import loads

c = pwc.getMousePos
get_position = lambda: [c().x, c().y]
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
    windows = pwc.getAllAppsWindowsTitles()
    window = ''
    monitors = pwc.getAllScreens()
    monitors_key = list(dict.keys(monitors))
    d_w = 0
    d_h = 0
    s_x = 0
    s_y = 0
    s_x_override = 0
    s_y_override = 0
    z_x = 0
    z_y = 0
    refresh_rate = int(obs.obs_get_frame_interval_ns()/1000000)
    source_name = ""
    source_type = ""
    zoom_w = 1280
    zoom_h = 720
    active_border = 0.15
    max_speed = 160
    smooth = 1.0
    zoom_time = 300

    def update_sources(self):
        windows = pwc.getAllAppsWindowsTitles()
        monitors = pwc.getAllScreens()
        monitors_key = list(dict.keys(monitors))

    def update_source_size(self):
        data = obs.obs_data_get_json(obs.obs_source_get_settings(obs.obs_get_source_by_name(self.source_name)))
        if (self.source_type == 'window_capture') or (self.source_type == 'game_capture'):
            data = loads(data)['window'].split(":")
            window = pwc.getWindowsWithTitle(data[0])[0]
            window_dim = window.getClientFrame()
            self.d_w = window_dim.right - window_dim.left
            self.d_h = window_dim.bottom - window_dim.top
            self.s_x = window_dim.left
            self.s_y = window_dim.top
        elif (self.source_type == 'monitor_capture'): 
            data = loads(data)['monitor']
            for i in range(len(self.monitors_key)):
                monitor = self.monitors[self.monitors_key[i]]
                if (monitor['id'] == data):
                    self.d_w = monitor['size'].width
                    self.d_h = monitor['size'].height
                    self.s_x = monitor['pos'].x
                    self.s_y = monitor['pos'].y
        if (self.s_x_override > 0):
            self.s_x += self.s_x_override
        if (self.s_y_override > 0):
            self.s_y += self.s_y_override

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
        
        track = False

        if (mousePos[0] - (self.s_x + self.d_w) < 0) and (mousePos[0] - self.s_x > 0):
            if (mousePos[1] - (self.s_y + self.d_h) < 0) and (mousePos[1] - self.s_y > 0):
                    track = True


        if not track:
            return track

        move = False

        # Find shortest dimension (usually height)
        if self.d_w > self.d_h:
            borderScale = self.d_h
        else:
            borderScale = self.d_w

        # Get active zone edges
        zoom_edge_left = self.z_x + int(self.active_border * borderScale)
        zoom_edge_right = self.z_x + self.zoom_w - int(self.active_border * borderScale)
        zoom_edge_top = self.z_y + int(self.active_border * borderScale)
        zoom_edge_bottom = self.z_y + self.zoom_h - int(self.active_border * borderScale)

        # Clamp zone edges at center
        if zoom_edge_right < zoom_edge_left:
            zoom_edge_left = self.z_x + int(self.zoom_w/2.0)
            zoom_edge_right = zoom_edge_left

        if zoom_edge_bottom < zoom_edge_top:
            zoom_edge_top = self.z_y + int(self.zoom_h/2.0)
            zoom_edge_bottom = zoom_edge_top

        # Set smoothing values
        smoothFactor = int((self.smooth * 9) / 10 + 1)


        # Set x and y zoom offset
        x_o = mousePos[0] - self.s_x
        y_o = mousePos[1] - self.s_y

        # Set x and y zoom offset
        offset_x = 0
        offset_y = 0
        
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

        self.z_x += offset_x
        self.z_y += offset_y
        if (self.active_border < 0.5):
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
        "Crops and resizes a source to simulate a zoomed in tracked to the mouse.\n\n"
        + "Set activation hotkey in Settings.\n\n"
        + "Active Border enables lazy tracking; border size calculated as percent of smallest dimension. "
        + "Border of 50% keeps mouse locked in the center of the zoom frame\n\n"
        + "By tryptech (@yo_tryptech)"
    )


def script_defaults(settings):
    zoom.update_sources()
    obs.obs_data_set_default_int(settings, "Width", zoom.zoom_w)
    obs.obs_data_set_default_int(settings, "Height", zoom.zoom_h)
    obs.obs_data_set_default_double(settings, "Border", zoom.active_border)
    obs.obs_data_set_default_int(settings, "Speed", zoom.max_speed)
    obs.obs_data_set_default_double(settings, "Smooth", zoom.smooth)
    obs.obs_data_set_default_int(settings, "Zoom", int(zoom.zoom_time))
    obs.obs_data_set_default_int(settings, "Manual X Offset", 0)
    obs.obs_data_set_default_int(settings, "Manual Y Offset", 0)


def script_update(settings):
    zoom.source_name = obs.obs_data_get_string(settings, "source")
    zoom.source_type = obs.obs_source_get_id(obs.obs_get_source_by_name(zoom.source_name))
    zoom.zoom_w = obs.obs_data_get_int(settings, "Width")
    zoom.zoom_h = obs.obs_data_get_int(settings, "Height")
    zoom.active_border = obs.obs_data_get_double(settings, "Border")
    zoom.max_speed = obs.obs_data_get_int(settings, "Speed")
    zoom.smooth = obs.obs_data_get_double(settings, "Smooth")
    zoom.zoom_time = obs.obs_data_get_double(settings, "Zoom")
    zoom.s_x_override = obs.obs_data_get_int(settings, "Manual X Offset")
    zoom.s_y_override = obs.obs_data_get_int(settings, "Manual Y Offset")


def script_properties():
    props = obs.obs_properties_create()

    p = obs.obs_properties_add_list(
        props,
        "source",
        "Zoom Source",
        obs.OBS_COMBO_TYPE_EDITABLE,
        obs.OBS_COMBO_FORMAT_STRING,
    )

    sources = obs.obs_enum_sources()
    if sources is not None:
        for source in sources:
            source_type = obs.obs_source_get_id(source)
            if source_type == "monitor_capture" or source_type == "window_capture" or source_type == "game_capture":
                name = obs.obs_source_get_name(source)
                obs.obs_property_list_add_string(p, name, name)
    obs.source_list_release(sources)

    obs.obs_properties_add_int(props, "Manual X Offset", "Manual X Offset", -8000, 8000, 1)
    obs.obs_properties_add_int(props, "Manual Y Offset", "Manual Y Offset", -8000, 8000, 1)

    obs.obs_properties_add_int(props, "Width", "Zoom Window Width", 320, 3840, 1)
    obs.obs_properties_add_int(props, "Height", "Zoom Window Height", 240, 3840, 1)
    obs.obs_properties_add_float_slider(props, "Border", "Active Border", 0, 0.5, 0.01)
    obs.obs_properties_add_int(props, "Speed", "Max Scroll Speed", 0, 540, 10)
    obs.obs_properties_add_float_slider(props, "Smooth", "Smooth", 0, 10, 0.01)
    obs.obs_properties_add_int_slider(props, "Zoom", "Zoom Duration (ms)", 0, 1000, 1)

    return props


def script_load(settings):
    global zoom_id_tog
    zoom.update_sources()
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
