Zoom and Follow
---------------
Have you ever needed to zoom in on your screen to show some fine detail work, or to make your large 4k/ultrawide monitor less daunting? **Zoom and Follow** for OBS Studio does exactly that, zooms in on your mouse and follows it around. Configurable and low-impact, you can now do old school Camtasia zoom ins ***live***!

*Inspired by [caharkness](https://obsproject.com/forum/members/caharkness.153928/)'s [Magic Window](https://obsproject.com/forum/threads/magic-window.107614/)*


Dependencies
------------
- [mouse](https://github.com/boppreh/mouse) by [BoppreH](https://github.com/boppreh)
- [screeninfo](https://github.com/rr-/screeninfo) by [rr-](https://github.com/rr-)

Install
-------
- Install Python 3 (3.6 for Windows, that's what OBS works with)
- Install mouse *python -m pip install mouse*
- Install screeninfo *python -m pip install screeninfo*
- Add zoom_and_follow_mouse.py as an OBS script

How to Use
----------
- Setup a hotkey for "Enable/Disable Mouse Zoom and Follow
- Select a source to zoom into as part of the script settings
- Configure the settings to your liking
- Add a Crop/Pad filter named "ZoomCrop" to the source with "Relative" unchecked
- You're done!

To Do
-----
- Move hotkey to script settings (?)
- Set up zooms for different sources (?)
