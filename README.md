Zoom and Follow
---------------
Have you ever needed to zoom in on your screen to show some fine detail work, or to make your large 4k/ultrawide monitor less daunting? **Zoom and Follow** for OBS Studio does exactly that, zooms in on your mouse and follows it around. Configurable and low-impact, you can now do old school Camtasia zoom ***live***!

*Inspired by [caharkness](https://obsproject.com/forum/members/caharkness.153928/)'s [Magic Window](https://obsproject.com/forum/threads/magic-window.107614/)*


Dependencies
------------
- [pynput](https://github.com/moses-palmer/pynput) by [moses-palmer](https://github.com/moses-palmer)
- [screeninfo](https://github.com/rr-/screeninfo) by [rr-](https://github.com/rr-)

Install
-------
- Install Python 3 (3.6 for Windows, that's what OBS works with)
- Install pynput *python -m pip install pynput*
- Install screeninfo *python -m pip install screeninfo*
- Add `zoom_and_follow_mouse.py` as an OBS script

How to Use
----------
- Setup a hotkey for "Enable/Disable Mouse Zoom"
- Setup a hotkey for "Enable/Disable Mouse Follow"
- Select a source to zoom into as part of the script settings
- Configure the settings to your liking
- You're done!

Set up zooms for different sources
---
- Copy paste `zoom_and_follow_mouse.py` file , add it as an OBS script, and repeat **How to Use**.

To Do
-----
- Move hotkey to script settings (?)
