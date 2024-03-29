from dynamixel_sdk import *                    # Uses Dynamixel SDK library   
from dynamixel_control.dxl import Dxl
from time import sleep
import os
import pickle as pkl
import numpy as np
from math import pi
import threading 
import time
# To tune PID https://www.youtube.com/watch?v=msWlMyx8Nrw&ab_channel=ROBOTISOpenSourceTeam

class Dynamixel:
    """
    How to use this class:
    See the example in the if statement at the bottom of the file

    Shift - will shift only when specified!!
    
    
    """

    def __init__(self, port = '/dev/ttyUSB0'): 
        self.DEVICENAME = port
        self.PROTOCOL_VERSION = 2.0
        self.BAUDRATE = 57600

        self.portHandler = PortHandler(self.DEVICENAME)
        self.event = threading.Event()

        # Create flag for first bulk read
        self.first_bulk_read = True
        self.shift_values = False
        
        # Initialize PacketHandler instance
        # Set the protocol version
        # Get methods and members of Protocol1PacketHandler or Protocol2PacketHandler
        self.packetHandler = PacketHandler(self.PROTOCOL_VERSION)

        # Initialize GroupBulkWrite instance
        self.groupBulkWrite = GroupBulkWrite(self.portHandler, self.packetHandler)

        # Initialize GroupBulkRead instace for Present Position
        self.groupBulkRead = GroupBulkRead(self.portHandler, self.packetHandler)
        self.groupBulkRead_torque = GroupBulkRead(self.portHandler, self.packetHandler)

        # Open port
        if self.portHandler.openPort():
            print("Succeeded to open the port")
        else:
            print("Failed to open the port")
            quit()

        # Set port baudrate
        if self.portHandler.setBaudRate(self.BAUDRATE):
            print("Succeeded to change the baudrate")
        else:
            print("Failed to change the baudrate")
            quit()

        # Create a dictionary of each Dynamixel object
        # key: id_number; value: Dxl object
        self.dxls = {}

    def reboot_dynamixel(self):
        # Try reboot
        # Dynamixel LED will flicker while it reboots
        for id in self.dxls.keys():
            self.packetHandler.reboot(self.portHandler, id)
        
        for id in self.dxls.keys():
            self.enable_torque(id, True)

        print("All Dynamixels rebooted and on.")



    def add_dynamixel(self, type = "XL-320", ID_number = 0, calibration = [0, 511, 1023], shift = 0):
        """ Creates a Dxl object and adds it to our dictionary based on the parameters passed in.

        Args:
            dyn_dict (dict): Dictionary of relavent Dynamixel settings
        Returns:
            none
        """
        dynamixel_dict = {"type": type,
                          "ID_number": ID_number,
                          "calibration": calibration,
                          "shift": shift}

        # Create a Dxl object and add it to our dictionary
        self.dxls[ID_number] = Dxl(dynamixel_dict)

    ## Here are the new functions!!!
    def send_parameters(self):
        """ Sends parameters in groupBulkWrite to the Dynamixels, then erases the paramaters

        Args:
            none
        Returns:
            none
        """

        # Enable Dynamixel Torque
        dxl_comm_result = self.groupBulkWrite.txPacket()
        if dxl_comm_result != COMM_SUCCESS:
            print("%s" % self.packetHandler.getTxRxResult(dxl_comm_result))

       
        # Clear bulkwrite parameter storage
        self.groupBulkWrite.clearParam()

    def add_parameter(self, id = 0, address = 100, byte_length = 1, value = 0):
        """ Adds parameter to groupBulkWrite storage. Chooses correct data type based on motor type and length of parameter. Note, only one parameter per motor at a time is allowed.

        Args:
            id (int): ID number of Dynamixel
            address (int): Control table address of paramater for the dynamixel
                (default is 0)
            byte_length (int): Number of bytes the paramater value should be
                (default is 1)
            value (int): Actual paramter value being passed to the dybnamixel
                (default is 0)
        Returns:
            none
        """

        # Get the value in the correct format based on the length in bytes
        if byte_length == 1:
            value_out = [value]
        elif byte_length == 2:
            value_out = [DXL_LOBYTE(value), DXL_HIBYTE(value)]
        elif byte_length == 4:
            value_out = [DXL_LOBYTE(DXL_LOWORD(value)), DXL_HIBYTE(DXL_LOWORD(value)), DXL_LOBYTE(DXL_HIWORD(value)), DXL_HIBYTE(DXL_HIWORD(value))]
        
        # Add the parameter
        dxl_addparam_result = self.groupBulkWrite.addParam(id, address, byte_length, value_out) 
        if dxl_addparam_result != True:
                print("[ID:%03d] groupBulkWrite addparam failed" % id)
                quit()
    
    def set_speed(self, speed = 100):
        """ Updates the max speed/velocity profile for all attached dynamixels

        Args:
            id (speed): The new speed
                (default is 100)
        Returns:
            none
        """
        for id in self.dxls.keys():
            # Add parameters for all Dynamixels
            self.add_parameter(id, self.dxls[id].dxl_params["ADDR_velocity_cap"], self.dxls[id].dxl_params["LEN_velocity_cap"], speed)

        # Send to motors
        self.send_parameters()

    def enable_torque(self, id: int, enable: bool = True):
        """ Enables or disables torque for one Dynamixel.

        Args:
            id (int): ID number of Dynamixel
            enable (boot): Enable torque (True) or disable torque (False)
                (default is True)
        Returns:
            none
        """

        if enable == True:
            value = 1
        else:
            value = 0

        self.add_parameter(id, self.dxls[id].dxl_params["ADDR_torque_enable"], self.dxls[id].dxl_params["LEN_torque_enable"], value)

        # Send to motor
        self.send_parameters()
        
    def update_PID(self, P: int = 36, I: int = 0, D: int = 0):
        """ Updates the PID constants for all Dynamixels 

        Args:
            P (int): Proportional constant
            I (int): Integral constant
            D (int): Derivative constant
        
        Returns:
            none
        """

        # Loop through all Dxls and update the P value
        for id in self.dxls.keys():
            self.add_parameter(id, self.dxls[id].dxl_params["ADDR_P_position"], self.dxls[id].dxl_params["LEN_PID_position"], P)
                # Send to motors
        self.send_parameters()

        # Loop through all Dxls and update the I value
        for id in self.dxls.keys():
            self.add_parameter(id, self.dxls[id].dxl_params["ADDR_I_position"], self.dxls[id].dxl_params["LEN_PID_position"], I)
                # Send to motors
        self.send_parameters()

                # Loop through all Dxls and update the D value
        for id in self.dxls.keys():
            self.add_parameter(id, self.dxls[id].dxl_params["ADDR_D_position"], self.dxls[id].dxl_params["LEN_PID_position"], D)
                # Send to motors
        self.send_parameters()
            
    def send_goal(self):
        """ Writes goal positions to all Dynamixels based on goal position stored in each Dxl object.

        Args:
            none
        
        Returns:
            none
        
        """

        # Loop through all Dxls
        for id in self.dxls.keys():
            self.add_parameter(id, self.dxls[id].dxl_params["ADDR_goal_position"], self.dxls[id].dxl_params["LEN_goal_position"], self.dxls[id].goal_position)
            
        self.send_parameters()

    def update_goal(self, id: int, new_goal: int):
        """ Updates the goal position stored in the object for 1 dynamixel

        Args:
            id (int): ID number of Dynamixel to update
            new_goal (int): New goal position from 0 to 1023
        Returns:
            none
        
        """

        # If true, send the shifted values (usually just to the initial position)
        if self.shift_values:
            self.dxls[id].goal_position = new_goal + self.dxls[id].shift 
        else:
            self.dxls[id].goal_position = new_goal

        # If inside/outside minimum bound update it to be the bound
        if self.dxls[id].goal_position < self.dxls[id].min_bound:
            self.dxls[id].goal_position = self.dxls[id].min_bound
        elif self.dxls[id].goal_position > self.dxls[id].max_bound:
            self.dxls[id].goal_position = self.dxls[id].max_bound


    def setup_all(self):
        """ "Starts" all Dynamixels - this enables the torque and sets up the position read parameter

        Args:
            none
        Returns:
            none
        """

        # Loop through the Dynamixels
        for id in self.dxls.keys():
            #  Enable torque for all Dyanmixels
  
            self.enable_torque(id, True)


            # Setup parameter to read dynamixel position
            # Add parameter storage for Dynamixel present position
            dxl_addparam_result = self.groupBulkRead.addParam(id, self.dxls[id].dxl_params["ADDR_present_position"], self.dxls[id].dxl_params["LEN_present_position"])
            if dxl_addparam_result != True:
                print("[ID:%03d] groupBulkRead addparam failed" % id)
                quit()
            dxl_addparam_result = self.groupBulkRead_torque.addParam(id, self.dxls[id].dxl_params["ADDR_present_torque"], self.dxls[id].dxl_params["LEN_present_torque"])
            if dxl_addparam_result != True:
                print("[ID:%03d] groupBulkRead addparam failed" % id)
                quit()

        self.groupBulkRead.rxPacket()
        self.groupBulkRead_torque.rxPacket()
        sleep(1)
        self.first_bulk_read = False
    
    def read_pos_torque(self):
        # Read from the Dynamixels
        self.groupBulkRead.txRxPacket()
        self.groupBulkRead_torque.txRxPacket()
        pos_array = []
        torque_array = []
        for id in self.dxls.keys():
            # Saves position read in each Dxl object
            temp = self.groupBulkRead.getData(id, self.dxls[id].dxl_params["ADDR_present_position"], self.dxls[id].dxl_params["LEN_present_position"])
            self.dxls[id].read_position_rad = self.convert_pos_to_rad(temp - self.dxls[id].center_pos)
            pos_array.append(self.dxls[id].read_position_rad)
            self.dxls[id].current_torque = self.groupBulkRead_torque.getData(id, 126, 2)
            torque_array.append(self.dxls[id].current_torque)

        return pos_array, torque_array


    def bulk_read_pos(self):
        """ Check and read current positions from each Dynamixel

        Args:
            none
        
        Returns:
            none        
        """

        # Read from the Dynamixels
        self.groupBulkRead.txRxPacket()
        # Must set to 2 bytes otherwise errors!!

        for id in self.dxls.keys():
            # Saves position read in each Dxl object
            self.dxls[id].read_position = self.groupBulkRead.getData(id, self.dxls[id].dxl_params["ADDR_present_position"], self.dxls[id].dxl_params["LEN_present_position"])
            
            self.dxls[id].read_position_m = self.convert_pos_to_rad(self.dxls[id].read_position - self.dxls[id].center_pos)
  
    
    def get_position(self, id: int):
        return self.dxls[id].read_position

    
    def bulk_read_torque(self):
        """ NOT IS USE
        Check and read current positions from each Dynamixel

        Args:
            none
        
        Returns:
            none
        
        """

        # TODO: not sure if this is actually working...
        for id in self.dxls.keys():
            # Add parameter storage for Dynamixel present position
            dxl_addparam_result = self.groupBulkRead.addParam(id, self.dxls[id].CURRENT_TORQUE_INDEX, self.dxls[id].LEN_CURRENT_TORQUE_INDEX)
            if dxl_addparam_result != True:
                print("[ID:%03d] groupBulkRead addparam failed" % id)
                quit()
        
        self.groupBulkRead.txRxPacket()
        
        for id in self.dxls.keys():

            # Saves torque read in each object
            self.dxls[id].current_torque = self.groupBulkRead.getData(id, self.dxls[id].CURRENT_TORQUE_INDEX, self.dxls[id].LEN_CURRENT_TORQUE_INDEX)
            #print(f"Current torque: {self.dxls[id].current_torque}")
            
        self.groupBulkRead.clearParam()

    

    
    
    
    

        
    def end_program(self):
        """ Turns off Dynamixel torque and closes the port. Run this upon exit/program end.

        Args:
            none
        Returns:
            none
        
        """

        # Disable torque
        for id in self.dxls.keys():
            self.enable_torque(id, False)

        self.portHandler.closePort()  

    def load_pickle(self, file_location="Open_Loop_Data", file_name="angles_N.pkl") -> int:
        """ Open and load in the radian values (relative positions) from the pickle file. Convert them to positions from 0 to 1023 (how the Dynamixel XL-320 uses them). Updates the joint angles lists.

        Args:
            file_location (string): Path to folder where the pickle is saved
                (default is "/Open_Loop_Data")
            file_name (string): Name of pickle file
                (default is "angles_N.pkl")

        Returns:
            none
        """
        # TODO: Add try except here for paths
        path_to = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
        # print("PATH TO", os.path.dirname(path_to)) This backs us up one directory
        file_path = os.path.join(path_to, file_location, file_name)
      
        with open(file_path, 'rb') as f:
            self.data = pkl.load(f)


        return len(self.data)

        for id in self.dxls.keys():
            name = "joint_" + str(id+1)
            self.dxls[id].joint_angles_pickle = self.convert_rad_to_pos(data[name])

        pickle_length = len(self.dxls[id].joint_angles_pickle)

        return pickle_length

    def convert_rad_to_pos(self, rad: float) -> int:
        """ Converts from radians to positions from 0 to 1023.

        Args:
            rad (float): Position value in radians
        Returns:
            pos (int): Position in range of 0 to 1023
        """

        if self.dxls[0].type == "XL-320":
        
        # XL-320 is 1023 to 300 degrees
            # .2932 degrees per step
            # Convert to degrees
            deg = np.multiply(rad, (180/pi))
            
            # Pos is deviation from center (0 degrees), defined in init
            pos = np.multiply(deg, (1023/300))
            pos = pos.astype(int)
        
        elif self.dxls[0].type == "XL-330":
            deg = np.multiply(rad, (180/pi))
            # Pos is deviation from center (0 degrees), defined in init
            pos = np.multiply(deg, (1025/90))
            pos = pos.astype(int)
        

        return pos

    def convert_pos_to_rad(self, pos: int) -> float:
        if self.dxls[0].type == "XL-320":
            pos = float(pos)
            deg = np.multiply(pos, (300.0/1023.0))

            rad = np.multiply(deg, (pi/180.0))
        elif self.dxls[0].type == "XL-330":
            pos = float(pos)
            deg = np.multiply(pos, (90.0/1025.0))
            rad = np.multiply(deg, (pi/180.0))

        return rad

    def map_pickle(self, i: int):
        """ Convert from relative to absolute positions based on the calibration. Updates global goal position variable.

        Args:
            i (int): Index of the list to convert
        Returns:
            none
        """

        id_counter = 1
        # Set the positions in terms of actual calibrated motor positions
        for id in self.dxls.keys():
        
            self.dxls[id].goal_position = self.dxls[id].center_pos + self.convert_rad_to_pos(self.data[i]["joint_" + str(id_counter)])
            id_counter += 1




    def replay_pickle_data(self, file_location="Open_Loop_Data", file_name="angles_N.pkl", delay_between_steps: float = .01):
            
        # Get our pickle data
        pickle_length = self.load_pickle(file_location, file_name)


        #self.map_pickle(0)
        #self.send_goal()
        #input("Press Enter to continue to next step.")
        self.skipp = False
        for i in range(pickle_length):
            if self.skipp == True:
                self.skipp = False
                continue
            #if self.event.is_set():
            #    break
            self.map_pickle(i)
            self.send_goal()
            sleep(delay_between_steps)
            #self.bulk_read_pos()
            self.skipp = True
            #self.bulk_read_pos()

        

    

    def go_to_initial_position(self, file_location="actual_trajectories_2v2", file_name="N_2v2_1.1_1.1_1.1_1.1.pkl"):
        #try: 
        self.go_to_center()
        sleep(2)
        self.flag = True
        pickle_length = self.load_pickle(file_location, file_name)
        self.map_pickle(0)
        self.send_goal()
        sleep(1)

        #except:
            #print("ahhh")
            #self.end_program()

    def go_to_center(self):
        """ Sends all connected Dynamixels to their center position as specified in the calibration.

        Args:
            none
        Returns:
            none
        """
        
        for id in self.dxls.keys():
            self.update_goal(id, self.dxls[id].center_pos)
            
        self.send_goal()

    def go_to_position_all(self, target):
        # Moves all connected motors to a target
        # Input is a list the length of the number of motors, in the order they were added
        # Input is in radians
        for i, id in enumerate(self.dxls.keys()):
            self.update_goal(id, self.dxls[id].center_pos + self.convert_rad_to_pos(target[i]))
        self.send_goal()

if __name__ == "__main__":
    Dynamixel_control = Dynamixel()
    # For XL330
    if True:
        Dynamixel_control.add_dynamixel(type="XL-330", ID_number=0, calibration=[1023,2048,3073], shift = 0) # Negative on left side was -25
        Dynamixel_control.add_dynamixel(type="XL-330", ID_number=1, calibration=[1023,2048,3073], shift = 0)
        Dynamixel_control.add_dynamixel(type="XL-330", ID_number=2, calibration=[1023,2048,3073], shift = 0) # Positive on right side was 25
        Dynamixel_control.add_dynamixel(type="XL-330", ID_number=3, calibration=[1023,2048,3073], shift = 0)
        #4565, 545, 450, 553
        Dynamixel_control.set_speed(100)
        Dynamixel_control.setup_all()
        Dynamixel_control.update_PID(1000,400,2000)
        sleep(1)
        
        
        #Dynamixel_control.update_speed(400)
        #Dynamixel_control.test_write()
        #input("press enter to continue")
        #Dynamixel_control.update_speed(100)
    #Dynamixel_control.go_to_center()
    sleep(1)
    print("Speed done")
    # Dynamixel_control.go_to_position_all([.1, .04, -.05, -.01])
    sleep(.75)
    # Dynamixel_control.bulk_read_pos()
    # sleep(1)
    # last_reading = time.time()
    # while True:
        
    # Dynamixel_control.read_pos_torque()
    #     this_reading = time.time()
    #     print(this_reading-last_reading)
    #     last_reading = this_reading
    # sleep(100)
        #Dynamixel

    try:
        Dynamixel_control.go_to_initial_position(file_location = "Open_Loop_Data/2v2_50.50_50.50_1.1_63",file_name="SW_2v2_50.50_50.50_1.1_63.pkl")
        print(Dynamixel_control.read_pos_torque())
        sleep(10)
        #Dynamixel_control.update_speed(1000)
        Dynamixel_control.set_speed(25)
        print("Speed done")
        input("Press enter")
        
        Dynamixel_control.replay_pickle_data(file_location = "Open_Loop_Data/2v2_50.50_50.50_1.1_63",file_name="SW_2v2_50.50_50.50_1.1_63.pkl", delay_between_steps = .01)
    except:
        Dynamixel_control.reboot_dynamixel()
        
        
    Dynamixel_control.end_program()
        