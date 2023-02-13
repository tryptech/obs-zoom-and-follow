Zoom and Follow
---------------
Have you ever needed to zoom in on your screen to show some fine detail work, or to make your large 4k/ultrawide monitor appear less daunting on stream? **Zoom and Follow** for OBS Studio does exactly that, zooms in on your mouse and follows it around. Configurable and low-impact, you can now do old school Camtasia zoom ***live***!

*Maintained for the [current release version of OBS](https://github.com/obsproject/obs-studio/releases/latest)*

*Inspired by [caharkness](https://obsproject.com/forum/members/caharkness.153928/)'s [Magic Window](https://obsproject.com/forum/threads/magic-window.107614/)*


Dependencies
------------
- [PyWinCtl](https://github.com/Kalmat/PyWinCtl/) by [Kalmat](https://github.com/Kalmat)

Install
-------
- Install Python 3 (3.6.x for OBS version <28 for Windows and Mac OS, any Python 3 for OBS version 28+)

  Make sure that you configure the correct version of Python within OBS in the "Scripts" window > "Python Settings" tab

- Install [PyWinCtl](https://github.com/Kalmat/PyWinCtl#install)

  Be sure to install to the Python version that OBS is using.

- Add `zoom_and_follow_mouse.py` as an OBS script

How to Use
----------
- Setup a hotkey for ***Enable/Disable Mouse Zoom***
- Setup a hotkey for ***Enable/Disable Mouse Follow***
- Select a source to zoom into as part of the script settings
- Configure the size of the zoom window
- Edit the bounding box settings for the source in it's "Edit Transform" menu, usually to ***Stretch to inner bounds*** and your canvas size
- Use ***Zoom*** hotkey to zoom in to the source

Set up zoom control for multiple sources
---
Duplicate (and optionally rename) `zoom_and_follow_mouse.py`, add it as an OBS script, and follow the **How to Use** section with the duplicate copy.

To Do
-----
- Automatically setup transform bounding box
- Only track windows/games when they are the active window
- Refactor Mac support
