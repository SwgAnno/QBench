import sys
sys.path.append("../utils/")

# AWS imports: Import Braket SDK modules

from typing import List
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable
import qutip
from mpl_toolkits.mplot3d import Axes3D


from braket.circuits import Circuit, Gate, Instruction, circuit, Observable
from braket.devices import LocalSimulator
from braket.aws import AwsDevice ,AwsQuantumTask
import numpy as np
from numpy.linalg import eigh

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
import networkx as nx

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
        H_gate = Circuit().h(qubits)
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


def result_per_qubit( result, H_len : int = 0):
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

def get_qubit_counts(df, n_qubit):
    return df.iloc[n_qubit:(n_qubit+2),3]


def get_rigetti_compilation_map( src ):

    measure_re = "MEASURE (\d+) \w+\[(\d+)\]"

    matches = re.findall(measure_re,src)

    out = dict()
    for m in matches:
        out[int(m[1])] = int(m[0])

    return out

def get_rigetti_rewiring_map(src):

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

def plot_z_per_qubit(scanner : BraketTaskScanner, cmap = "RdYlGn_r", ax = None) :

    if ax == None:
        fig,ax = plt.subplots(1,1,figsize = (5,6))

    
    df = result_per_qubit( scanner.get_results())
    perr = []

    if scanner.get_task_type() == "RIGETTI":
        compilation_map = get_rigetti_compilation_map( scanner.get_compiled_circuit())
    elif scanner.get_task_type() == "IONQ":
        compilation_map = { x:x for x in range(11)}
    else:
        raise KeyError("task type not supported")

    graph = scanner.get_device().topology_graph

    
    for qubit in range(len(df["qubit_n"])//2):

        counts = np.array(df[df.qubit_n == qubit]["counts"])
        #print(counts)

        perr.append( counts[1]/(counts[1]+counts[0]))

    colors = [ perr[compilation_map[x]] for x in graph.nodes]
    #print(colors)
    #obj = ax.imshow(perr, vmin = 0, vmax = 1, cmap = "inferno")
    nx.draw_kamada_kawai(graph, with_labels=True, node_color=colors, node_size=300, cmap=cmap, vmin = 0, vmax = 1, ax = ax)


    divider = make_axes_locatable(ax)
    cax = divider.append_axes('right', size='5%', pad=0.05)
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin = 0, vmax=1))
    plt.colorbar(sm, cax=cax, orientation='vertical')


########################################################

def tomography_circuits( circ, n_qubits):

    circ_x = circ.deepcopy().h(n_qubits)
    circ_y = circ.deepcopy().z(n_qubits).s(n_qubits).h(n_qubits)
    circ_z = circ.deepcopy()
    return ( circ_x, circ_y, circ_z)

def get_tomography_results( scanners: List[BraketTaskScanner]):

    n_qubits = [sc.get_results().measured_qubits for sc in scanners]

    per_qubits = [result_per_qubit(sc.get_results()) for sc in scanners]
    maps = [get_rigetti_rewiring_map(sc.get_compiled_circuit()) for sc in scanners]
    
    print(n_qubits)
    #print(scanners[0].get_compiled_circuit())
    #print(per_qubits[0])
    #print(map)
    #aggiungere mappa
    density = dict()
    purity = dict()
    for qubit in range(len(n_qubits[0])) :
        counts_x = np.array(per_qubits[0][per_qubits[0].qubit_n == qubit]["counts"])
        counts_y = np.array(per_qubits[1][per_qubits[1].qubit_n == qubit]["counts"])
        counts_z = np.array(per_qubits[2][per_qubits[2].qubit_n == qubit]["counts"])
        #print(counts)

        print(counts_x)
        x =  (counts_x[1]-counts_x[0])/(counts_x[1]+counts_x[0])
        y =  (counts_y[1]-counts_y[0])/(counts_y[1]+counts_y[0])
        z =  (counts_z[1]-counts_z[0])/(counts_z[1]+counts_z[0])

        r = x**2 + y**2 +z**2
        purity[maps[0][qubit]] = (1+r)/2
        x = x/r
        y = y/r
        z = z/r

        dmat = np.array([[1-z, x+ 1j*y],[x-1j*y, 1+z]], dtype=complex)
        density[maps[0][qubit]] = dmat

    return density,purity

def plot_on_device(data, device : AwsDevice, rewiring_map = None, ax= None, cmap = "RdYlGn_r"):

    if ax == None:
        fig, ax = plt.subplots(1,1, figsize = (5,6))

    if rewiring_map == None:
        rewiring_map = {x:x for x in range(len(data))}

    graph = device.topology_graph
    print(rewiring_map)
    col_vec = [ data.get(rewiring_map.get(x,-1),0) for x in range(len(graph.nodes))]
    nx.draw_kamada_kawai(graph, with_labels=True, node_color=col_vec, node_size=300, cmap=cmap, vmin = 0, vmax = 1, ax = ax)


    divider = make_axes_locatable(ax)
    cax = divider.append_axes('right', size='5%', pad=0.05)
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin = 0, vmax=1))
    plt.colorbar(sm, cax=cax, orientation='vertical')

def plot_density_eigen( densities, fig = None, ax = None, mayavi = False):

    n_mat = len(densities)
    major = np.empty((3, n_mat))
    minor = np.empty((3, n_mat))


    for i , key in enumerate(densities):

        values, vectors = eigh(densities[key])

        mi = vectors[:,0]
        mj = vectors[:,1]

        minor[:,i] =( (np.abs(mi[1])**2-np.abs(mi[0])**2), 2* np.real( mi[0]*np.conj(mi[1])),2* np.imag( mi[0]*np.conj(mi[1])))
        major[:,i] =( (np.abs(mj[1])**2-np.abs(mj[0])**2), 2* np.real( mj[0]*np.conj(mj[1])),2* np.imag( mj[0]*np.conj(mj[1])))

    if mayavi :
        b=qutip.Bloch3d()
    else:
        if ax == None:
            fig = plt.figure(figsize= (6,6))
            ax = Axes3D(fig, azim=-40, elev=30)

        b = qutip.Bloch(axes=ax)
    b.add_points([minor[1], minor[2], minor[0]])
    b.add_points([major[1], major[2], major[0]])
    #b.make_sphere()
    b.show()

    return ax