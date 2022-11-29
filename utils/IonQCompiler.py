import sys

sys.path.append("../")


import re
from utils import *
from qiskit import QuantumCircuit, QuantumRegister,ClassicalRegister, transpile
import numpy as np
import qiskit.quantum_info as qi

from braket.circuits import Circuit, Gate, Instruction, circuit, Observable


class CompilationNode:

    def __init__(self, n_q, code = None, ch = [], parents = [], params = []) :
        _n_qubits = n_q
        self._childs = ch
        self._parents = parents
        self._params = params
        self._code = code

    def get_parent(self):
        return self._parents

    def set_parent(self, par, i = 0):
        self._get_parents()[i] = par

    def get_child(self):
        return self._childs

    def set_child(self, ch, i = 0):
        self._get_parents()[i] = ch

    def get_code(self):
        return self._code
        

class CompilationNodeBuilder:

    def __init__() :
        pass
    
    def getNode( code):
        pass

    def start():
        return CompilationNode(1, "start")
    def end():
        return CompilationNode(1,"end")

class CompiledCircuitGraph:

    def __init__(self, n_qubits):

        nb = CompilationNodeBuilder()

        self._reg = []

        for i in n_qubits:
            self._reg.append( nb.start())

    def get_reg(self):
        return self._reg

        
################################

def qasm_downgrade( src):
    """
    DIY compatibility method from OpenQASM3 to OpenQASM2
    """
    def invert_array(match):

        if match.group(1) == "\nbit":
            token = "\ncreg "
        else:
            token = "\nqreg "

        return token + match.group(3) + match.group(2)

    def invert_measure(match):
        return "\n" + match.group(2) + match.group(3) +" -> " + match.group(1)+";"


    src = re.sub( "OPENQASM 3.0;", "OPENQASM 2.0;\ninclude \"qelib1.inc\";", src)
    src = re.sub( "(\nbit)(\[\d+\]) (\w+)", invert_array, src)
    src = re.sub( "(\nqubit)(\[\d+\]) (\w+)", invert_array, src)
    src = re.sub( "\n(\w+\[\d+\]) = (measure )(\w+\[\d+\]);", invert_measure, src)

    ############
    # gates transcription
    # todo :this should be automated

    src = re.sub( "\ncphaseshift", "\ncp", src)
    src = re.sub( "\ncnot", "\ncx", src)

    return src


class IonQCompiler :
    def __init__(self):
        pass

    def compile(self, circ) :
        """
        accept a braket circuit and returns a compilation node structure
        """

        src = self._compile_step1( circ)
        #print(src)
        n_qubits, instr = self._step1_to_list( src)

#         print(n_qubits)


        out = self._compile_step2(n_qubits, instr)

        return out

    def _compile_step1(self, circ):
        """
        accept a general braket circuit and returns a Qiskit circuit which uses only rx,ry,rz, rxx
        """

        src = qasm_downgrade(qasm_source( circ))
        #print(src)
        qiskit_circ = QuantumCircuit.from_qasm_str(src)

        trans_qc = transpile(qiskit_circ, backend = None, basis_gates = ['rx', 'ry', 'rz', 'rxx'])

        return str(trans_qc.qasm())

    def _step1_to_list(self, src):

        instr = []
        n_qubits = -1

        states = ["reg", "gates"]

        s = "reg"
        for l in src.splitlines():
            #print(l)
            if s == "reg":
                # looking for qreg instruction
                m = re.search("qreg \w+\[(\d+)\]", l)

                if m != None:
                    s = "gates"
                    n_qubits =  int(m.group(1))

            if s == "gates":
                #looking for start of gates
                m = re.search("r(\w+)\(((\w|[*/-])+)\) \w+\[(\d+)\](,\w+\[(\d+)\])?", l)

                if m != None:
                    #print("gate!")
                    instr.append(self.gate_tuple(m))

        return n_qubits, instr

    def gate_tuple(self, m):
        """
        accept a match case as input and returns a tuple for CompiledGate init
        """
        gate = m.group(1)
        par = self.format_params(m.group(2))
        regs = []

        regs.append( int(m.group(4)))
        if m.group(6) != None:
            regs.append( int(m.group(6)))

        return (gate,par,regs)


    def format_params(self, p):

        if "pi" in p:
            m = re.search("(-)?((\w+)\*)?pi(/(\w+))?",p)

            if m == None:
                raise RuntimeError("parameter string does not support regex form")

            else:
                s = 1  if m.group(1) == None else -1
                p1 = 1 if m.group(3) == None else float(m.group(3))
                p2 = 1 if m.group(5) == None else float(m.group(5))
                return s*np.pi * p1/p2
        else:
            return p

    def _compile_step2(self, n_qubits, instr):
        

        out = Circuit()

        qphase = [0]*32

        for i in instr :
            #print(i)
            if i[0] == "x":
                if abs(i[1]-0.5*np.pi)<1e-6:
                    out.gpi2(i[2][0], (qphase[i[2][0]]+0)%(2*np.pi))

                elif abs(i[1]+0.5*np.pi)<1e-6:
                    out.gpi2(i[2][0], (qphase[i[2][0]]+np.pi)%(2*np.pi))

                elif abs(i[1]-np.pi)<1e-6:
                    out.gpi(i[2][0], (qphase[i[2][0]]+0)%(2*np.pi))

                elif abs(i[1]+np.pi)<1e-6:
                    out.gpi(i[2][0], (qphase[i[2][0]]+np.pi)%(2*np.pi))

                else :
                    out.gpi2( i[2][0], (qphase[i[2][0]]+(3*np.pi/2))%(2*np.pi) )
                    qphase[i[2][0]]=(qphase[i[2][0]]-i[1])%(2*np.pi)
                    out.gpi2( i[2][0], (qphase[i[2][0]]+(np.pi/2))%(2*np.pi) )

            elif i[0] == "y":
                if abs(i[1]-0.5*np.pi)<1e-6:
                    out.gpi2(i[2][0], (qphase[i[2][0]]+(np.pi/2))%(2*np.pi))

                elif abs(i[1]+0.5*np.pi)<1e-6:
                    out.gpi2(i[2][0], (qphase[i[2][0]]+(3*np.pi/2))%(2*np.pi))

                elif abs(i[1]-np.pi)<1e-6:
                    out.gpi(i[2][0], (qphase[i[2][0]]+(np.pi/2))%(2*np.pi))

                elif abs(i[1]+np.pi)<1e-6:
                    out.gpi(i[2][0], (qphase[i[2][0]]+(3*np.pi/2))%(2*np.pi))

                else :
                    out.gpi2( i[2][0], (qphase[i[2][0]]+0)%(2*np.pi) )
                    qphase[i[2][0]]=(qphase[i[2][0]]-i[1])%(2*np.pi)
                    out.gpi2( i[2][0], (qphase[i[2][0]]+np.pi)%(2*np.pi) )

            elif i[0] == "z":
                qphase[i[2][0]] = (qphase[i[2][0]]-i[1])%(2*np.pi)

            elif i[0] == "xx":
                if i[1]>0 :
                    out.ms(i[2][0],i[2][1], qphase[i[2][0]], qphase[i[2][1]] )
                else :
                    out.ms(i[2][0],i[2][1], qphase[i[2][0]], (qphase[i[2][1]]+np.pi)%(2*np.pi) )


        return out

