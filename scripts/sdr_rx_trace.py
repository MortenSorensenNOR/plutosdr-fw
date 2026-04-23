#!/usr/bin/env python3
"""
SDR RX timing probe — run this under strace to see where sdr.rx spends its time.

Usage on Pluto:
    strace -T -tt -o /tmp/sdr_rx_trace.log python3 /root/sdr_rx_trace.py
    # -T  : show time spent in each syscall
    # -tt : absolute timestamps (microsecond resolution)
    # -o  : write to file so strace overhead doesn't block the terminal

Then copy the log off and inspect:
    grep -E "^[0-9]" /tmp/sdr_rx_trace.log | sort -t= -k2 -rn | head -40
    # sorts by time-in-syscall to show the slow ones first
"""

import time
import adi

# ------------------------------------------------------------------
# Configuration — match your actual pipeline settings
# ------------------------------------------------------------------
SAMPLE_RATE   = 2_400_000   # 2.4 MSPS
RX_BUF_SIZE   = 1024 * 32  # samples per rx() call
CENTER_FREQ   = 2_437_000_000  # 2.437 GHz (Wi-Fi ch 6, adjust as needed)
RX_GAIN       = 50          # dB, manual mode

# ------------------------------------------------------------------
# Initialise the SDR  (this is a one-time cost, not what we're timing)
# ------------------------------------------------------------------
print("Initialising SDR...", flush=True)
sdr = adi.Pluto("ip:192.168.2.1")
sdr.sample_rate          = SAMPLE_RATE
sdr.rx_lo                = CENTER_FREQ
sdr.rx_buffer_size       = RX_BUF_SIZE
sdr.gain_control_mode_chan0 = "manual"
sdr.rx_hardwaregain_chan0   = RX_GAIN
print("SDR ready.", flush=True)

# ------------------------------------------------------------------
# Warm-up call (first call often triggers extra setup)
# ------------------------------------------------------------------
_ = sdr.rx()

# ------------------------------------------------------------------
# Timed calls — this is the section strace will show in detail
# ------------------------------------------------------------------
N = 10
times = []
for i in range(N):
    t0 = time.perf_counter()
    samples = sdr.rx()
    t1 = time.perf_counter()
    ms = (t1 - t0) * 1e3
    times.append(ms)
    print(f"rx() call {i:2d}: {ms:6.2f} ms  ({len(samples)} samples)", flush=True)

print()
print(f"mean : {sum(times)/len(times):.2f} ms")
print(f"min  : {min(times):.2f} ms")
print(f"max  : {max(times):.2f} ms")
