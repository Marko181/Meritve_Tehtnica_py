# .\avms\Scripts\activate
# deactivate

import serial
import serial.serialutil
import serial.tools.list_ports
import asyncio
import atexit
import time
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import numpy as np
from state_mng import ser, prev_stanje, zacetni_cas, vmesni_cas, koncni_cas, teza_graf, cas_graf, cas, serial_options
from nicegui import ui


######################################################################################################
##### FUNCTION DEFINITIONS ###########################################################################
######################################################################################################


# Scan serial ports
def scan_serial():
    global serial_options
    ports = serial.tools.list_ports.comports()
    serial_options = {index + 1: port.device for index, port in enumerate(ports)}
    print("Ports: ", serial_options)
    # serial_options se mora vpisati spodaj v spremenljivko za dejanski selector

# Check if the connection is established
def connect_serial(selected_port):
    global ser
    if ser is None or not ser.is_open:
        print("Serial Connection Not Open")
        try:
            print("Connecting...")
            ser = serial.Serial(
            port=selected_port,  # Adjust according to the port you are using
            baudrate=9600,  # Transmission rate, adjust according to device requirements
            timeout=1  # Timeout for reading from the serial connection
            )
            print("Connected")
            update_error_msg_visibility()
            error_message.text = ''
        except serial.serialutil.SerialException as e:
            print("Failed to open", e)
            error_message.text = "Connection with serial failed! Try another port!"
            update_error_msg_visibility()
    else:
        print("Serial Connected")
        update_error_msg_visibility()

# Function for hiding and showing error message
def update_error_msg_visibility():
    if ser is None or not ser.is_open:
        row.visible = True
        row1.visible = True
        b1.disable()
        b2.disable()
        b3.disable()
        b4.disable()
        b5.disable()
        b6.disable()
        b7.disable()
        b8.disable()
    else:
        row.visible = False
        row1.visible = False
        b1.enable()
        b2.enable()
        b3.enable()
        b4.enable()
        b5.enable()
        b6.enable()
        b7.enable()
        b8.enable()

# Reconnect serial
def reconnect_serial():
    selected_value = com_select.value
    selected_com = serial_options[selected_value]

    connect_serial(selected_com)

# Function to update the time
async def update_time(ura):
    while True:
        ura.text = datetime.now().strftime('%H:%M:%S')
        await asyncio.sleep(1)  # Wait for 1 second before updating again

def timer_callback():
    asyncio.create_task(update_time(ura))

# Function to get weather data
def get_weather():
    # URL of the XML file
    url = 'https://meteo.arso.gov.si/uploads/probase/www/observ/surface/text/sl/observationAms_LJUBL-ANA_BEZIGRAD_latest.xml'
    #url = ''

    # Fetch the XML file
    try:
        response_arso = requests.get(url)

        # Check if the request was successful
        if response_arso.status_code == 200:
            # Parse the XML content
            root = ET.fromstring(response_arso.content)
            
            # Extracting specific data based on the tag names provided
            temperature = root.find('.//t')
            humidity = root.find('.//rh')
            air_pressure = root.find('.//p')
            
            # Print the results
            # Check if the elements exist and print their text
            if temperature is not None:
                temperatura.text = temperature.text + " °C"
            else:
                temperatura.text = "NaN"

            if humidity is not None:
                vlaga.text = humidity.text + " %"
            else:
                vlaga.text = "NaN"

            if air_pressure is not None:
                pritisk.text = air_pressure.text + " hPa"
            else:
                pritisk.text = "NaN"
        else:
            print("Failed to retrieve the XML file. Status code:", response_arso.status_code)
    except Exception as e:
        print("Error in accessing weather data: ", e)

# Function to wait for response from serial
async def wait_response(ser):
    while True:
        if ser.in_waiting > 0:
            response = ser.readline().decode().strip()  # Read the device's response
            #response = ser.readline().decode(errors='ignore').strip() # Read the device's response
            if response:
                return response
        await asyncio.sleep(0.1)  # Wait for the device to respond

# Function for calculating time of measurment
async def cas_umeritve(response):
    global prev_stanje
    global zacetni_cas
    global vmesni_cas
    global koncni_cas
    global teza_graf
    global cas_graf
    global cas
    stanje_tehnice = response[2]

    try:
        if stanje_tehnice == 'D' and prev_stanje == 'S' and prev_stanje is not None:
            zacetni_cas = time.time()
            koncni_cas = None
            cas = 0.0
            teza_graf = []
            cas_graf = []
            ax.clear
        elif stanje_tehnice == 'D':
            vmesni_cas = time.time()
            cas = vmesni_cas - zacetni_cas
        elif stanje_tehnice == 'S' and prev_stanje == 'D' and prev_stanje is not None:
            koncni_cas = time.time()
        elif zacetni_cas is not None and koncni_cas is not None:
            cas =  koncni_cas - zacetni_cas
        else:
            cas = 0.0

        if cas < 0.0:
            cas = 0.0

        teza_graf.append(float(response[4:-2].strip()))
        cas_graf.append(cas)

        # print(teza_graf)
        # print(cas_graf)

        draw_plot()

    except Exception as e:
        print('Exception cas umeritve: ', e)
        pass
    prev_stanje = stanje_tehnice

    # if zacetni_cas is not None and koncni_cas is not None:
    #     raise Exception("Stop continous read")

    return cas

# Function to draw a plot
def draw_plot():
    with fig:
        ax.clear()
        x = cas_graf
        y = teza_graf
        # x = [0.0, 0.11226630210876465, 0.2956056594848633, 0.4954662322998047, 0.5893375873565674, 0.7954599857330322, 0.9142954349517822, 1.096367359161377, 1.2964608669281006, 1.4016785621643066, 1.6056127548217773, 1.705721139907837, 1.8956196308135986, 2.010911226272583, 2.2155606746673584]
        # y = [0.01, 0.37, 25.29, 101.82, 165.93, 182.71, 196.42, 199.38, 199.76, 199.97, 199.99, 199.99, 199.99, 199.99, 199.99]
        ax.plot(x, y, '-')
        ax.set_title('Time to measure stable weight', fontsize=20)
        ax.set_xlabel('Measuring Time [s]', fontsize=14)
        ax.set_ylabel('Weight [g]', fontsize=14)
    fig.canvas.draw()

# Function to send a command and handle response asynchronously
async def send_command(command):
    global continue_reading
    global command_flag # Globalna command spremenljivka
    try:
        input_field.set_text(command)
        ser.write((command + '\r\n').encode())  # Send the command
        if command == 'SIR' or command == 'SR':# or command == 'ST':
            if command == 'SIR':
                command_flag = True
            else:
                command_flag = False
            
            continue_reading = True
            asyncio.create_task(read_continuously())
        else:
            continue_reading = False
            # Reset serial input buffer
            ser.reset_input_buffer()
            response = await wait_response(ser)
            #print(response)
            if response == 'I4 A "1116241108"':
                output_field.text = "Reset complete!"
                error_message.text = ''
                cas_umerjanja_field.text = ''
            elif len(response) < 17:
                output_field.text = response
                error_message.text = ''
                cas_umerjanja_field.text = ''
            else:
                error_message.text = response
                output_field.text = ''
                ref_weight_label.text = ''
                num_objects_label.text = ''
    except Exception as e:
        error_message.text = "Error sending command: " + str(e)

# Function to read continously from serial
async def read_continuously():
    global continue_reading
    global command_flag
    try:
        while continue_reading:
            #if response:  # Only update if there is a response
            response = await wait_response(ser)
            #print(response)
            if len(response) < 17:
                output_field.text = response
                error_message.text = ''
            else:
                error_message.text = response
                output_field.text = ''

            if command_flag:
                t_umiritve = await cas_umeritve(response)
                t_umiritve_str = str(round(t_umiritve,3))
                cas_umerjanja_field.text = t_umiritve_str + ' s'
                ref_weight_label.text = ''
                num_objects_label.text = ''
    except Exception as e:
        error_message.text = "Error reading continuously: " + str(e)
        continue_reading = False
        command_flag = False
        #draw_plot()

async def set_ref_weight():
    global ref_weight
    output_field.text = ''

    # Send command to get current stable weight
    await send_command('S')

    measured_weight_ref = output_field.text[4:-2].strip()
    #measured_weight_ref = "20.0"

    ref_weight = float(measured_weight_ref)/float(num_of_ref_weights.value)
    ref_weight_label.text = 'Reference weight: ' + str(round(ref_weight,3)) + ' g'

async def count_objects():
    # Set output field to empty
    output_field.text = ''

    # Send command to get current stable weight
    await send_command('S')

    measured_weight = output_field.text[4:-2].strip()
    #measured_weight = "50.0"

    # Calculate number of objects
    num_objects = float(measured_weight)/ref_weight
    num_objects_label.text = str(round(num_objects))


######################################################################################################
##### GUI CODE #######################################################################################
######################################################################################################


# Define styles
label_style = 'font-size: 20px; font-weight: bold;'
button_style1 = 'font-size: 20px; padding-top:5px; padding-bottom:5px; font-weight:bold; background-color: rgb(50, 205, 50) !important;'
button_style2 = 'font-size: 20px; padding-top:5px; padding-bottom:5px; font-weight:bold; background-color: rgb(255, 191, 0) !important;'
button_style3 = 'font-size: 20px; padding-top:5px; padding-bottom:5px; font-weight:bold; background-color: rgb(0, 123, 255) !important;'
button_style4 = 'font-size: 20px; padding-top:5px; padding-bottom:5px; font-weight:bold; background-color: rgb(128, 0, 128) !important;'
row_style = 'padding-top:5px; padding-bottom:5px;'

scan_serial()

# Title
title = ui.label('Scale GUI').style('font-size: 50px; text-align: center; width: 100%; font-weight:bold;')

# split screen in two columns (one for buttons and one for plot)
with ui.row():
    with ui.column().style('padding-left:20px'):

        # A row for the date and time display
        with ui.row().style('padding-top:5px; padding-bottom:5px;'):
            ui.label('Time:').style('font-size: 20px; font-weight:bold;')
            ura = ui.label(datetime.now().strftime('%H:%M:%S')).style('font-size: 20px;')
            ui.label('Date:').style('font-size: 20px; font-weight:bold;')
            datum = ui.label(datetime.now().strftime('%d. %m. %Y')).style('font-size: 20px;')

        # A row for sensor readings with icons placed next to the values
        with ui.row().style(row_style):
            
            # Temperature
            with ui.column():
                ui.label('Temperature:').style(label_style)
                with ui.row().classes('items-center').style(row_style):
                    ui.icon('device_thermostat', color='primary').classes('text-5xl mr-2')
                    temperatura = ui.label('').style('font-size: 20px;')
                    
            # Humidity        
            with ui.column().style('padding-left:70px'):
                ui.label('Humidity:').style(label_style)
                with ui.row().classes('items-center').style(row_style):
                    ui.icon('water_drop', color='primary').classes('text-5xl mr-2')
                    vlaga = ui.label('').style('font-size: 20px;')

            # Pressure        
            with ui.column().style('padding-left:70px'):
                ui.label('Pressure:').style(label_style)
                with ui.row().classes('items-center').style(row_style):
                    ui.icon('speed', color='primary').classes('text-5xl mr-2')
                    pritisk = ui.label('').style('font-size: 20px;')

        # A row for buttons in two columns
        with ui.row().style(row_style):
            with ui.column():
                b1 = ui.button('Get Stable Weight', on_click=lambda: send_command('S')).style(button_style1) # RGB: (50, 205, 50)
                b2 = ui.button('Get Weight Now', on_click=lambda: send_command('SI')).style(button_style1)   # RGB: (50, 205, 50)
                b3 = ui.button('Zero Scale', on_click=lambda: send_command('Z')).style(button_style3)        # RGB: (0, 123, 255)
                
                ui.label('Command Sent:').style('font-size: 20px; padding-top:5px; font-weight: bold;')
                input_field = ui.label('').style('font-size: 20px;')

            with ui.column().style('padding-left:20px;'):
                b4 = ui.button('Get Weight Live', on_click=lambda: send_command('SIR')).style(button_style2) # RGB for Orange: (255, 165, 0) or RGB for Amber: (255, 191, 0)  
                #b4 = ui.button('Get Weight Live', on_click=lambda: draw_plot()).style(button_style2)
                b5 = ui.button('Get Stable Weight Live', on_click=lambda: send_command('SR')).style(button_style2)  # RGB for Orange: (255, 165, 0) or RGB for Amber: (255, 191, 0)
                #b6 = ui.button('Get Weight on Key Press', on_click=lambda: send_command('ST')).style(button_style4) # RGB for Purple: (128, 0, 128) or RGB for Light Blue: (173, 216, 230)
                b6 = ui.button('Reset', on_click=lambda: send_command('@')).style(button_style4)

                ui.label('Measurement:').style('font-size: 25px; padding-top:5px; font-weight: bold;')
                output_field = ui.label('').style('font-size: 30px; font-weight: bold;')
            
        with ui.row():
            with ui.column():
                ui.label('Measuring time:').style('font-size: 25px; font-weight: bold;')
            with ui.column(): 
                cas_umerjanja_field = ui.label('').style('font-size: 30px; font-weight: bold;')

    # Error message
    with ui.column():
        with ui.row():
            with ui.row().style('align-items: center;'):
                # Error message
                with ui.column().style('padding-left:20px'):
                    error_message = ui.label('').style('padding-left:20px; font-size: 20px; background-color:yellow')
                # Available port options
                with ui.column().style('padding-left:20px') as row:
                    #serial_options = {1: 'COM1', 2: 'COM2', 3: 'COM3'}
                    com_select = ui.select(serial_options, value=1)
                # Reconnect button
                with ui.column().style('padding-left:20px') as row1:
                    retry_ser_con = ui.button('Retry', on_click=lambda: reconnect_serial()).style('background-color:yellow !important; color: black !important;')
        # Plot
        with ui.row():
            with ui.matplotlib(figsize=(9, 5)).figure as fig:
                ax = fig.gca()
                ax.set_title('Time to measure stable weight', fontsize=20)
                ax.set_xlabel('Measuring Time [s]', fontsize=14)
                ax.set_ylabel('Weight [g]', fontsize=14)

    with ui.row().style('align-items: center; padding-left:20px;'):
            with ui.column():
                ui.label('Number of reference objects: ').style('font-size: 20px; font-weight: bold;')
            with ui.column():
                num_of_ref_weights = ui.number(value=1, min=1).style('width:100px; font-size: 18px;')
            with ui.column():
                b7 = ui.button('Get ref weight', on_click=lambda: set_ref_weight()).style('font-size: 18px; padding-bottom:5px; font-weight:bold; align-items: center;')
            with ui.column():
                ref_weight_label = ui.label('').style('font-size: 20px; font-weight: bold;')
            with ui.column().style('padding-left:5px; padding-right:5px'):
                b8 = ui.button('Count objects', on_click=lambda: count_objects()).style('font-size: 18px; padding-bottom:5px; font-weight:bold; align-items: center;')
            with ui.column().style('padding-left:20px'):
                ui.label('Counted objects: ').style('font-size: 20px; font-weight: bold;')
            with ui.column():
                num_objects_label = ui.label('').style('font-size: 25px; font-weight: bold;')

connect_serial('COM1')

update_error_msg_visibility()

ui.timer(1, timer_callback)

get_weather()

# Function to close RS232 connection on shutdown
def cleanup():
    if ser.is_open:
        ser.close()
        print('Serial connection closed.')

atexit.register(cleanup)

ui.run(reload=False, port=8081)  # Specify the port for the NiceGUI server
