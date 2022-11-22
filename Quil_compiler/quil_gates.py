from quil_utils import *
from pyquil.quil import Pragma, Program
from pyquil.api import get_qc
from pyquil.gates import *

qc = get_qc(name='Aspen-M-2',as_qvm=True)

gates = []
for key in QUANTUM_GATES:
    gate = QUANTUM_GATES[key]
    if 'angle' not in signature(gate).parameters.keys():
        gates.append(quil_gate(qc,gate))

for gate in gates:
    save_gates_to_file('quil_gates.json',gate)
    

