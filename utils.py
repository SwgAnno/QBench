# general imports
import matplotlib.pyplot as plt

# AWS imports: Import Braket SDK modules
from braket.circuits import Circuit, Gate, Instruction, circuit, Observable
from braket.devices import LocalSimulator
from braket.aws import AwsDevice ,AwsQuantumTask
import numpy as np

import json     

#Device graph plotting
import networkx as nx

#Simple Bridge to encapsulate Quantum Task and Aws Device information retrival
class BraketTaskScanner(object) :

    def __init__( self, qtask):

        self._task = qtask

        arn = qtask.metadata()["deviceArn"]
        self._device = AwsDevice(arn)

    def get_task(self):
        return self._task

    def get_device(self):
        return self._device    

    def get_device_arn(self):
        return self._device.arn

    def get_device_name(self):
        return self._device.name

    def get_task_status(self):
        return self.get_task().metadata()["status"] 

    def get_device_provider(self):
        return self.get_device().provider_name

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

    def get_task_results(self):
        if not self.results_available():
            print("TASK RESULT ERROR: Results not available")
            return 0

        return self.get_task().result()

    def get_circuit_source(self):
        result = self.get_task_results()

        if result :
            return result.additional_metadata.action.source

    def get_circuit_source_compiled(self):
        result = self.get_task_results()

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
        return self.get_task_status() in AwsQuantumTask.TERMINAL_STATES

    def results_available(self):
        return self.get_task_status() in AwsQuantumTask.RESULTS_READY_STATES

    #core device information: arn, provider info, execution window and location
    def list_device_properties( self):

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

    