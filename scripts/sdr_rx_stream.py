#!/usr/bin/env python3
"""
Threaded SDR RX stream: decouples hardware buffer collection from processing.

The producer thread calls _rx_buffered_data() continuously so it is always
waiting for the next DMA buffer while the main thread processes the current one.

Usage on Pluto:
    python3 /root/sdr_rx_stream.py

To use in your pipeline:
    stream = RxStream(sdr)
    stream.start()
    while True:
        samples = stream.get()   # complex64, normalised — replaces sdr.rx()
        ...
    stream.stop()
"""

import threading
import queue
import time
import numpy as np
import adi

SAMPLE_RATE = 2_400_000
CENTER_FREQ = 2_437_000_000
RX_BUF_SIZE = 32768
RX_GAIN     = 50
SCALE       = np.float32(2.0 / 16384)


class RxStream:
    """
    Wraps an adi.Pluto (or any pyadi-iio rx device) and continuously drains
    hardware buffers in a background thread.

    get() returns the next buffer as complex64 with minimal latency.
    """

    def __init__(self, sdr, maxsize: int = 2):
        """
        Args:
            sdr:     configured adi.Pluto instance
            maxsize: queue depth — 2 means at most one pre-fetched buffer is
                     held in memory waiting for the consumer
        """
        self._sdr = sdr
        self._q: queue.Queue = queue.Queue(maxsize=maxsize)
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._producer, daemon=True)
        self._overruns = 0

    def start(self):
        self._stop.clear()
        self._thread.start()

    def stop(self):
        self._stop.set()
        # Unblock the producer if it's waiting on a full queue
        try:
            self._q.get_nowait()
        except queue.Empty:
            pass
        self._thread.join()

    def get(self, timeout: float = 2.0) -> np.ndarray:
        """Return next buffer as complex64 normalised samples."""
        return self._q.get(timeout=timeout)

    @property
    def overruns(self) -> int:
        """Number of times the producer dropped a buffer because the consumer
        was too slow (queue full)."""
        return self._overruns

    def _producer(self):
        while not self._stop.is_set():
            buf = self._raw_rx()
            try:
                self._q.put_nowait(buf)
            except queue.Full:
                # Consumer too slow — drop oldest, push newest
                try:
                    self._q.get_nowait()
                except queue.Empty:
                    pass
                self._q.put_nowait(buf)
                self._overruns += 1

    def _raw_rx(self) -> np.ndarray:
        """Bypass chan.read() deinterleave — buf.read() gives raw interleaved
        bytes in one shot, saving ~5 ms vs _rx_buffered_data()."""
        if not self._sdr._rxbuf:
            self._sdr._rx_init_channels()
        self._sdr._rxbuf.refill()
        raw = np.frombuffer(self._sdr._rxbuf.read(), dtype=np.int16)
        arr = np.empty((len(raw) // 2, 2), dtype=np.float32)
        arr[:, 0] = raw[0::2]   # I
        arr[:, 1] = raw[1::2]   # Q
        out = arr.view(np.complex64).reshape(-1)
        out *= SCALE
        return out


# ── benchmark ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    sdr = adi.Pluto("ip:192.168.2.1")
    sdr.sample_rate             = SAMPLE_RATE
    sdr.rx_lo                   = CENTER_FREQ
    sdr.rx_buffer_size          = RX_BUF_SIZE
    sdr.gain_control_mode_chan0 = "manual"
    sdr.rx_hardwaregain_chan0   = RX_GAIN
    sdr.rx()  # warm up

    N = 20

    # Simulate detection workload: ~8 ms of numpy ops on the buffer
    def fake_detect(samples):
        # Rough proxy for Schmidl-Cox + matched filter on 32768 complex64 samples
        _ = np.abs(samples) ** 2
        _ = np.convolve(samples[:512].real, np.ones(32, dtype=np.float32), mode="full")

    DETECT_MS = 8.0   # adjust to match your real pipeline if needed

    def simulate_detection(samples):
        t0 = time.perf_counter()
        fake_detect(samples)
        elapsed = (time.perf_counter() - t0) * 1e3
        remaining = DETECT_MS - elapsed
        if remaining > 0:
            time.sleep(remaining / 1e3)

    # Baseline: sequential sdr.rx() + detection
    print(f"=== sequential sdr.rx() + {DETECT_MS:.0f} ms detection ===")
    times, cycle_times = [], []
    t_cycle = time.perf_counter()
    for i in range(N):
        t0 = time.perf_counter()
        samples = sdr.rx()
        rx_ms = (time.perf_counter() - t0) * 1e3
        simulate_detection(samples)
        cycle_ms = (time.perf_counter() - t_cycle) * 1e3
        t_cycle = time.perf_counter()
        times.append(rx_ms)
        cycle_times.append(cycle_ms)
        print(f"  {i:2d}: rx={rx_ms:.1f} ms  cycle={cycle_ms:.1f} ms", flush=True)
    print(f"rx    mean={sum(times)/N:.2f} ms")
    print(f"cycle mean={sum(cycle_times)/N:.2f} ms  (samples captured every ~{sum(cycle_times)/N:.1f} ms)")
    print()

    # Threaded RxStream + detection
    print(f"=== RxStream.get() + {DETECT_MS:.0f} ms detection ===")
    stream = RxStream(sdr)
    stream.start()

    times, cycle_times = [], []
    t_cycle = time.perf_counter()
    for i in range(N):
        t0 = time.perf_counter()
        samples = stream.get()
        wait_ms = (time.perf_counter() - t0) * 1e3
        simulate_detection(samples)
        cycle_ms = (time.perf_counter() - t_cycle) * 1e3
        t_cycle = time.perf_counter()
        times.append(wait_ms)
        cycle_times.append(cycle_ms)
        print(f"  {i:2d}: wait={wait_ms:.1f} ms  cycle={cycle_ms:.1f} ms", flush=True)

    stream.stop()
    print(f"wait  mean={sum(times)/N:.2f} ms")
    print(f"cycle mean={sum(cycle_times)/N:.2f} ms  (samples captured every ~{sum(cycle_times)/N:.1f} ms)")
    print(f"overruns: {stream.overruns}")
    buf_period_ms = RX_BUF_SIZE / SAMPLE_RATE * 1e3
    print(f"hw buffer period: {buf_period_ms:.1f} ms — {'OK, keeping up' if sum(cycle_times)/N <= buf_period_ms * 1.05 else 'DROPPING buffers'}")
