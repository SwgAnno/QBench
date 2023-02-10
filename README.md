# QBench
Collection of simple Benchmarking experiments to assess performance differences in Amazon Bracket devices.
The experiments have been run during winter 2022 and targeted the main gate-based QPUs available on Braket at that time:

- Ionq11 from Ionq
- Aspen M-2 from Rigetti
- (Lucy from OQC)

# Content

Brief description of the files organized in each folder

### AWS_objects
Exploring and reverse engeneering the criptic structure of the AWS SDK objects to extract all possibly useful informations

### examples
DIY fork of Braket SDK examples

### Deutsch

Two example notebooks  implementing Deutsch algorithm with Braket SDK and visualising its results

### QFT

QFT test on Rigetti, Ionq and OQC devices.

Implementation on the two superconducting qubits devices follows the one given in  aws/amazon-braket-examples  repository.

CPhase for IonQ hardware had to be implemented from scratch, not being directly avaliable in the braket SDK

The notebooks includes results of some 3 to 10 qubits QFT launched one the various devices

A last notebook tries a QPE implementation

### RIVETTI VS IONQ

Main QPU benchmarck experiments where we tested and compared the capabilities of IonQ11 and Aspen M-2.
The experiments assessed in a simple way two relevant parameters for computation : 
- Single Gate Fidelity 
- Entangling gate Quality.

The single gate fidelity experiment, codename H_line, implemented from scartch a native version of the H gate for each device and applyed this gate a set even number of time on every qubit.
The resulting circuit behaves like a noisy identity, the quality of the output and the size of the resulting noise is directly correlated to the quality of the implemented gate.

The entangling gate experiment, codename GHZ, tried to create a bigger and bigger GHZ state using the canonical Hadamard + CNOT circuid and assessed the quality of the output.

### development

Attempt at creating a compiling tool

### utils

Random utils that had been written for the various experiments

# Credits

Those experiments are the result of a side university project carried on for the MSc degree in Physics, Quantum Physics&Tech major during winter 2022.
Two people contributed to this code:
- Emilio Annoni, emilio.annoni@studenti.unimi.it
- Emilio Rui, emilio.rui@studenti.unimi.it

Thanks for stopping by!