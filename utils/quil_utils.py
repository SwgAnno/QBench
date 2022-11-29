"""
Basic idea is to create a sort of DB (maybe in a json file?) with all the basic circuits compiled.

When you have a compiled quil code you give it to the transpiler and it gives you back the higher level code

"""

from pyquil.quil import Pragma, Program
from pyquil.api import get_qc
from pyquil.gates import *
from inspect import signature
import json
import re
from utils import DeviceScanner,DeviceUtils
from braket.circuits import Circuit, Gate, Instruction, circuit, Observable
import numpy as np

def get_gate_name(gate_str):
    """
    Given a string of a gate in quil returns only the gate name

    example: gate_str = 'I 0'
    returns: 'I'
    
    Parameters
    ----------
    gate_str = str 
        the string of a gate in quil e.g. 'I 0'
    """
    return re.split(' ', gate_str)[0]

class Compiled_gate(object):
    def __init__(self,device,gate_program):
        self.standard = device.compile(gate_program)
        self.native_quil = device.compiler.quil_to_native_quil(gate_program, protoquil=True)
        self.executable = device.compiler.native_quil_to_executable(self.native_quil)

    def as_dict(self):
        return {
            'standard'  : str(self.standard),
            'native_quil'  : str(self.native_quil),
            'executable'   : str(self.executable)
            }


class quil_gate(object):
    def __init__( self, device, gate, rewiring_strategy='PARTIAL'):
        self.device = device
        
        
        rewiring_string='PRAGMA INITIAL_REWIRING "' +rewiring_strategy +'"'
        
        
        n_inputs = len(signature(gate).parameters)
        self.gate_name = get_gate_name (str(gate(*range(n_inputs))))

        self.gate_program = Program(rewiring_string) + gate(*range(n_inputs))
        self.compiled_gate = Compiled_gate (device,self.gate_program)
        
    def as_dict(self):
        return{
            'gate_name' : self.gate_name,
            'gate_program'  : str(self.gate_program),
            'compiled_gate' : self.compiled_gate.as_dict(),
            'device'    : str(self.device),
        }

    
    

class Compiled_Circuit(object):
    def __init__(self,device,program):
        self.standard = device.compile(program)
        self.native_quil = device.compiler.quil_to_native_quil(program, protoquil=True)
        self.executable = device.compiler.native_quil_to_executable(self.native_quil)

    def as_dict(self):
        return {
            'standard'  : str(self.standard),
            'native_quil'  : str(self.native_quil),
            'executable'   : str(self.executable)
            }
    
    
    

class Quil_to_Braket_Transpiler(object):
    def __init__(self,string_circ,quil_rewiring = False):
        self.braket_circ,self.qubit_mapping = transpile_quil_to_braket(string_circ,quil_rewiring)
        
        

        
        
        
class Braket_to_Quil_Transpiler(object):
    def __init__(self,braket_circ):
        self.quil_circ = transpile_braket_to_quil(braket_circ)
    
    def quil_compiled_circuit(self,device):
        return Compiled_Circuit(device,self.quil_circ)
    
    def verbatim_circ(self,compiler_device):
        
        return Quil_to_Braket_Transpiler(str(self.quil_compiled_circuit(compiler_device).executable), quil_rewiring=True).braket_circ

    
    
    
    
def save_gates_to_file(filename,gate):
    '''
    Save to a json file the compiled version of gates.
    
    Parameters
    ----------
    filename: str
        the name of the file to save the data
    gate :  quil_gate object
        the object containing a gate

    '''
    try:
        with open (filename,'r') as f:
            json_db = json.load(f)
        #print(old_json)
    #if the file is not created we try
    except:
        json_db = {}
    
    gate_dic = (gate.as_dict())
    json_db[gate_dic['gate_name']] = gate.as_dict()

    #json_db['gates'].append((gate.as_dict()))
    #print('updated version', old_json)
    with open (filename,'w') as gate_file:
        json.dump(json_db,gate_file,indent=4)


def print_db(dic):
    '''
    print a dictionary in an ordered way, in case of nested dicts
    
    Parameters
    ----------
    dic: dict
    dictionary to print

    '''
    for key,value in dic.items():
        if isinstance(value,dict):
            print(key,':') 
            print_db(value)
            print('\n\n')
        else:
            print(key, ':', value)


            
def transpile_quil_to_braket(string_circ,quil_rewiring = False):
    """

    Parameters
    ----------
    string_circ: str
    string version of a quil circuit
    quil_rewiring: book, keeps qubits labeling of quil or standard :(O:n_qubits)
    
    
    Output
    ----------
    braket_circ: aws_braket.Circuit()
    corresponding braket_circuit
    """
    transpile_tuple = [
        ('ccnot', 'CCNOT'),
        ('cnot', 'CNOT'),
        ('cphaseshift', 'CPHASE'),
        ('cphaseshift00', 'CPHASE00'),
        ('cphaseshift01', 'CPHASE01'),
        ('cphaseshift10', 'CPHASE10'),
        ('cswap', 'CSWAP'),
        ('cz', 'CZ'),
        ('h', 'H'),
        ('i', 'I'),
        ('iswap', 'ISWAP'),
        ('phaseshift', 'PHASE'),
        ('pswap', 'PSWAP'),
        ('rx', 'RX'),
        ('ry', 'RY'),
        ('rz', 'RZ'),
        ('s', 'S'),
        ('swap', 'SWAP'),
        ('t', 'T'),
        ('x', 'X'),
        ('xy', 'XY'),
        ('y', 'Y'),
        ('z', 'Z')]

    qubit_mapping = {}

    braket_circ = Circuit()
    braket_circ_cmd = 'braket_circ'

    for str_line in string_circ.splitlines():
        quil_code = str_line.split()
        if 'DECLARE' in quil_code:
            qubits_used = int(''.join([x for x in quil_code[-1] if x.isdigit()]))
            #print(qubits_used)
        if any (string in quil_code for string in ['INITIAL_REWIRING','RESET','MEASURE','DECLARE']):
            continue
        gate_has_angle = '(' in str_line


        quil_code = str_line.replace('(', ' ').replace(')', ' ').split()
    #     quil_code.remove('(')
    #     quil_code.remove(')')

        gates_dict = dict(reverseTuple(transpile_tuple))
        quil_gate = quil_code[0]
        braket_gate = gates_dict[quil_gate]
        if gate_has_angle:
            angle = quil_code[1].replace('pi','np.pi')
        quil_qubits = quil_code[2:] if gate_has_angle else quil_code[1:]

        braket_qubits = []
        for quil_qubit in quil_qubits:
            braket_qubits.append(get_braket_qubit_number(qubit_mapping,quil_qubit))
        
        gate_qubits = braket_qubits if not quil_rewiring else quil_qubits
        
        braket_gate_cmd = braket_gate + '(' + ','.join(gate_qubits) 
    
        braket_gate_cmd += ','+ angle + ')' if gate_has_angle else ')'
        braket_circ_cmd += '.'+ braket_gate_cmd
    exec(braket_circ_cmd)
    return braket_circ,qubit_mapping


def reverseTuple(list_of_tuple):
    return list(map(lambda tup: tup[::-1], list_of_tuple))

def get_braket_qubit_number(qubit_mapping,quil_qubit):
    """
    Returns the mapping in braket of quil qubit
    
    Parameters
    ----------
    qubit_mapping = dict
    quil_qubit = str
    """
    if not quil_qubit in qubit_mapping.keys():
        qubit_mapping[quil_qubit] = str(len(qubit_mapping.keys()))
 
    return qubit_mapping[quil_qubit]


def transpile_braket_to_quil(braket_circuit):
    n_tot_qubits = len(braket_circuit.qubits.item_list)
    #qc = get_qc(name='Aspen-M-2',as_qvm=True)
    quil_prog = Program()
    ro = quil_prog.declare('ro', 'BIT', n_tot_qubits)
    quil_prog += Pragma('INITIAL_REWIRING', ['"PARTIAL"'])
    quil_prog += RESET()

    instructions = braket_circuit.instructions
    for instruction in instructions:
        braket_gate = str(instruction.operator).replace('(',' ').split()[0]
        n_qubits = instruction.operator.qubit_count
        target_qubits = []
        for i in range(n_qubits):
            target_qubits.append(instruction.target.item_list[i].real)
        
        parameter = None
        if '_parameters' in instruction.operator.__dict__.keys():
            parameter = instruction.operator.__dict__['_parameters']

        quil_gate = QUANTUM_GATES [gate_name_braket_to_quil(braket_gate)]
        
        inputs = parameter + target_qubits if parameter  else target_qubits
        quil_prog += quil_gate(*inputs)

    for i in range(n_tot_qubits):
        quil_prog += MEASURE(braket_circuit.qubits.item_list[i].real, ro[i] )
    return quil_prog

def gate_name_braket_to_quil(gate_name):
    return gate_name.replace('Shift','').upper()

# def transpile_tuple_creation():
#     """
#     creates a tuple with corresponding gates of quil (left) and braket(right)

#     Output
#     ----------
#     transpile_tuple: tuple
#     """
#     device=DeviceUtils.get_device('rigetti')
#     rigetti_gates = DeviceScanner(device=device).get_supported_gates()
#     quil_gates = QUANTUM_GATES.keys()
#     rigetti_gates.sort()
#     quil_gates.sort()
#     for i in range(max(len(rigetti_gates)))
#     #removing excess gates from braket circuit
    