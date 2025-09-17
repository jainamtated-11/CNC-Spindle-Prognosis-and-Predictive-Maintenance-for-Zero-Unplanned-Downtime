import time
import spidev
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime
import RPi.GPIO as GPIO

# GPIO setup for trigger pin
TRIGGER_PIN = 17  # GPIO17 (pin 11)
GPIO.setmode(GPIO.BCM)
GPIO.setup(TRIGGER_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

# SPI setup for MCP3008
spi = spidev.SpiDev()
spi.open(0, 0)
spi.max_speed_hz = 1000000

# Read MCP3008 channel
def read_channel(ch):
    adc = spi.xfer2([1, (8 + ch) << 4, 0])
    result = ((adc[1] & 3) << 8) + adc[2]
    return result

# Sample data for FFT check
def acquire_fft_samples(sample_rate=25600, duration=1.0):
    total_samples = int(sample_rate * duration)
    sample_interval = 1.0 / sample_rate
    data = []
    start_time = time.perf_counter()
    for _ in range(total_samples):
        loop_start = time.perf_counter()
        adc_val = read_channel(0)
        voltage = (adc_val * 3.3) / 1023
        data.append(voltage)
        while (time.perf_counter() - loop_start) < sample_interval:
            pass
    elapsed = time.perf_counter() - start_time
    return data, elapsed

# Perform FFT and detect specific frequency
def frequency_detected(voltage_data, elapsed, target_freqs, tolerance=10.0, threshold=0.05):
    N = len(voltage_data)
    T = elapsed / N
    yf = np.fft.fft(np.hanning(N) * np.array(voltage_data))
    xf = np.fft.fftfreq(N, T)[:N//2]
    amplitudes = 2.0 / N * np.abs(yf[:N//2])

    # Plot FFT
    plt.figure(figsize=(10, 4))
    plt.plot(xf, amplitudes)
    plt.title("FFT - Frequency Spectrum")
    plt.xlabel("Frequency (Hz)")
    plt.ylabel("Amplitude")
    plt.grid(True)
    plt.tight_layout()
    plt.show(block=False)
    plt.pause(0.1)
    plt.close()

    for target_freq in target_freqs:
        for freq, amp in zip(xf, amplitudes):
            if (target_freq - tolerance) <= freq <= (target_freq + tolerance) and amp > threshold:
                return target_freq
    return None

# Log detailed data into specific sheet of a writer
def log_data(writer, sheet_name, duration_sec=2.0, sample_rate=25600):
    print(f"🔴 Logging for {sheet_name} triggered! Waiting 7 seconds...")
    time.sleep(7)
    print(f"📊 Logging data for 2 seconds into sheet: {sheet_name}")

    total_samples = int(sample_rate * duration_sec)
    sample_interval = 1.0 / sample_rate
    adc_data, voltage_data, timestamp_data = [], [], []

    for _ in range(total_samples):
        loop_start = time.perf_counter()
        adc_val = read_channel(0)
        voltage = (adc_val * 3.3) / 1023-1.65
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        adc_data.append(adc_val)
        voltage_data.append(voltage)
        timestamp_data.append(timestamp)
        while (time.perf_counter() - loop_start) < sample_interval:
            pass

    df = pd.DataFrame({
        'Timestamp': timestamp_data,
        'ADC Value': adc_data,
        'Voltage': voltage_data
    })
    df.to_excel(writer, sheet_name=sheet_name, index=False)
    print(f"✅ Data saved to sheet: {sheet_name}")

# Get multiple target frequencies from user
print("📥 Enter target frequencies to monitor:")
while True:
    try:
        freq_count = int(input("How many frequencies to monitor? (min 3, max 6): "))
        if 3 <= freq_count <= 6:
            break
        else:
            print("Please enter a number between 3 and 6.")
    except ValueError:
        print("Invalid input. Please enter an integer.")

target_frequencies = []
for i in range(freq_count):
    while True:
        try:
            freq = float(input(f"Enter frequency {i+1} (Hz): "))
            target_frequencies.append(freq)
            break
        except ValueError:
            print("Invalid input. Please enter a numeric value.")

# Main loop
print("🔎 Waiting for trigger pin to go HIGH (3.3V)...")
try:
    file_session = 1
    while True:
        if GPIO.input(TRIGGER_PIN) == GPIO.HIGH:
            print("✅ Trigger detected. Waiting 30 seconds before monitoring...")
            time.sleep(30)

            filename = f"fft_triggered_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}_session{file_session}.xlsx"
            writer = pd.ExcelWriter(filename, engine='openpyxl')

            print("🎯 Monitoring for frequencies...")
            while GPIO.input(TRIGGER_PIN) == GPIO.HIGH:
                voltages, elapsed = acquire_fft_samples()
                matched_freq = frequency_detected(voltages, elapsed, target_frequencies)
                if matched_freq:
                    sheet_name = f"{int(matched_freq)}Hz"
                    log_data(writer, sheet_name)
                else:
                    print("Target frequencies not detected. Monitoring continues...")
                time.sleep(1)

            writer.close()
            print(f"🔁 Trigger pin went LOW. File saved: {filename}")
            file_session += 1
        time.sleep(0.1)

except KeyboardInterrupt:
    print("⏹ Monitoring stopped by user.")
finally:
    spi.close()
    GPIO.cleanup()
