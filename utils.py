# general imports
import matplotlib.pyplot as plt

# AWS imports: Import Braket SDK modules
from braket.circuits import Circuit, Gate, Instruction, circuit, Observable
from braket.devices import LocalSimulator
import braket.tracking.tracker as tracker
from braket.aws import AwsDevice ,AwsQuantumTask
import numpy as np

import json     

#Device graph plotting
import networkx as nx

#Simple Bridge to encapsulate Quantum Task and Aws Device information retrival
class BraketTaskScanner(object) :

    def __init__( self, task_arn = None, qtask = None):

        assert task_arn or qtask

        if task_arn :
            qtask = AwsQuantumTask(task_arn)

        self._task = qtask

        arn = qtask.metadata()["deviceArn"]
        self._dscanner = DeviceScanner(arn)

    def get_task(self):
        return self._task
    
    def get_arn(self):
        return self._task._arn

    def get_device(self):
        return self._dscanner.get_device()   
    
    def get_device_status(self):
        return self._dscanner.get_status()  

    def get_device_arn(self):
        return self._dscanner.get_arn()

    def get_device_name(self):
        return self._dscanner.get_name()

    def get_status(self):
        return self.get_task().metadata()["status"] 
    
    def get_shots(self):
        return self.get_task().metadata()["shots"]

    def get_device_provider(self):
        return self._dscanner.get_provider()

    def get_device_native_gates(self):
        return self._dscanner.get_native_gates()

    def get_device_supported_gates(self):
        return self._dscanner.get_supported_gates()

    def get_task_type(self):
        provider = self.get_device_provider()

        if provider == "Amazon Braket":
            return "SIMULATOR"
        elif provider == "IonQ":
            return "IONQ"
        elif provider == "Rigetti":
            return "RIGETTI"
        elif provider == "Oxford":
            return "OQC"

    def get_results(self):
        if not self.results_available():
            print("TASK RESULT ERROR: Results not available")
            return 0

        return self.get_task().result()

    def get_circuit(self):
        result = self.get_results()

        if result :
            return result.additional_metadata.action.source

    def get_compiled_circuit(self):
        result = self.get_results()

        if result :
            type = self.get_task_type()

            if type == "SIMULATOR":
                print("SIMULATOR Task: No compiled source")
                return ""
            elif type == "IONQ":
                print("IONQ Task: No compiled source")
                return ""
            elif type == "RIGETTI" :
                return result.additional_metadata.rigettiMetadata.compiledProgram
            elif type == "OQC" :
                return result.additional_metadata.oqcMetadata.compiledProgram
            

    def task_done(self):
        return self.get_status() in AwsQuantumTask.TERMINAL_STATES

    def results_available(self):
        return self.get_status() in AwsQuantumTask.RESULTS_READY_STATES

    #basic non computational datas about the task
    def list_task_metadata( self):
        meta = self.get_task().metadata()

        print("############################")
        print("Quantum Task Metadata")
        print("Task arn:", meta["quantumTaskArn"])
        print("Task shots#:", meta["shots"])
        print("Task status:", meta["status"])
        print("Task tags:", meta["tags"])
        print("Task on device:", meta["deviceArn"])
        print("Creation date:", meta["createdAt"])
        print("End date:", meta["endedAt"])
        print("Output buket data:", meta["outputS3Directory"], " / ", meta["outputS3Bucket"])

    def cost_extimate(self):

        #simulating auto generated task details to reuse traker cost extimate
        #see implementation of _get_qpu_task_cost for more infos
        new_details = dict()
        new_details["status"] = self.get_status()
        new_details["device"] = self.get_device_arn()
        new_details["job_task"] = False
        new_details["shots"] = self.get_shots()

        out = tracker._get_qpu_task_cost( self.get_arn(), new_details)
        return out




class DeviceScanner(object):

    def __init__( self, device_arn = None, device = None):

        assert device_arn or device

        if device_arn :
            device = AwsDevice(device_arn)

        self._device = device

    def get_device(self):
        return self._device    

    def get_status(self):
        return self.get_device().status

    def get_arn(self):
        return self.get_device().arn

    def get_name(self):
        return self.get_device().name

    def get_provider(self):
        return self.get_device().provider_name

    def get_native_gates(self):
        return self.get_device().properties.paradigm.nativeGateSet

    def get_supported_gates(self):
        return self.get_device().properties.action['braket.ir.jaqcd.program'].supportedOperations

     #core device information: arn, provider info, execution window and location
    def list_properties( self):

        device = self.get_device()
        print("#############################")
        print( "Device name: ", device.name)
        print( "Device type: ", device.type)
        print( "Device arn: ", device.arn)
        print( "Device provider:", device.provider_name)
        print( "Device status:", device.status)
        print( "Device availability: ", device.is_available)
        print( "Device region: ", device.get_device_region( device.arn))

        topo = device.topology_graph
        
        if topo == None:
            print("No associated device topology")
        else:
            nx.draw_kamada_kawai(device.topology_graph, with_labels=True, font_weight="bold")


class Plotter(object) :

    def plot_binary_results( task_results,decimal = False, debug = False, title = None):

        counts = task_results.measurement_counts
        # print counts
        if debug:
            print(counts)
            
        # plot using Counter

        fig, ax = plt.subplots(1, 1)
        
        x_values = [int(x,2) for x in counts.keys()] if decimal else counts.keys()
        ax.bar(counts.keys(), counts.values())
        ax.set_xlabel('bitstrings')
        ax.set_ylabel('counts')
        ax.set_title(title)
        plt.show()

class DeviceUtils(object) :

    #shortcut to get a device without arn
    def get_device(short_id) :

        if short_id == "local":
            return LocalSimulator()
        if short_id == "sv1":
            return AwsDevice("arn:aws:braket:::device/quantum-simulator/amazon/sv1")
        if short_id == "dm1":
            return AwsDevice("arn:aws:braket:::device/quantum-simulator/amazon/dm1")
        if short_id == "tn1":
            return AwsDevice("arn:aws:braket:::device/quantum-simulator/amazon/tn1")
        if short_id == "ionq":
            return AwsDevice("arn:aws:braket:::device/qpu/ionq/ionQdevice")
        if short_id == "oqc":
            return AwsDevice('arn:aws:braket:eu-west-2::device/qpu/oqc/Lucy')
        if short_id == "rigetti":
            return AwsDevice('arn:aws:braket:us-west-1::device/qpu/rigetti/Aspen-M-2')
    