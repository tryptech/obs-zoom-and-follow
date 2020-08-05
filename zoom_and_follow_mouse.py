import obspython as obs
from mouse import get_position  # python -m pip install mouse
from screeninfo import get_monitors # python -m pip install screeninfo

#Variables

REFRESH_RATE = 16
FLAG = True

ZOOM_W = 1280
ZOOM_H = 720
ACTIVE_BORDER = 0.15
MAX_SPEED = 160
SMOOTH = 1.0
ZOOM_D = 300
ZI_TIMER = 0
ZO_TIMER = 0

hotkey_id_tog = None
HOTKEY_NAME_TOG = 'zoom_follow.toggle'
HOTKEY_DESC_TOG = 'Enable/Disable Mouse Zoom and Follow'

#-------------------------------------------------------------------

class CursorWindow:
    def __init__(self, source_name=None):
        self.source_name = source_name
        self.lock = True
        self.track = True
        self.d_w = get_monitors()[0].width
        self.d_h = get_monitors()[0].height
        self.z_x = 0
        self.z_y = 0
        self.z_w = 0
        self.z_h = 0
        self.z_d = 0

    def setW(self,p):
        self.d_w = p
    
    def setH(self,p):
        self.d_h = p

    def resetZI(self):
        global ZI_TIMER
        ZI_TIMER = 0
    
    def resetZO(self):
        global ZO_TIMER
        ZO_TIMER = 0

    def cubic_in_out(self, p):
        if (p < 0.5):
            return 4 * p * p * p
        else:
            f = ((2 * p) - 2)
            return 0.5 * f * f * f + 1

    def follow(self, mousePos):
        #Updates Zoom window position
        global ZOOM_W
        global ZOOM_H
        global ACTIVE_BORDER
        global SMOOTH
        global MAX_SPEED

        #Find shortest dimension (usually height)
        if (self.d_w > self.d_h):
            borderScale = self.d_h
        else:
            borderScale = self.d_w
        
        #Get active zone edges
        zoom_l = self.z_x + int(ACTIVE_BORDER*borderScale)
        zoom_r = self.z_x + ZOOM_W - int(ACTIVE_BORDER*borderScale)
        zoom_u = self.z_y + int(ACTIVE_BORDER*borderScale)
        zoom_d = self.z_y + ZOOM_H - int(ACTIVE_BORDER*borderScale)

        #Set smoothing values
        smoothFactor = int((SMOOTH*9)/10 + 1)
        
        move = False

        #Set x and y zoom offset
        if (mousePos[0] < zoom_l):
            self.z_x -= (int(round((zoom_l - mousePos[0])/smoothFactor)) if int(round((zoom_l - mousePos[0])/smoothFactor)) < MAX_SPEED else MAX_SPEED)
            move = True
        if (mousePos[0] > zoom_r):
            self.z_x += (int(round((mousePos[0] - zoom_r)/smoothFactor)) if int(round((mousePos[0] - zoom_r)/smoothFactor)) < MAX_SPEED else MAX_SPEED)
            move = True
        if (mousePos[1] < zoom_u):
            self.z_y -= (int(round((zoom_u - mousePos[1])/smoothFactor)) if int(round((zoom_u - mousePos[0])/smoothFactor)) < MAX_SPEED else MAX_SPEED)
            move = True
        if (mousePos[1] > zoom_d):
            self.z_y += (int(round((mousePos[1] - zoom_d)/smoothFactor)) if int(round((mousePos[1] - zoom_d)/smoothFactor)) < MAX_SPEED else MAX_SPEED)
            move = True
        
        self.check_pos()
        return move 
    
    def check_pos(self):
        #Checks if zoom window exceeds window dimensions and clamps it if true
        global ZOOM_W
        global ZOOM_H

        if (self.z_x <= 0):
            self.z_x = 0
        elif (self.z_x > self.d_w - ZOOM_W):
            self.z_x = self.d_w - ZOOM_W
        if (self.z_y <= 0):
            self.z_y = 0
        elif (self.z_y > self.d_h - ZOOM_H):
            self.z_y = self.d_h - ZOOM_H

    def set_crop(self, inOut):
        #Set crop filter dimensions
        global ZOOM_W
        global ZOOM_H
        global ZOOM_D
        global ZI_TIMER
        global ZO_TIMER

        totalFrames = int(ZOOM_D/REFRESH_RATE)

        source = obs.obs_get_source_by_name(self.source_name)
        crop = obs.obs_source_get_filter_by_name(source, "ZoomCrop")
        filter_settings = obs.obs_source_get_settings(crop)

        if inOut == 0:
            ZI_TIMER = 0
            if (ZO_TIMER < totalFrames):
                ZO_TIMER += 1
                time = self.cubic_in_out(ZO_TIMER/totalFrames)
                obs.obs_data_set_int(filter_settings, "left", int(((1-time)*self.z_x)))
                obs.obs_data_set_int(filter_settings, "top", int(((1-time)*self.z_y)))
                obs.obs_data_set_int(filter_settings, "cx", ZOOM_W + int(time*(self.d_w - ZOOM_W)))
                obs.obs_data_set_int(filter_settings, "cy", ZOOM_H + int(time*(self.d_h - ZOOM_H)))
            else:
                obs.obs_data_set_int(filter_settings, "left", 0)
                obs.obs_data_set_int(filter_settings, "top", 0)
                obs.obs_data_set_int(filter_settings, "cx", self.d_w)
                obs.obs_data_set_int(filter_settings, "cy", self.d_h)
        else:
            ZO_TIMER = 0
            if (ZI_TIMER < totalFrames):
                ZI_TIMER += 1
                time = self.cubic_in_out(ZI_TIMER/totalFrames)
                obs.obs_data_set_int(filter_settings, "left", int(time*self.z_x))
                obs.obs_data_set_int(filter_settings, "top", int(time*self.z_y))
                obs.obs_data_set_int(filter_settings, "cx", self.d_w - int(time*(self.d_w - ZOOM_W)))
                obs.obs_data_set_int(filter_settings, "cy", self.d_h - int(time*(self.d_h - ZOOM_H)))
            else:
                obs.obs_data_set_int(filter_settings, "left", self.z_x)
                obs.obs_data_set_int(filter_settings, "top", self.z_y)
                obs.obs_data_set_int(filter_settings, "cx", ZOOM_W)
                obs.obs_data_set_int(filter_settings, "cy", ZOOM_H)

        obs.obs_source_update(crop, filter_settings)

        obs.obs_data_release(filter_settings)
        obs.obs_source_release(source)
        obs.obs_source_release(crop)

        if (inOut == 0) and (ZO_TIMER >= totalFrames):
            obs.remove_current_callback()

    def reset_crop(self):
        #Resets crop filter dimensions and removes timer callback
        self.set_crop(0)    

    def tracking(self):
        if (self.lock):
            self.follow(get_position())
            self.set_crop(1)
        else :
            self.reset_crop()

    def tick(self):
        #Containing function that is run every frame
        self.tracking()

zoom = CursorWindow()

#-------------------------------------------------------------------

def script_description():
    return "Crops and resizes a display capture source to simulate a zoomed in mouse. Intended for use with one monitor or the primary monitor of a multi-monitor setup.\n\n" + "Set activation hotkey in Settings.\n\n" + "Active Border enables lazy tracking; calculated as percent of smallest dimension (Max of 33%)\n\n" + "Place a 'Crop/Pad' filter named 'ZoomCrop' on the chosen display source with relative unchecked\n\n" + "By tryptech (@yo_tryptech)"

def script_defaults(settings):
    global REFRESH_RATE
    global ZOOM_W
    global ZOOM_H
    global ACTIVE_BORDER
    global MAX_SPEED
    global SMOOTH
    global ZOOM_D

    obs.obs_data_set_default_int(settings, "interval", REFRESH_RATE)
    obs.obs_data_set_default_int(settings, "Width", ZOOM_W)
    obs.obs_data_set_default_int(settings, "Height", ZOOM_H)
    obs.obs_data_set_default_double(settings, "Border", ACTIVE_BORDER)
    obs.obs_data_set_default_int(settings, "Speed", MAX_SPEED)
    obs.obs_data_set_default_double(settings,"Smooth", SMOOTH)
    obs.obs_data_set_default_int(settings, "Zoom", int(ZOOM_D))

def script_update(settings):
    global REFRESH_RATE
    global ZOOM_W
    global ZOOM_H
    global ACTIVE_BORDER
    global MAX_SPEED
    global SMOOTH
    global ZOOM_D

    REFRESH_RATE = obs.obs_data_get_int(settings, "interval")
    zoom.source_name = obs.obs_data_get_string(settings, "source")
    ZOOM_W = obs.obs_data_get_int(settings, "Width")
    ZOOM_H = obs.obs_data_get_int(settings, "Height")
    ACTIVE_BORDER =  obs.obs_data_get_double(settings, "Border")
    MAX_SPEED = obs.obs_data_get_int(settings, "Speed")
    SMOOTH = obs.obs_data_get_double(settings, "Smooth")
    ZOOM_D = obs.obs_data_get_double(settings, "Zoom")

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
    obs.obs_properties_add_int(props, "Width", "Zoom Window Width", 320, 3840, 1)
    obs.obs_properties_add_int(props, "Height", "Zoom Window Height", 240, 3840, 1)
    obs.obs_properties_add_float_slider(props, "Border", "Active Border", 0, 0.33, 0.01)
    obs.obs_properties_add_int(props, "Speed", "Max Scroll Speed", 0, 540, 10)
    obs.obs_properties_add_float_slider(props, "Smooth", "Smooth", 0, 10, 0.01)
    obs.obs_properties_add_int_slider(props, "Zoom", "Zoom Duration (ms)", 0, 1000, 1)

    return props

def script_load(settings):
    global hotkey_id_tog
    hotkey_id_tog = obs.obs_hotkey_register_frontend(HOTKEY_NAME_TOG, HOTKEY_DESC_TOG, toggle_zoom_follow)
    hotkey_save_array = obs.obs_data_get_array(settings, HOTKEY_NAME_TOG)
    obs.obs_hotkey_load(hotkey_id_tog, hotkey_save_array)
    obs.obs_data_array_release(hotkey_save_array)

def script_unload():
    obs.obs_hotkey_unregister(toggle_zoom_follow)

def script_save(settings):
    hotkey_save_array = obs.obs_hotkey_save(hotkey_id_tog)
    obs.obs_data_set_array(settings, HOTKEY_NAME_TOG, hotkey_save_array)
    obs.obs_data_array_release(hotkey_save_array)

def toggle_zoom_follow(pressed):
    global FLAG
    if pressed:
        if zoom.source_name != "" and FLAG:
            monitor = get_monitors()[0]
            zoom.setW(monitor.width)
            zoom.setH(monitor.height)
            obs.timer_add(zoom.tick, REFRESH_RATE)
            zoom.lock = True
            FLAG = False
        elif not FLAG:
            FLAG = True
            zoom.lock = False