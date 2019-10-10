import uuid
import numpy as np
import tensorflow as tf
import tensorflow_probability as tfp
import matplotlib.pyplot as plt





class Device:
    """
    """
    def __init__(
            self,
            name = " ",
            desc = " ",
            comment = " ",
            resolutions = {},
            resources = [],
            resource_groups = {}
            ):

        self.name = name
        self.desc = desc
        self.comment = comment
        self.resolutions = resolutions
        self.resources = resources
        self.resource_groups = resource_groups


    def calc_slice_num(self, res_key):
        res = self.resolutions[res_key]

        if self.t_start != None and self.t_end != None and res != None:
            self.slice_num = int(np.abs(self.t_start - self.t_end) * res)
        else:
            self.slice_num = None


    def create_ts(self, res_key):
        if self.t_start != None and self.t_end != None and self.slice_num != None:
            dt = 1/self.resolutions[res_key]
            t_start = tf.constant(self.t_start + dt/2, dtype=tf.float64)
            t_end = tf.constant(self.t_end - dt/2, dtype=tf.float64)
            self.ts = tf.linspace(t_start, t_end, self.slice_num)
        else:
            self.ts = None

    def plot_IQ_components(self, fig=None, ax=None):
        """ Plotting control functions """

        ts = self.ts
        I = self.Inphase
        Q = self.Quadrature

        if ax is None:
            plt.rcParams['figure.dpi'] = 100
            fig, ax = plt.subplots(1, 1)
        else:
            ax.clear()

        ax.plot(ts/1e-9, I)
        ax.plot(ts/1e-9, Q)
        ax.grid()
        plt.legend(['I', 'Q'])
        plt.xlabel('Time [ns]')
        # I (Kevin) don't really understand the behaviour of plt.show()
        # here. If I only put plt.show(block=False), I get error messages
        # on my system at home. Adding a second plt.show() resolves that
        # issue???
        # look at:  https://github.com/matplotlib/matplotlib/issues/12692/

        fig.canvas.draw()
        fig.canvas.flush_events()





class Mixer(Device):
    """
    """
    def __init__(
            self,
            name = " ",
            desc = " ",
            comment = " ",
            resolutions = {},
            resources = [],
            resource_groups = {},
            t_start = None,
            t_end = None,
            Inphase = [],
            Quadrature = []
            ):

        super().__init__(name, desc, comment, resolutions, resources, resource_groups)

        self.t_start = t_start
        self.t_end = t_end

        self.slice_num = None
        self.ts = []

        self.Inphase = Inphase
        self.Quadrature = Quadrature

        self.output = []


    def combine(self, res_key):

        self.calc_slice_num(res_key)
        self.create_ts(res_key)


        ts = self.ts

        carr_group = self.resource_groups["carr"]
        carr_group_id = carr_group.get_uuid()


        control = self.resources[0]
        for comp in control.comps:
            if carr_group_id in comp.groups:
                omega_lo = comp.params["freq"]


        self.output = tf.zeros_like(ts)

        self.output += (self.Inphase * tf.cos(omega_lo * ts) +
                        self.Quadrature * tf.sin(omega_lo * ts))


class AWG(Device):
    """
    """
    def __init__(
            self,
            name = " ",
            desc = " ",
            comment = " ",
            resolutions = {},
            resources = [],
            resource_groups = {},
            t_start = None,
            t_end = None
            ):

        super().__init__(name, desc, comment, resolutions, resources, resource_groups)

        self.t_start = t_start
        self.t_end = t_end

        self.slice_num = None
        self.ts = []

        self.Inphase = []
        self.Quadrature = []
        self.amp_tot_sq = None


    def create_IQ(self, res_key):
        """
        Construct the in-phase (I) and quadrature (Q) components of the

        control signals. These are universal to either experiment or
        simulation. In the experiment these will be routed to AWG and mixer
        electronics, while in the simulation they provide the shapes of the
        controlfields to be added to the Hamiltonian.

        """

        with tf.name_scope("I_Q_generation"):

            self.calc_slice_num(res_key)
            self.create_ts(res_key)

            ts = self.ts


            Inphase = []
            Quadrature = []

            env_group = self.resource_groups["env"]
            env_group_id = env_group.get_uuid()

            amp_tot_sq = 0.0
            I_components = []
            Q_components = []

            control = self.resources[0]
            if (control.comps[1].name == 'pwc'):
                self.amp_tot = 1
                self.Inphase = control.comps[1].params['Inphase']
                self.Quadrature = control.comps[1].params['Quadrature']
            else:
                for comp in control.comps:
                    if env_group_id in comp.groups:

                        amp = comp.params['amp']

                        amp_tot_sq += amp**2

                        xy_angle = comp.params['xy_angle']
                        freq_offset = comp.params['freq_offset']
                        I_components.append(
                            amp * comp.get_shape_values(ts) *
                            tf.cos(xy_angle - freq_offset * ts)
                            )
                        Q_components.append(
                            amp * comp.get_shape_values(ts) *
                            tf.sin(xy_angle - freq_offset * ts)
                            )

                norm = tf.sqrt(tf.cast(amp_tot_sq, tf.float64))
                Inphase = tf.add_n(I_components, name="Inhpase")/norm
                Quadrature = tf.add_n(Q_components, name="Quadrature")/norm

                self.amp_tot = norm
                self.Inphase = Inphase
                self.Quadrature = Quadrature


    def get_I(self):
        return self.amp_tot * self.Inphase


    def get_Q(self):
        return self.amp_tot * self.Quadrature


    # def plot_IQ(self, ts, Is, Qs):
        # """
        # Plot (hopefully) into an existing figure.
        # """
        # plt.cla()
        # plt.plot(ts / 1e-9, Is)
        # plt.plot(ts / 1e-9, Qs)
        # plt.legend(("I", "Q"))
        # plt.ylabel('I/Q')
        # plt.xlabel('Time[ns]')
        # plt.tick_params('both',direction='in')
        # plt.tick_params('both', direction='in')




    def plot_fft_IQ_components(self, axs=None):


        print("""WARNING: still have to ad from c3po.control.generator import Device as Device
from c3po.control.generator import AWG as AWG
from c3po.control.generator import Mixer as Mixer
from c3po.control.generator import Generator as Generatorjust the x-axis""")


        ts = self.ts
        I = self.Inphase
        Q = self.Quadrature


        """ Plotting control functions """
        plt.rcParams['figure.dpi'] = 100

        fft_I = np.fft.fft(I)
        fft_Q = np.fft.fft(Q)
        fft_I = np.fft.fftshift(fft_I.real / max(fft_I.real))
        fft_Q = np.fft.fftshift(fft_Q.real / max(fft_Q.real))

        fig, axs = plt.subplots(2, 1)
        axs[0].plot(ts, fft_I)
        axs[1].plot(ts, fft_Q)
        # I (Kevin) don't really understand the behaviour of plt.show()
        # here. If I only put plt.show(block=False), I get error messages
        # on my system at home. Adding a second plt.show() resolves that
        # issue???
        # look at:  https://github.com/matplotlib/matplotlib/issues/12692/
        plt.show(block=False)
        plt.show()



class Generator:
    """

    """
    def __init__(
            self,
            devices = {},
            resolutions = {},
            resources = [],
            resource_groups = {}
            ):

        self.devices = devices
        self.resolutions = resolutions
        self.resources = resources
        self.resource_groups = resource_groups

        self.output = None


    def generate_signals(self, resources = []):
        with tf.name_scope('Signal_generation'):

            if resources == []:
                resources = self.resources

            output = {}

            awg = self.devices["awg"]
            mixer = self.devices["mixer"]

            for ctrl in resources:

                awg.t_start = ctrl.t_start
                awg.t_end = ctrl.t_end
                awg.resolutions = self.resolutions
                awg.resources = [ctrl]
                awg.resource_groups = self.resource_groups
                awg.create_IQ("awg")

                #awg.plot_IQ_components("awg")
                #awg.plot_fft_IQ_components("awg")

                mixer.t_start = ctrl.t_start
                mixer.t_end = ctrl.t_end
                mixer.resolutions = self.resolutions
                mixer.resources = [ctrl]
                mixer.resource_groups = self.resource_groups
                mixer.calc_slice_num("sim")
                mixer.create_ts("sim")

                I = tfp.math.interp_regular_1d_grid(
                    mixer.ts,
                    x_ref_min = awg.ts[0],
                    x_ref_max = awg.ts[-1],
                    y_ref = awg.get_I()
                    )
                Q =  tfp.math.interp_regular_1d_grid(
                    mixer.ts,
                    x_ref_min = awg.ts[0],
                    x_ref_max = awg.ts[-1],
                    y_ref = awg.get_Q()
                    )

                mixer.Inphase = I
                mixer.Quadrature = Q
                mixer.combine("sim")

                output[(ctrl.name,ctrl.get_uuid())] = {"ts" : mixer.ts}
                output[(ctrl.name,ctrl.get_uuid())].update(
                    {"signal" : mixer.output}
                    )

                self.output = output

        return output



    def plot_signals(self, resources = []):

        if resources != []:
            self.generate_signals(resources)

        for entry in self.output:
            ctrl_name = entry[0]
            control = self.output[entry]

            """ Plotting control functions """
            plt.rcParams['figure.dpi'] = 100


            ts = control["ts"]
            signal = control["signal"]

            fig = plt.figure()
            ax = fig.add_subplot(1, 1, 1)
            ax.plot(ts.numpy(), signal.numpy())
            ax.set_xlabel('Time [ns]')
            plt.title(ctrl_name)
            plt.grid()
            plt.show(block=False)


    def plot_fft_signals(self, resources = []):

        if resources != []:
            self.generate_signals(resources)

        print("WARNING: still have to adjust the x-axis")

        for entry in self.output:
            ctrl_name = entry[0]
            control = self.output[entry]


            """ Plotting control functions """
            plt.rcParams['figure.dpi'] = 100

            ts = control["ts"]
            signal = control["signal"]


            fft_signal = np.fft.fft(signal)
            fft_signal = np.fft.fftshift(fft_signal.real / max(fft_signal.real))

            plt.plot(ts, fft_signal)
            plt.title(ctrl_name + " (fft)")

            plt.show(block=False)
