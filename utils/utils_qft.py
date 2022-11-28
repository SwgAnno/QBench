# general imports
import math

import numpy as np

# AWS imports: Import Braket SDK modules
from braket.circuits import Circuit, circuit
#non recursive QFT implementation kindly borrowed by braket examples

@circuit.subroutine(register=True)
def qft(qubits,swaps=True):    
    """
    Construct a circuit object corresponding to the Quantum Fourier Transform (QFT)
    algorithm, applied to the argument qubits.  Does not use recursion to generate the QFT.
    
    Args:
        qubits (int array): The list of qubits on which to apply the QFT
        swaps (bool) : Apply the ending swaps
    """
    qftcirc = Circuit()
    
    # get number of qubits
    num_qubits = len(qubits)
    
    for k in range(num_qubits):
        # First add a Hadamard gate
        qftcirc.h(qubits[k])
    
        # Then apply the controlled rotations, with weights (angles) defined by the distance to the control qubit.
        # Start on the qubit after qubit k, and iterate until the end.  When num_qubits==1, this loop does not run.
        for j in range(1,num_qubits - k):
            angle = 2*math.pi/(2**(j+1))
            qftcirc.cphaseshift(qubits[k+j],qubits[k], angle)
    
    if swaps:
        # Then add SWAP gates to reverse the order of the qubits:
        for i in range(math.floor(num_qubits/2)):
            qftcirc.swap(qubits[i], qubits[-i-1])

    return qftcirc



@circuit.subroutine(register=True)
def inverse_qft(qubits,swaps=True):
    """
    Construct a circuit object corresponding to the inverse Quantum Fourier Transform (QFT)
    algorithm, applied to the argument qubits.  Does not use recursion to generate the circuit.
    
    Args:
        qubits (int): The list of qubits on which to apply the inverse QFT
        swaps (bool) : Apply the ending swaps

    """
    # instantiate circuit object
    qftcirc = Circuit()
    
    # get number of qubits
    num_qubits = len(qubits)
    
    if swaps:
        # First add SWAP gates to reverse the order of the qubits:
        for i in range(math.floor(num_qubits/2)):
            qftcirc.swap(qubits[i], qubits[-i-1])
        
    # Start on the last qubit and work to the first.
    for k in reversed(range(num_qubits)):
    
        # Apply the controlled rotations, with weights (angles) defined by the distance to the control qubit.
        # These angles are the negative of the angle used in the QFT.
        # Start on the last qubit and iterate until the qubit after k.  
        # When num_qubits==1, this loop does not run.
        for j in reversed(range(1, num_qubits - k)):
            angle = -2*math.pi/(2**(j+1))
            qftcirc.cphaseshift(qubits[k+j],qubits[k], angle)
            
        # Then add a Hadamard gate
        qftcirc.h(qubits[k])
    
    return qftcirc
