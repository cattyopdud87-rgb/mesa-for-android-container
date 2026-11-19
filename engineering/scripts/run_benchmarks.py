#!/data/data/com.termux/files/usr/bin/env python3
"""
Comprehensive Mesa GPU Benchmark & Telemetry Harness
Measures: OpenGL (Freedreno) & Vulkan (Turnip) on Snapdragon 732G (Adreno 618)
Telemetry: GPU Freq, GPU Busy %, Battery Voltage, Current, Power Draw, Temperature, Energy (Joules)
"""

import subprocess
import time
import json
import os
import sys
import threading
import statistics

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, "benchmarks", "raw")
os.makedirs(RAW_DIR, exist_ok=True)

def read_sys(path, default="0"):
    try:
        with open(path) as f:
            return f.read().strip()
    except Exception:
        return default

class TelemetryCollector:
    def __init__(self, interval=0.2):
        self.interval = interval
        self.stop_event = threading.Event()
        self.thread = None
        self.samples = []

    def _sample(self):
        volt = float(read_sys("/sys/class/power_supply/battery/voltage_now", 0)) / 1e6
        curr = float(read_sys("/sys/class/power_supply/battery/current_now", 0)) / 1e6
        temp = float(read_sys("/sys/class/power_supply/battery/temp", 0)) / 10.0
        power = volt * curr

        # GPU metrics
        freq_str = read_sys("/sys/class/kgsl/kgsl-3d0/devfreq/cur_freq", "0")
        try:
            freq_mhz = int(freq_str) / 1e6
        except ValueError:
            freq_mhz = 0.0

        busy_str = read_sys("/sys/class/kgsl/kgsl-3d0/gpu_busy_percentage", "0")
        try:
            busy_pct = float(busy_str.replace("%", "").strip())
        except ValueError:
            busy_pct = 0.0

        return {
            "time": time.time(),
            "voltage_v": volt,
            "current_a": curr,
            "power_w": power,
            "battery_temp_c": temp,
            "gpu_freq_mhz": freq_mhz,
            "gpu_busy_pct": busy_pct,
        }

    def _run(self):
        while not self.stop_event.is_set():
            self.samples.append(self._sample())
            time.sleep(self.interval)

    def start(self):
        self.samples = []
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._run)
        self.thread.daemon = True
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=2.0)

    def summarize(self):
        if not self.samples:
            return {}
        powers = [s["power_w"] for s in self.samples]
        volts = [s["voltage_v"] for s in self.samples]
        currs = [s["current_a"] for s in self.samples]
        temps = [s["battery_temp_c"] for s in self.samples]
        freqs = [s["gpu_freq_mhz"] for s in self.samples]
        busys = [s["gpu_busy_pct"] for s in self.samples]

        duration = self.samples[-1]["time"] - self.samples[0]["time"]
        avg_power = statistics.mean(powers) if powers else 0.0
        energy_joules = avg_power * duration

        return {
            "duration_s": round(duration, 2),
            "avg_power_w": round(avg_power, 3),
            "max_power_w": round(max(powers) if powers else 0.0, 3),
            "energy_joules": round(energy_joules, 2),
            "start_temp_c": temps[0] if temps else 0.0,
            "end_temp_c": temps[-1] if temps else 0.0,
            "max_temp_c": max(temps) if temps else 0.0,
            "temp_delta_c": round((temps[-1] - temps[0]) if temps else 0.0, 2),
            "avg_gpu_freq_mhz": round(statistics.mean(freqs), 1) if freqs else 0.0,
            "max_gpu_freq_mhz": max(freqs) if freqs else 0.0,
            "avg_gpu_busy_pct": round(statistics.mean(busys), 1) if busys else 0.0,
        }

def run_command_in_container(cmd):
    full_cmd = [
        "su", "-c",
        f'PATH=$PATH:/data/local/Droidspaces/bin droidspaces --name=mikasa run -- su - Gold -c "{cmd}"'
    ]
    p = subprocess.run(full_cmd, capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr

import re

def parse_glmark2(output):
    scenes = {}
    score = None
    for line in output.splitlines():
        line = line.strip()
        if line.startswith("[") and "FPS:" in line:
            scene_match = re.search(r"\[(\w+)\]", line)
            fps_match = re.search(r"FPS:\s*([0-9.]+)", line)
            ft_match = re.search(r"FrameTime:\s*([0-9.]+)", line)
            if scene_match and fps_match and ft_match:
                scenes[scene_match.group(1)] = {
                    "fps": float(fps_match.group(1)),
                    "frametime_ms": float(ft_match.group(1))
                }
        elif "glmark2 Score:" in line:
            score_match = re.search(r"glmark2 Score:\s*([0-9]+)", line)
            if score_match:
                score = int(score_match.group(1))
    return {"scenes": scenes, "score": score}

def parse_vkmark(output):
    scenes = {}
    score = None
    for line in output.splitlines():
        line = line.strip()
        if line.startswith("[") and "FPS:" in line:
            scene_match = re.search(r"\[(\w+)\]", line)
            fps_match = re.search(r"FPS:\s*([0-9.]+)", line)
            ft_match = re.search(r"FrameTime:\s*([0-9.]+)", line)
            if scene_match and fps_match and ft_match:
                scenes[scene_match.group(1)] = {
                    "fps": float(fps_match.group(1)),
                    "frametime_ms": float(ft_match.group(1))
                }
        elif "vkmark Score:" in line:
            score_match = re.search(r"vkmark Score:\s*([0-9]+)", line)
            if score_match:
                score = int(score_match.group(1))
    return {"scenes": scenes, "score": score}

def benchmark_suite(name, env_vars="", repetitions=3):
    print(f"\n=======================================================")
    print(f" Running Benchmark Suite: {name}")
    print(f" Environment Overrides: {env_vars if env_vars else 'Default'}")
    print(f" Repetitions: {repetitions}")
    print(f"=======================================================")

    results = {
        "suite_name": name,
        "env_vars": env_vars,
        "repetitions": repetitions,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "glmark2_runs": [],
        "vkmark_runs": [],
    }

    # 1. Run glmark2
    gl_cmd = f"WAYLAND_DISPLAY=wayland-1 XDG_RUNTIME_DIR=/run/user/1000 {env_vars} glmark2-wayland --off-screen -b terrain:duration=2.0 -b shading:duration=2.0 -b build:duration=2.0 -b bump:duration=2.0"
    for r in range(repetitions):
        print(f"[*] Running OpenGL (glmark2) Repetition {r+1}/{repetitions}...")
        collector = TelemetryCollector()
        collector.start()
        code, out, err = run_command_in_container(gl_cmd)
        collector.stop()
        parsed = parse_glmark2(out)
        telem = collector.summarize()
        print(f"    -> Score: {parsed.get('score')}, Power: {telem.get('avg_power_w')}W, Max Temp: {telem.get('max_temp_c')}C")
        results["glmark2_runs"].append({
            "repetition": r + 1,
            "parsed": parsed,
            "telemetry": telem,
            "raw_output": out
        })
        time.sleep(1.0) # Thermal settling

    # 2. Run vkmark
    vk_cmd = f"WAYLAND_DISPLAY=wayland-1 XDG_RUNTIME_DIR=/run/user/1000 {env_vars} vkmark --winsys wayland -b vertex:duration=2.0 -b texture:duration=2.0 -b shading:duration=2.0 -b desktop:duration=2.0"
    for r in range(repetitions):
        print(f"[*] Running Vulkan (vkmark) Repetition {r+1}/{repetitions}...")
        collector = TelemetryCollector()
        collector.start()
        code, out, err = run_command_in_container(vk_cmd)
        collector.stop()
        parsed = parse_vkmark(out)
        telem = collector.summarize()
        print(f"    -> Score: {parsed.get('score')}, Power: {telem.get('avg_power_w')}W, Max Temp: {telem.get('max_temp_c')}C")
        results["vkmark_runs"].append({
            "repetition": r + 1,
            "parsed": parsed,
            "telemetry": telem,
            "raw_output": out
        })
        time.sleep(1.0) # Thermal settling

    return results

if __name__ == "__main__":
    suite_id = sys.argv[1] if len(sys.argv) > 1 else "baseline"
    env_args = sys.argv[2] if len(sys.argv) > 2 else ""
    reps = int(sys.argv[3]) if len(sys.argv) > 3 else 3

    res = benchmark_suite(suite_id, env_vars=env_args, repetitions=reps)

    out_file = os.path.join(RAW_DIR, f"{suite_id}.json")
    with open(out_file, "w") as f:
        json.dump(res, f, indent=2)

    print(f"\n[+] Suite completed successfully. Results saved to: {out_file}")
