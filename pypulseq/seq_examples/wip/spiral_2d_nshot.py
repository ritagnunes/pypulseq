"""
This is starter code to demonstrate a working example of a 2D Spiral (N-shots) as a pure Python implementation.
"""
from math import pi

import numpy as np

from pypulseq.Sequence.sequence import Sequence
from pypulseq.calc_duration import calc_duration
from pypulseq.make_adc import make_adc
from pypulseq.make_delay import make_delay
from pypulseq.make_sinc_pulse import make_sinc_pulse
from pypulseq.make_trap_pulse import make_trapezoid
from pypulseq.make_arbitrary_grad import make_arbitrary_grad
from pypulseq.opts import Opts
from pypulseq.utils.vds_2d import vds_2d

system = Opts(max_grad=32, grad_unit='mT/m', max_slew=130, slew_unit='T/m/s', grad_raster_time=10e-6)
seq = Sequence(system)

fov = 256e-3
Nx = 128
Ny = 256
slice_thickness = 5e-3
dx = fov / Nx
TR = 25e-3
TE = 5e-3

n_shots = 16
alpha = 9

[ktraj, G, lamda] = vds_2d(fov, Nx, n_shots, alpha, system)
ktraj = ktraj * 1e-3
ktrajs = np.zeros((np.size(ktraj, 0), np.size(ktraj, 1), 2))
ktrajs[:, :, 0] = np.real(ktraj)
ktrajs[:, :, 1] = np.imag(ktraj)

flip = 15 * pi / 180
kwargs_for_sinc = {"flip_angle": flip, "system": system, "duration": 1.5e-3, "slice_thickness": slice_thickness,
                   "apodization": 0.5, "time_bw_product": 4}
rf, gz, _ = make_sinc_pulse(flip_angle=flip, system=system, duration=1.5e-3, slice_thickness=slice_thickness,
                         apodization=0.5, time_bw_product=4)

adc = make_adc(num_samples=max(G.shape), dwell=system.grad_raster_time)

n_slices = 3
deltaz = n_slices * slice_thickness
z = np.linspace(-(deltaz / 2), (deltaz / 2), deltaz / slice_thickness + 1)

pre_time = 8e-4
gz_reph = make_trapezoid(channel='z', system=system, area=-gz.area / 2, duration=1e-3)

gz_spoil = make_trapezoid(channel='z', system=system, area=gz.area * 2, duration=3 * pre_time)

gx = make_arbitrary_grad(channel='x', system=system, waveform=np.squeeze(np.real(G[:, 0])))

delayTE = TE - calc_duration(gz_reph) - (calc_duration(rf) / 2)
delayTR = TR - calc_duration(gz_reph) - calc_duration(rf) - calc_duration(gx) - calc_duration(gz_spoil)
delay1 = make_delay(delayTE)
delay2 = make_delay(delayTR)

for s in range(n_slices):
    freq_offset = gz.amplitude * z[s]
    rf.freq_offset = freq_offset

    for ns in range(n_shots):
        seq.add_block(rf, gz)
        seq.add_block(gz_reph)

        gx = make_arbitrary_grad(channel='x', system=system, waveform=np.squeeze(np.real(G[:, ns])))
        gy = make_arbitrary_grad(channel='y', system=system, waveform=np.squeeze(np.imag(G[:, ns])))

        seq.add_block(delay1)
        seq.add_block(gx, gy, adc)
        seq.add_block(gz_spoil)
        seq.add_block(delay2)

# Display entire plot
# seq.plot()

# The .seq file will be available inside the /gpi/<user>/imr_framework folder
seq.write('spiral_2d_256_9_3_16_python.seq')