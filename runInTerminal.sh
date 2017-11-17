#!/bin/sh

osascript - "$@" > /dev/null <<SCRIPT
on run argv
  set originalTID to AppleScript's text item delimiters
  set AppleScript's text item delimiters to space

  tell application "Terminal"
    activate
    set newTab to do script(argv as text)
  end tell
  set AppleScript's text item delimiters to originalTID
end run
SCRIPT
