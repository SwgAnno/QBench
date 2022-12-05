import sys

# AWS imports: Import Braket SDK modules

import matplotlib.pyplot as plt

from braket.circuits import Circuit, Gate, Instruction, circuit, Observable
from braket.devices import LocalSimulator
from braket.aws import AwsDevice ,AwsQuantumTask
import numpy as np

import functools
import time

from quil_utils import *
from pyquil.quil import Pragma, Program
from pyquil.api import get_qc,QVM
from pyquil.gates import *
from quil_utils import Compiled_Circuit,Quil_to_Braket_Transpiler,Braket_to_Quil_Transpiler
from utils import DeviceUtils,DeviceScanner,BraketTaskScanner,Plotter
from IonQCompiler import IonQCompiler

import json
import pandas as pd
import seaborn as sns

import re

@circuit.subroutine(register=True)
def H_line (n_qubits,line_length,device_name):
    """
    Creates a circuit with n_qubits, each with line_length hadamards applied
    
    Parameters:
    ----------------
    n_qubits : int #of qubits
    line_length : int # of Hadamards to apply to each qubit
    device_name : str #name of the QPU it is going to run on
    """
    qubits = range(n_qubits) if isinstance(n_qubits,int) else n_qubits
    
    if device_name =='LocalSimulator':
        base_circ = Circuit()
        for _ in range(line_length):
            base_circ.h(range(n_qubits))
        return base_circ

    elif device_name == 'Rigetti':
        qc = get_qc(name='Aspen-M-2',as_qvm=True)
        #first we compile Hadamard gate, then we repeat it in order to have it executed N times, first we transpile it in quil, then compile it, then retranspile in braket
        H_gate = Circuit().h(range(n_qubits))
        transpiled_H_gate = Braket_to_Quil_Transpiler(H_gate)
        compiled_H = transpiled_H_gate.verbatim_circ(qc)
        
        H_line_circ = Circuit()
        for _ in range(line_length):
            H_line_circ.add_circuit(compiled_H)
            
    elif device_name == 'IonQ':
        c = IonQCompiler()
        H_gate = Circuit().h(range(n_qubits))
        compiled_H = c.compile(H_gate)
        H_line_circ = Circuit()
        for _ in range(line_length):
            H_line_circ.add_circuit(compiled_H)
        
    return H_line_circ


def result_per_qubit( result, H_len : int):
    """
    Process Braket task results in result into a dataframe
    Output dataframe sorts results per qubit and add a label
    """

    n_qubits = len(result.measurements[0,:])
    shots = len(result.measurements[:,0])

    measure = []

    for qubit_number in range(n_qubits):
        #meas[str(qubit_number)] = {'0':0,'1':0}
        ones = result.measurements[:,qubit_number].sum()
        zeros = shots - ones

        measure.append({'H_len' : H_len,
                'qubit_n' : qubit_number,
            'value': '0',
                'counts' : zeros})
        measure.append({'H_len' : H_len,
                'qubit_n' : qubit_number,
            'value': '1','counts':ones})
    #         meas[str(qubit_number)]['1'] = ones
    #         meas[str(qubit_number)]['0'] = zeros

    return pd.DataFrame(measure)

def plot_result_per_qubit(data : pd.DataFrame, ax = None ):

    if ax == None:
        fig, ax = plt.subplots(1, 1, figsize=(5, 6))

    sns.barplot(x="qubit_n", y="counts",hue="value", data=data,ax=ax)
    ax.set_ylabel("Counts")
    ax.set_xlabel("Qubit_number")

    return ax

def get_rigetti_compilation_map( src ):

    measure_re = "MEASURE (\d+) \w+\[(\d+)\]"

    matches = re.findall(measure_re,src)

    out = dict()
    for m in matches:
        out[int(m[1])] = int(m[0])

    return out


def dump_tasks( tasks , labels = None, filename :str = None):

    if filename == None:
        filename = "quantum_task_dump" + str(int(np.random()*10000))
    if labels == None:
        labels = np.arange(0, len(tasks))

    task_id_dict = {}

    for task, label in zip(tasks, labels):
        task_id_dict[label] = { 'id' : task.id}

    with open(filename,'w') as f:
        json.dump(task_id_dict,f,indent=3)

def load_tasks( filename : str):

    with open(filename,'r') as f:
        task_ids =json.load(f)

    #return array of quantum tasks
    out = dict()

    for key, task in task_ids.items():
        out[key] = AwsQuantumTask(task["id"])


    return out