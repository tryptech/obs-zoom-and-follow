Zoom and Follow
---------------
Have you ever needed to zoom in on your screen to show some fine detail work, or to make your large 4k/ultrawide monitor appear less daunting on stream? **Zoom and Follow** for OBS Studio does exactly that, zooms in on your mouse and follows it around. Configurable and low-impact, you can now do old school Camtasia zoom ***live***!

*Maintained for the [current release version of OBS](https://github.com/obsproject/obs-studio/releases/latest)*

*Built using Python 3.10*

*Inspired by [caharkness](https://obsproject.com/forum/members/caharkness.153928/)'s [Magic Window](https://obsproject.com/forum/threads/magic-window.107614/)*

*Last updated: 2023 September 12*

Dependencies
------------
- [PyWinCtl](https://github.com/Kalmat/PyWinCtl/) by [Kalmat](https://github.com/Kalmat)

Install
-------
- Install Python 3

  Make sure that you configure the correct version of Python within OBS in the "Scripts" window > "Python Settings" tab

- Install requirements

  ```python pip install -r requirements.txt```

  or

  ```python3 pip install -r requirements.txt```

- Add `zoom_and_follow_mouse.py` as an OBS script

*Note: I will not provide support on how to install Python or any dependencies as each system and platform is different. I am only set up to test on the current versions of Windows 11 and Apple Silicon-based macOS and can only guarantee compatibility with the latest version of OBS on the latest version of each OS.*

How to Use
----------
1. In the "Tools > Scripts" Menu of OBS
   - Select a source to zoom into as part of the script settings
   - Configure the size of the zoom window
   - Change any of the other settings to adjust the zoom and follow behavior (Optional)
2. In the "Settings > Hotkeys" Menu of OBS
   - Setup a hotkey for ***Enable/Disable Mouse Zoom***
   - Setup a hotkey for ***Enable/Disable Mouse Follow***
3. In the "Edit Transform" menu for the source:
  - Set the "Bounding Box Type" to ***Scale to inner bounds***
  - Set the "Bounding Box Size" to the size you want on the canvas when zoomed out
- Use ***Zoom*** hotkey to zoom in and out of the source
- Optionally, use the ***Follow*** hotkey to toggle mouse tracking

Setting up zoom control for multiple sources
---
Duplicate and rename `zoom_and_follow_mouse.py`, and repeat the **Install** and **How to Use** sections with the duplicate copy.

To Do
-----
- Automatically setup transform bounding box
- Only track windows/games when they are the active window
- Re-implement window tracking on macOS
