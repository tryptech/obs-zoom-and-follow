Zoom and Follow
---------------


*Currently refactoring under the **PyWinCtl** branch to consolidate dependencies, simplify use, and remove extraneous settings*

Have you ever needed to zoom in on your screen to show some fine detail work, or to make your large 4k/ultrawide monitor less daunting? **Zoom and Follow** for OBS Studio does exactly that, zooms in on your mouse and follows it around. Configurable and low-impact, you can now do old school Camtasia zoom ***live***!

*Inspired by [caharkness](https://obsproject.com/forum/members/caharkness.153928/)'s [Magic Window](https://obsproject.com/forum/threads/magic-window.107614/)*


Dependencies
------------
- [PyWinCtl](https://github.com/Kalmat/PyWinCtl/) by [Kalmat](https://github.com/Kalmat)

Install
-------
- Install Python 3 (3.6.8 for Windows, that's what OBS works with)
- [Install PyWinCtl](https://github.com/Kalmat/PyWinCtl#install) (Make sure it is the latest version)
- Add `zoom_and_follow_mouse.py` as an OBS script
- Add the Python folder in the "Scripts Windows" > "Python Settings" tab

How to Use
----------
- Setup a hotkey for "Enable/Disable Mouse Zoom"
- Setup a hotkey for "Enable/Disable Mouse Follow"
- Select a source to zoom into as part of the script settings
- Configure the size of the zoom window
- Edit the bounding box settings for the source in it's "Edit Transform" menu
- Use Zoom hotkey to zoom in to the source

If there are any issues after changing any scenes/sources, reload the script

Set up zooms for different sources
---
Duplicate (and optionally rename) `zoom_and_follow_mouse.py`, add it as an OBS script, and follow the **How to Use** section with the duplicate copy.

To Do
-----
- Automatically setup transform bounding box
- Only track windows/games when they are the active window