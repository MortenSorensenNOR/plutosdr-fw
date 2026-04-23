#!/usr/bin/env python3
"""
Detailed breakdown of rx() latency and comparison of backends.

Usage on Pluto:
    python3 /root/sdr_rx_bench.py
"""

import time
import numpy as np
import adi

SAMPLE_RATE = 2_400_000
CENTER_FREQ = 2_437_000_000
RX_BUF_SIZE = 32768
RX_GAIN     = 50
SCALE       = np.float32(2.0 / 16384)
N           = 10


def bench(label, fn, n=N):
    times = []
    for _ in range(n):
        t0 = time.perf_counter()
        result = fn()
        times.append((time.perf_counter() - t0) * 1e3)
    mean = sum(times) / n
    print(f"{label:40s}  mean={mean:6.2f} ms  min={min(times):6.2f} ms  max={max(times):6.2f} ms")
    return result


def fast_rx(sdr):
    x = sdr._rx_buffered_data()
    raw = np.empty((len(x[0]), 2), dtype=np.float32)
    raw[:, 0] = x[0]
    raw[:, 1] = x[1]
    out = raw.view(np.complex64).reshape(-1)
    out *= SCALE
    return out


def setup(uri):
    sdr = adi.Pluto(uri)
    sdr.sample_rate             = SAMPLE_RATE
    sdr.rx_lo                   = CENTER_FREQ
    sdr.rx_buffer_size          = RX_BUF_SIZE
    sdr.gain_control_mode_chan0 = "manual"
    sdr.rx_hardwaregain_chan0   = RX_GAIN
    sdr.rx()  # warm up
    return sdr


# ── ip: backend ───────────────────────────────────────────────────────────────
print("=== ip: backend ===")
sdr_ip = setup("ip:192.168.2.1")

def raw_rx(sdr) -> np.ndarray:
    """Read raw interleaved buffer directly, bypassing chan.read() deinterleave."""
    sdr._rxbuf.refill()
    raw = np.frombuffer(sdr._rxbuf.read(), dtype=np.int16)  # [I0,Q0,I1,Q1,...]
    arr = np.empty((len(raw) // 2, 2), dtype=np.float32)
    arr[:, 0] = raw[0::2]   # I
    arr[:, 1] = raw[1::2]   # Q
    out = arr.view(np.complex64).reshape(-1)
    out *= SCALE
    return out


bench("sdr.rx()              [ip:192]",  lambda: sdr_ip.rx())
bench("_rx_buffered_data()   [ip:192]",  lambda: sdr_ip._rx_buffered_data())
bench("fast_rx()             [ip:192]",  lambda: fast_rx(sdr_ip))
bench("raw_rx() buf.read()   [ip:192]",  lambda: raw_rx(sdr_ip))

# ── localhost ─────────────────────────────────────────────────────────────────
print()
print("=== ip:localhost ===")
try:
    sdr_lo = setup("ip:localhost")
    bench("sdr.rx()              [localhost]", lambda: sdr_lo.rx())
    bench("_rx_buffered_data()   [localhost]", lambda: sdr_lo._rx_buffered_data())
    bench("fast_rx()             [localhost]", lambda: fast_rx(sdr_lo))
    bench("raw_rx() buf.read()   [localhost]", lambda: raw_rx(sdr_lo))
except Exception as e:
    print(f"localhost unavailable: {e}")

# ── local: backend ────────────────────────────────────────────────────────────
print()
print("=== local: backend ===")
try:
    sdr_local = setup("local:")
    bench("sdr.rx()              [local]", lambda: sdr_local.rx())
    bench("_rx_buffered_data()   [local]", lambda: sdr_local._rx_buffered_data())
    bench("fast_rx()             [local]", lambda: fast_rx(sdr_local))
    bench("raw_rx() buf.read()   [local]", lambda: raw_rx(sdr_local))
except Exception as e:
    print(f"local: unavailable: {e}")
