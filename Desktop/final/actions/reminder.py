# actions/reminder.py

import subprocess
import os
import sys
import tempfile
from datetime import datetime


def _notify_linux(title: str, message: str) -> None:
    """Show notification on Linux using various backends."""
    try:
        subprocess.run(["notify-send", title, message], timeout=5)
    except FileNotFoundError:
        try:
            subprocess.run(["zenity", "--notification", f"--text={message}"], timeout=5)
        except FileNotFoundError:
            print(f"[Reminder] Alert: {title} - {message}")


def _notify_macos(title: str, message: str) -> None:
    """Show notification on macOS."""
    script = f'display notification "{message}" with title "{title}"'
    subprocess.run(["osascript", "-e", script], capture_output=True, timeout=5)


def _notify_windows(title: str, message: str) -> None:
    """Show notification on Windows."""
    try:
        from win10toast import ToastNotifier
        ToastNotifier().show_toast(title, message, duration=15, threaded=False)
    except ImportError:
        try:
            subprocess.run(["msg", "*", "/TIME:30", message], shell=True, timeout=5)
        except Exception:
            print(f"[Reminder] Alert: {title} - {message}")


def reminder(
    parameters: dict,
    response: str | None = None,
    player=None,
    session_memory=None
) -> str:
    """
    Sets a timed reminder using system-appropriate scheduling.
    Windows: Task Scheduler
    Linux: at command or cron
    macOS: launchd

    parameters:
        - date    (str) YYYY-MM-DD
        - time    (str) HH:MM
        - message (str)

    Returns a result string.
    """

    date_str = parameters.get("date")
    time_str = parameters.get("time")
    message  = parameters.get("message", "Reminder")

    if not date_str or not time_str:
        return "I need both a date and a time to set a reminder."

    try:
        target_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")

        if target_dt <= datetime.now():
            return "That time is already in the past."

        safe_message = message.replace('"', '').replace("'", "").strip()[:200]
        platform_name = sys.platform

        if platform_name == "win32":
            return _set_reminder_windows(target_dt, safe_message, player)
        elif platform_name == "darwin":
            return _set_reminder_macos(target_dt, safe_message, player)
        else:
            return _set_reminder_linux(target_dt, safe_message, player)

    except ValueError:
        return "Invalid date or time format. Use YYYY-MM-DD and HH:MM."
    except Exception as e:
        return f"Error setting reminder: {e}"


def _set_reminder_windows(target_dt: datetime, message: str, player=None) -> str:
    """Schedule reminder using Windows Task Scheduler."""
    try:
        task_name = f"MARKReminder_{target_dt.strftime('%Y%m%d_%H%M')}"
        python_exe = sys.executable
        
        if python_exe.lower().endswith("python.exe"):
            pythonw = python_exe.replace("python.exe", "pythonw.exe")
            if os.path.exists(pythonw):
                python_exe = pythonw

        temp_dir = os.environ.get("TEMP", "C:\\Temp")
        notify_script = os.path.join(temp_dir, f"{task_name}.pyw")

        script_code = f'''import sys, os, time
try:
    from win10toast import ToastNotifier
    ToastNotifier().show_toast("MARK Reminder", "{message}", duration=15, threaded=False)
except:
    try:
        import subprocess
        subprocess.run(["msg", "*", "/TIME:30", "{message}"], shell=True)
    except:
        print("Reminder: {message}")

time.sleep(3)
try:
    os.remove(__file__)
except:
    pass
'''
        with open(notify_script, "w", encoding="utf-8") as f:
            f.write(script_code)

        xml_content = f'''<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>MARK Reminder: {message}</Description>
  </RegistrationInfo>
  <Triggers>
    <TimeTrigger>
      <StartBoundary>{target_dt.strftime("%Y-%m-%dT%H:%M:%S")}</StartBoundary>
      <Enabled>true</Enabled>
    </TimeTrigger>
  </Triggers>
  <Actions>
    <Exec>
      <Command>{python_exe}</Command>
      <Arguments>"{notify_script}"</Arguments>
    </Exec>
  </Actions>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <StartWhenAvailable>true</StartWhenAvailable>
  </Settings>
  <Principals>
    <Principal>
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
</Task>'''

        xml_path = os.path.join(temp_dir, f"{task_name}.xml")
        with open(xml_path, "w", encoding="utf-16") as f:
            f.write(xml_content)

        result = subprocess.run(
            f'schtasks /Create /TN "{task_name}" /XML "{xml_path}" /F',
            shell=True, capture_output=True, text=True
        )

        try:
            os.remove(xml_path)
        except:
            pass

        if result.returncode == 0:
            if player:
                player.write_log(f"[reminder] set for {target_dt.strftime('%Y-%m-%d %H:%M')}")
            return f"Reminder set for {target_dt.strftime('%B %d at %I:%M %p')}."
        else:
            try:
                os.remove(notify_script)
            except:
                pass
            return "Could not schedule reminder."

    except Exception as e:
        return f"Error scheduling reminder: {e}"


def _set_reminder_linux(target_dt: datetime, message: str, player=None) -> str:
    """Schedule reminder using Linux 'at' command or as fallback."""
    try:
        # Use 'at' command if available
        time_str = target_dt.strftime("%H:%M %Y-%m-%d")
        
        # Create notification script
        notify_cmd = f"notify-send 'MARK Reminder' '{message}' || zenity --notification --text='{message}' || echo '{message}'"
        
        try:
            # Try using 'at' command
            proc = subprocess.Popen(
                ["at", time_str],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = proc.communicate(input=notify_cmd)
            
            if proc.returncode == 0:
                if player:
                    player.write_log(f"[reminder] scheduled for {target_dt.strftime('%Y-%m-%d %H:%M')}")
                return f"Reminder set for {target_dt.strftime('%B %d at %I:%M %p')}."
            else:
                return f"Could not schedule reminder: {stderr}"
                
        except FileNotFoundError:
            # Fallback: use crontab
            minute = target_dt.minute
            hour = target_dt.hour
            day = target_dt.day
            month = target_dt.month
            
            cron_schedule = f"{minute} {hour} {day} {month} * {notify_cmd}"
            
            # This is a fallback message - full crontab integration would be complex
            return f"Reminder would be set for {target_dt.strftime('%B %d at %I:%M %p')}. (Use crontab manually if 'at' is not available)"

    except Exception as e:
        return f"Error scheduling reminder: {e}"


def _set_reminder_macos(target_dt: datetime, message: str, player=None) -> str:
    """Schedule reminder using macOS launchd plist."""
    try:
        reminder_name = f"com.mark.reminder.{target_dt.strftime('%Y%m%d_%H%M')}"
        plist_dir = os.path.expanduser("~/Library/LaunchAgents")
        os.makedirs(plist_dir, exist_ok=True)
        
        plist_path = os.path.join(plist_dir, f"{reminder_name}.plist")
        
        # Create notification script
        notify_script = f'''
tell application "System Events"
    display notification "{message}" with title "MARK Reminder"
end tell
'''
        
        plist_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{reminder_name}</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/osascript</string>
        <string>-e</string>
        <string>{notify_script}</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Minute</key>
        <integer>{target_dt.minute}</integer>
        <key>Hour</key>
        <integer>{target_dt.hour}</integer>
        <key>Day</key>
        <integer>{target_dt.day}</integer>
        <key>Month</key>
        <integer>{target_dt.month}</integer>
    </dict>
</dict>
</plist>'''
        
        with open(plist_path, "w") as f:
            f.write(plist_content)
        
        subprocess.run(["launchctl", "load", plist_path], capture_output=True)
        
        if player:
            player.write_log(f"[reminder] set for {target_dt.strftime('%Y-%m-%d %H:%M')}")
        
        return f"Reminder set for {target_dt.strftime('%B %d at %I:%M %p')}."
        
    except Exception as e:
        return f"Error scheduling reminder: {e}"

    except ValueError:
        return "I couldn't understand that date or time format."

    except Exception as e:
        return f"Something went wrong while scheduling the reminder: {str(e)[:80]}"