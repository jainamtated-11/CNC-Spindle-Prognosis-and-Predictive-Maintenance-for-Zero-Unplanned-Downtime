import spidev
import time
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
 
# SPI setup
spi = spidev.SpiDev()
spi.open(0, 0)
spi.max_speed_hz = 1350000  # Max safe for MCP3008
 
# Read from MCP3008 channel
def read_channel(ch):
    adc = spi.xfer2([1, (8 + ch) << 4, 0])
    return ((adc[1] & 3) << 8) + adc[2]
 
# User input
try:
    duration = float(input("Enter logging duration in seconds: "))
except ValueError:
    duration = 5
 
sample_rate = 25600
interval = 1.0 / sample_rate
num_samples = int(sample_rate * duration)
 
adc_data = []
voltage_data = []
 
print(f"\nStarting high-speed data logging for {duration} seconds...")
print(f"Target rate: {sample_rate} samples/sec")
 
start_time = time.perf_counter()
 
for i in range(num_samples):
    loop_start = time.perf_counter()
 
    adc_val = read_channel(0)
    voltage = (adc_val * 3.3) /4095
 
    adc_data.append(adc_val)
    voltage_data.append(voltage)
 
    # Enforce sample  
    while (time.perf_counter() - loop_start) < interval:
        pass
 
elapsed = time.perf_counter() - start_time
actual_rate = len(adc_data) / elapsed
 
print(f"\n✅ Done logging {len(adc_data)} samples")
print(f"Actual time: {elapsed:.3f} s")
print(f"Actual sample rate: {actual_rate:.2f} Hz")
 
# Save to CSV
df = pd.DataFrame({
    'ADC Value': adc_data,
    'Voltage': voltage_data
})
filename = f"iepe_data_fast_{int(time.time())}.csv"
df.to_csv(filename, index=False)
print(f"Data saved to {filename}")
 
# Plot signal
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
ax1.plot(voltage_data)
ax1.set_title("Voltage Signal (Time Domain)")
ax1.set_xlabel("Sample Number")
ax1.set_ylabel("Voltage (V)")
ax1.grid(True)
 
# FFT
N = len(voltage_data)
T = elapsed / N  # actual sample interval
window = np.hanning(N)
signal = np.array(voltage_data) * window
yf = np.fft.fft(signal)
xf = np.fft.fftfreq(N, T)[:N//2]
amplitude = 2.0 / N * np.abs(yf[:N//2])
 
ax2.plot(xf, amplitude)
ax2.set_title("FFT - Frequency Spectrum")
ax2.set_xlabel("Frequency (Hz)")
ax2.set_ylabel("Amplitude")
ax2.grid(True)
 
plt.tight_layout()
plt.show()
spi.close()
 

