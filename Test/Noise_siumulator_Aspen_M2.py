import sys
sys.path.append("../utils/")
# sys.path.append("./utils/")

import numpy as np
import pandas as pd
from braket.aws import AwsDevice
from braket.circuits import Circuit, Gate, Noise, Observable,Qubit
from braket.circuits.noise_model import (GateCriteria, NoiseModel,
                                         ObservableCriteria)
from braket.circuits.noises import (AmplitudeDamping, BitFlip, Depolarizing,
                                    PauliChannel, PhaseDamping, PhaseFlip,
                                    TwoQubitDepolarizing)
from braket.devices import LocalSimulator
from utils import DeviceScanner,DeviceUtils
from quil_utils import Braket_to_Quil_Transpiler,Quil_to_Braket_Transpiler, get_braket_qubit_number
# from utils.quil_utils import Braket_to_Quil_Transpiler,Quil_to_Braket_Transpiler, get_braket_qubit_number
from copy import deepcopy


def simulate_noise_aspen_m_2(braket_circ : Circuit()):
    """
    It simulates noise using calibration data available at https://us-east-1.console.aws.amazon.com/braket/home?region=us-east-1#/devices/arn:aws:braket:us-west-1::device/qpu/rigetti/Aspen-M-2

    Parameters
    ----------
    braket_circ: braket.Circuit() Circuit to simulate with real noise
    
    Output
    ----------
    
    """
   
    aspen_m_2 = DeviceUtils.get_device("rigetti")

    aspen_m_2_specs = aspen_m_2.properties.dict()["provider"]["specs"]

    one_qubit_data = aspen_m_2_specs["1Q"]
    two_qubit_data = aspen_m_2_specs["2Q"]

    # median 1q and 2q gate times
    gate_time_1_qubit = 40e-9
    gate_time_2_qubit = 180e-09

        
    noise_model = NoiseModel()
    # Single-qubit noise
    for q, data in one_qubit_data.items():  # iterate over qubits

        # T1 dampening
        t1 = data["T1"]
        damping_prob = 1 - np.exp(-(gate_time_1_qubit / t1))
        noise_model.add_noise(AmplitudeDamping(damping_prob), GateCriteria(qubits=int(q)))

        # T2 phase flip
        t2 = data["T2"]
        dephasing_prob = 0.5 * (1 - np.exp(-(gate_time_1_qubit / t2)))
        noise_model.add_noise(PhaseDamping(dephasing_prob), GateCriteria(qubits=int(q)))

        # 1q RB depolarizing rate from simultaneous RB
        depolar_rate = 1 - data["f1Q_simultaneous_RB"]
        noise_model.add_noise(Depolarizing(depolar_rate), GateCriteria(qubits=int(q)))

        # 1q RB readout
        readout_value = 1 - data["fRO"]
        noise_model.add_noise(BitFlip(readout_value), ObservableCriteria(qubits=int(q)))



    # Two-qubit noise
    for pair, data in two_qubit_data.items():  # iterate over qubit connections

        # parse strings "0-1" to integers [0, 1]
        q0, q1 = (int(s) for s in pair.split("-"))

        if "fCPHASE" in data:
            phase_rate = 1 - data["fCPHASE"]
            noise_model.add_noise(
                TwoQubitDepolarizing(phase_rate),
                GateCriteria(
                    Gate.CPhaseShift, [(q0, q1), (q1, q0)]
                ),  # symmetric connections
            )

        if "fXY" in data:
            xy_rate = 1 - data["fXY"]
            noise_model.add_noise(
                TwoQubitDepolarizing(xy_rate), GateCriteria(Gate.XY, [(q0, q1), (q1, q0)])
            )

        if "fCZ" in data:
            cz_rate = 1 - data["fCZ"]
            noise_model.add_noise(
                TwoQubitDepolarizing(cz_rate), GateCriteria(Gate.CZ, [(q0, q1), (q1, q0)])
            )

    #exploiting transpilers to have a computable circuit with logical qubits starting from 0
    
    #simulation    
    #np.random.seed(42)
    noisy_circ = noise_model.apply(braket_circ)
    # quil_noisy_circ = Braket_to_Quil_Transpiler(noisy_circ).quil_circ
    # rewired_noisy_circ = Quil_to_Braket_Transpiler(quil_noisy_circ,quil_rewiring=False)
    rewired_circ, qubit_mapping = Rewiring_circ(noisy_circ)
    return rewired_circ, qubit_mapping




# class Braket_Circuit_Rewiring():
#     def __init__ (self,braket_circ : Circuit()):
#         self.rewired_circ,  
#         self.qubit_mapping = self._Rewiring_circ(braket_circ)

def Rewiring_circ(braket_circ : Circuit()):
    """
    rewires a physical circuit to 'logical qubits' starting from 0 to n_qubits.
    It creates a circuit that fits the local simulators standards

    Parameters
    ----------
    braket:circ : braket.Circuit()  a Circuit object with physical qubits labeling

    Output:
    --------
    rewired_circ : braket.Circuit() a Circuit object with logical qubits labeling

    """
    rewired_circ = Circuit()
    

    qubit_mapping = {}
    instructions = deepcopy(braket_circ.instructions)
    for instruction in instructions:
        n_qubits = instruction.operator.qubit_count
        target_qubits = []
        for i in range(n_qubits):
            target_qubits.append(instruction.target.item_list[i].real)

        logical_qubit_numbers = [get_braket_qubit_number(qubit_mapping,target_qubit) for target_qubit in target_qubits]
        new_instruction = deepcopy(instruction)
        new_instruction.target.clear()
        for qubit_label in logical_qubit_numbers:
            new_instruction.target.add(Qubit(int(qubit_label)) )
        rewired_circ.add_instruction(instruction=new_instruction)
    return rewired_circ,qubit_mapping