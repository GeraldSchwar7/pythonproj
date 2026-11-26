# Gesture Mouse and Hands-Free Improvements

This is a review list for improving the camera-driven editor beyond the current pinch, drag, click, and cursor-stability changes. Items below are proposals, not additional changes already made.

## Recommended next steps

1. **Tune for the actual camera and user**
   - Add a short calibration flow to learn the user's neutral hand position, comfortable movement range, pinch distance, and preferred cursor speed.
   - Expose sensitivity, smoothing, pinch threshold, and drag threshold in Settings rather than requiring source edits.
   - Keep profiles per user/camera so camera distance and hand size do not require one fixed threshold.

2. **Finish hands-free app operation**
   - Add a gesture-accessible camera picker, camera rescan, and camera retry flow; the current camera dropdown is a mouse-oriented control.
   - Add an on-screen gesture menu with clear active-tool, pinch, drag, and camera status.
   - Add a deliberate pause/resume gesture and an emergency release action that always releases held buttons.
   - Decide whether speech input is wanted for text entry or commands. If added, make it opt-in and process locally where possible.
   - A hands-free workflow still needs a way to launch the program and sign into the operating system; those are outside the current application controls.

3. **Validate pointer and pinch behavior on real hardware**
   - Test in several lighting conditions, at different camera distances, and with left- and right-handed users.
   - Measure cursor jitter while the hand is still, pinch closure drift, time-to-target on fast sweeps, and drift during a drag.
   - Test one click, double-click, drag/drop, pinch release, temporary tracking loss, and camera unplug/reconnect in Windows File Explorer.
   - Verify that two deliberate pinch releases are close enough in time and position for Windows' configured double-click settings.
   - Tune the filter and gesture thresholds from those measurements rather than increasing smoothing blindly, which can create lag.

4. **Expand interaction coverage**
   - Consider scroll, right-click, cancel/escape, and a way to confirm or cancel destructive editor actions.
   - Add hover feedback and a dwell-selection option for users who cannot reliably pinch.
   - Keep drag initiation distinct from a stationary pinch so ordinary selection does not turn into a drag.

5. **Improve system compatibility and safety**
   - Test Windows display scaling, multiple monitors, screen edges, and cursor coordinates at non-default DPI.
   - Make tracking pause when the app is unfocused or the user explicitly pauses it, and show when global cursor control is active.
   - Keep a keyboard/mouse fallback and a visible way to recover if tracking is lost. No gesture system should make normal desktop input inaccessible.

## Current implementation decisions to review

- Pinching outside an asset thumbnail clicks immediately once, when thumb and index first touch.
- A pinch that starts on an asset thumbnail starts a native asset drag; the existing timeline drop handler accepts it only when released on a valid track.
- Select uses the original OK-sign pose and activates after a two-second hold.
- Asset dragging requires sustained palm-center displacement; index-finger curling into the pinch does not start a drag.
- A short tracking dropout is tolerated, while a longer loss cancels the gesture instead of generating an accidental click.
- Cursor smoothing uses a speed-responsive low-pass filter: small motion is damped while fast sweeps receive a higher response.
- All tool-selection gestures use the same two-second activation hold.

## Limits of current verification

Automated tests cover pinch state transitions, immediate click dispatch, asset-source hit testing, timeline drop bounds, dropout handling, relative drag movement, and small synthetic cursor noise. They do not prove camera landmark quality, human comfort, Windows DPI correctness, or physical drag timing. Those need hands-on testing on the target machine.
