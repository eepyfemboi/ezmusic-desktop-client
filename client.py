import os
import threading
import time
import traceback
import winreg
from ctypes import POINTER, cast

try: import GPUtil
except ImportError: os.system('pip install GPUtil'); import GPUtil
try: import psutil
except ImportError: os.system('pip install psutil'); import psutil
try: import requests
except ImportError: os.system('pip install requests'); import requests
try: import webview
except ImportError: os.system('pip install pywebview'); import webview
try: from comtypes import CLSCTX_ALL
except ImportError: os.system('pip install comtypes'); from comtypes import CLSCTX_ALL
try: from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
except ImportError: os.system('pip install pycaw'); from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
try: from pypresence import Presence
except ImportError: os.system('pip install pypresence'); from pypresence import Presence
try: from pythonosc import udp_client
except ImportError: os.system('pip install python-osc'); from pythonosc import udp_client

website_url = 'https://ezmusic.net/'
client = udp_client.SimpleUDPClient("127.0.0.1", 9000)

def format_bytes(bytes_size):
    gb_size = bytes_size / (1024 ** 3)
    return "{:.2f}".format(gb_size)

def get_volume():
    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(
        IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    volume = cast(interface, POINTER(IAudioEndpointVolume))
    return int(volume.GetMasterVolumeLevelScalar() * 100)

def get_stats_message():
    ram = psutil.virtual_memory()
    try:
        gpu = GPUtil.getGPUs()[0]
        gpuname = gpu.name
        gpu = str(float(gpu.load * 100)).split(".")[0]
    except Exception as e:
        gpuname = "GPU"
        gpu = None
    parts = str(psutil.cpu_percent(interval=1, percpu=False)).split(".")
    if len(parts[1]) > 2: cpu = parts[0] + "." + parts[1][2:]
    elif len(parts[1]) == 1: cpu = parts[0] + ".0" + parts[1]
    net_start = psutil.net_io_counters()
    time.sleep(1)
    net_end = psutil.net_io_counters()

    start = net_start.bytes_sent + net_start.bytes_recv
    end = net_end.bytes_sent + net_end.bytes_recv

    speed = ((end - start) * 8) / 1e6
    speed = "{:.2f}".format(speed)
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0") as key:
            cpub, _ = winreg.QueryValueEx(key, "ProcessorNameString")
    except Exception as e:
        cpub = None
    message = f"""
{cpub}: {cpu}%
{gpuname}: {gpu}%
RAM Usage: {format_bytes(ram.used)}/{format_bytes(ram.total)} GB
Network Usage: {speed} Mbps
"""
    return message

def read_metadata(path: str):
    try:
        response = requests.get(f"https://ezmusic.net/page/musicmp3/meta/{path}.mdf").text
        content = response.split("|LYRIC_DATA|")
        #print(content[0])
        print(response)
        #with open(f"musicmp3/meta/{path}.mdf", "r", encoding="utf-8") as file:
        #    content = file.read().split("\n|LYRIC_DATA|\n")
        #content = response.split("\n|LYRIC_DATA|\n")
        data_fields=content[0].strip().split('|:|:|')
        return {
            'title': data_fields[0],
            'artist': data_fields[1],
            'album': data_fields[2],
            'artwork': data_fields[3]
        }
    except Exception as e:
        traceback.print_exception(e)
        return {
            'title': path,
            'artist': 'Unknown Artist',
            'album': 'Unknown Album',
            'artwork': 'https://cocfire.xyz/page/assets/icons/music.png'
        }

def cookie_setter(window: webview.Window):
    time.sleep(2)
    js = """
function getCookie(name) {
    var match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
    return match ? match[2] : null;
}
getCookie('access_token');
"""
    try:
        with open(".cookie", "r") as f:
            cookie = f.read().strip()
        if len(cookie) > 5:
            window.evaluate_js(f"document.cookie = \"access_token={cookie}; path=/\";")
    except:
        pass
    while True:
        try:
            cookie = window.evaluate_js(js)
            if len(cookie) > 5:
                with open(".cookie", "w") as f:
                    f.write(cookie)
        except:
            pass
        time.sleep(5)

path_data = {}

def get_metadata(path: str):
    if path not in path_data:
        path_data[path] = read_metadata(path)
    return path_data[path]

def updater_loop(window: webview.Window):
    rpc = Presence(1198870224104079390)
    rpc.connect()
    while True:
        try:
            js_script = """
function getAudioInfo() {
    var audioPlayer = document.getElementById('audioPlayer');
    var currentPosition = audioPlayer.currentTime;
    var totalDuration = audioPlayer.duration;
    return {
        currentPosition: currentPosition,
        totalDuration: totalDuration
    };
}
getAudioInfo();
"""
            shit = window.evaluate_js(js_script)
            if shit is not None:
                shit = dict(shit)
            else:
                shit = {
                    'currentPosition': 0.00,
                    'totalDuration': 0.00
                }
            loop_js_script = """
function getLooping() {
    var audioPlayer = document.getElementById('audioPlayer');
    return audioPlayer.loop;
}
getLooping();
"""
            paused_js_script = """
function getPaused() {
    var audioPlayer = document.getElementById('audioPlayer');
    return audioPlayer.paused;
}
getPaused();
"""
            looping = window.evaluate_js(loop_js_script)
            paused = window.evaluate_js(paused_js_script)
            looping = bool(looping)
            if looping:
                loop_icon = "🔁 "
            else:
                loop_icon = ""
            paused = bool(paused)
            if paused:
                paused_icon = "⏸️ "
            else:
                paused_icon = "▶️ "
            current_time = int(shit.get('currentPosition'))
            total_time = int(shit.get('totalDuration'))
            e = total_time / 60
            if e >= 1.0:
                total_time_minutes = int(total_time / 60)
            else:
                total_time_minutes = 0
            total_seconds = total_time_minutes * 60
            total_time_seconds = total_time - total_seconds
            if len(str(total_time_seconds)) < 2:
                total_time_seconds = "0" + str(total_time_seconds)
            e = current_time / 60
            if e >= 1.0:
                current_time_minutes = int(current_time / 60)
            else:
                current_time_minutes = 0
            current_seconds = current_time_minutes * 60
            current_time_seconds = current_time - current_seconds
            if len(str(current_time_seconds)) < 2:
                current_time_seconds = "0" + str(current_time_seconds)
            volume = get_volume()
            if volume > 66:
                emoji = "🔊"
            elif volume > 33:
                emoji = "🔉"
            elif volume > 9:
                emoji = "🔈"
            else:
                emoji = "🔇"
            thing = f"{paused_icon}{loop_icon} {emoji}: {volume}% [{current_time_minutes}:{current_time_seconds}/{total_time_minutes}:{total_time_seconds}]"
            url = window.get_current_url()
            try:
                part = url.split("fp=")[1]
                part = part.split("&")[0]
                data = get_metadata(part)
                title = data.get('title')
                artist = data.get('artist')
                artwork = data.get('artwork')
                rpc.update(
                    state=thing,
                    details=f"{artist} - {title}",
                    large_image=artwork,
                    buttons=[
                        {
                            "label": "Listen (Free)",
                            "url": url
                        }
                    ]
                )
            except:
                try:
                    rpc.update(
                        state="[0:00/0:00]",
                        details="Nothing is playing",
                        large_image="https://cocfire.xyz/page/assets/icons/music.png",
                        buttons=[
                            {
                                "label": "Free Music",
                                "url": 'https://cocfire.xyz/musicplayer'
                            }
                        ]
                    )
                except:
                    rpc.connect()
            time.sleep(0.2)
        except Exception as e:
            pass

def updater_loop1(window: webview.Window):
    while True:
        try:
            js_script = """
function getAudioInfo() {
    var audioPlayer = document.getElementById('audioPlayer');
    var currentPosition = audioPlayer.currentTime;
    var totalDuration = audioPlayer.duration;
    return {
        currentPosition: currentPosition,
        totalDuration: totalDuration
    };
}
getAudioInfo();
"""
            shit = window.evaluate_js(js_script)
            if shit is not None:
                shit = dict(shit)
            else:
                shit = {
                    'currentPosition': 0.00,
                    'totalDuration': 0.00
                }
            loop_js_script = """
function getLooping() {
    var audioPlayer = document.getElementById('audioPlayer');
    return audioPlayer.loop;
}
getLooping();
"""
            paused_js_script = """
function getPaused() {
    var audioPlayer = document.getElementById('audioPlayer');
    return audioPlayer.paused;
}
getPaused();
"""
            looping = window.evaluate_js(loop_js_script)
            paused = window.evaluate_js(paused_js_script)
            looping = bool(looping)
            if looping:
                loop_icon = "🔁 "
            else:
                loop_icon = ""
            paused = bool(paused)
            if paused:
                paused_icon = "⏸️ "
            else:
                paused_icon = "▶️ "
            current_time = int(shit.get('currentPosition'))
            total_time = int(shit.get('totalDuration'))
            offset = int(total_time - current_time)
            e = total_time / 60
            if e >= 1.0:
                total_time_minutes = int(total_time / 60)
            else:
                total_time_minutes = 0
            total_seconds = total_time_minutes * 60
            total_time_seconds = total_time - total_seconds
            if len(str(total_time_seconds)) < 2:
                total_time_seconds = "0" + str(total_time_seconds)
            e = current_time / 60
            if e >= 1.0:
                current_time_minutes = int(current_time / 60)
            else:
                current_time_minutes = 0
            current_seconds = current_time_minutes * 60
            current_time_seconds = current_time - current_seconds
            if len(str(current_time_seconds)) < 2:
                current_time_seconds = "0" + str(current_time_seconds)
            volume = get_volume()
            if volume > 66:
                emoji = "🔊"
            elif volume > 33:
                emoji = "🔉"
            elif volume > 9:
                emoji = "🔈"
            else:
                emoji = "🔇"
            thing = f"{paused_icon}{loop_icon}{emoji}: {volume}% [{current_time_minutes}:{current_time_seconds}/{total_time_minutes}:{total_time_seconds}]"
            url = window.get_current_url()
            try:
                part = url.split("fp=")[1]
                part = part.split("&")[0]
                data = get_metadata(part)
                title = data.get('title')
                artist = data.get('artist')
                message = f"""
Free Music & No Ads
https://ezmusic.net/

{artist} - {title}
{thing}
"""
                client.send_message("/chatbox/input", [message.strip().replace("\n", " "), True, False])
                time.sleep(3)
            except:
                message = f"""
Free Music & No Ads
https://ezmusic.net/

Nothing is playing
"""
                client.send_message("/chatbox/input",[message.strip().replace("\n", " "),True,False])
                time.sleep(3)
            message = get_stats_message()
            client.send_message("/chatbox/input",[message.strip().replace("\n", " "),True,False])
            time.sleep(4)
        except Exception as e:
            pass

e = webview.create_window(title='EZMusic.net', url = 'https://ezmusic.net/')
threading.Thread(target=lambda:updater_loop(e)).start()
threading.Thread(target=lambda:updater_loop1(e)).start()
threading.Thread(target=lambda:cookie_setter(e)).start()
webview.start()
