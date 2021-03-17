import time 
import datetime
import sys
from os import path
import threading
import queue
import configparser
from urllib.request import urlopen
import PySimpleGUI as sg
import serial

DEBUG = False  #probably redundant, read from the config file
serial_list = []  
sg.theme('LightBlue2')  # can't read disabled settings text in default theme

def serial_ports():  #enumerate serial ports 
    ports = ['COM%s' % (i + 1) for i in range(256)]
    result = []
    for port in ports:
        try:
            s = serial.Serial(port)
            s.close()
            result.append(port)
            # if len(result)>1:
                # result = result+','
            # result = result+'\''+port+'\''
        except (OSError, serial.SerialException):
            pass
    return result
    
def check_config():  #called at beginning of main to verify that the config looks sane
    global DEBUG
    config = configparser.RawConfigParser()
    if path.exists('dmtalemux.ini'):
        try:
            config.read('dmtalemux.ini')
            DEBUG = config['Common'].getboolean('debug',False)
            RADIOport = config['Radio'].get('port')
            baud = config['Radio'].get('baud') 
            DMTport = config['DMT'].get('port') 
            ALEport = config['ALE'].get('port')
            if None in [RADIOport,baud,DMTport,ALEport]:
                print('dmtalemux.ini erros found.  Launching settings window...')
                settings()
        except:
            print('error found in dmtalemux.ini: ', sys.exc_info()[0])
            exit()
    else:
        if DEBUG:
            print('no dmtalemux.ini found.  Launching settings window...')
        config['Common'] = {'#debug': False,'#log': True,'minimize': True}
        config['Radio'] = {'baud': '19200','port': 'COM7'}
        config['DMT'] = {'port': 'COM15'}
        config['ALE'] = {'port': 'COM17'}
        with open('dmtalemux.ini', 'w') as configfile:
            config.write(configfile)
            configfile.close()
        settings()

def get_config(section, value):  #to avoid globals everything will have to call out to get settings
    config = configparser.RawConfigParser()
    config.read('dmtalemux.ini')
    answer = None
    try:
        answer = config[section].get(value) 
    except:
        pass
    return(answer)
   
def set_config(section,value,data):  #safely write a setting to the .ini file
    if DEBUG:
        print(section, value, data)
    config = configparser.RawConfigParser()
    config.read('dmtalemux.ini')
    config.set(section,value,data)                         
    # cfgfile = open(file_path,'w')
    with open('dmtalemux.ini','w') as configfile:
        config.write(configfile) 
    configfile.close()

def settings(): # settings() will open the .ini file, allow user edits, save .ini file
    mq.put('changing settings')
    config = configparser.RawConfigParser()
    if path.exists('dmtalemux.ini'):
        config.read('dmtalemux.ini')
        debug = config['Common'].getboolean('debug', False)
        LOGGING = config['Common'].getboolean('logging',False)
        minimize = config['Common'].getboolean('minimize',True)
        RADIOport = config['Radio'].get('port')
        baud = config['Radio'].get('baud','19200') 
        DMTport = config['DMT'].get('port') 
        ALEport = config['ALE'].get('port')
        # serial_list = serial_ports()
        
    col2_layout = [ [sg.Button('Save')],
                    [sg.Checkbox('Modem\nLogging',default=LOGGING, key="logging", change_submits = False)],
                    [sg.Checkbox('Minimize\non open',default=minimize, disabled=True, 
                         key="minim", change_submits = False)],
                    [sg.Checkbox('Log to File', disabled=True, change_submits = False)]]
    col1_layout = [
            [sg.Text('baud:',size=(14,1), justification="center"),sg.OptionMenu(['1200','2400','9600','19200','57600'], key='baud', default_value=baud)],
            [sg.Text('Radio port:',size=(14,1), justification="center"),sg.OptionMenu(serial_list, key='radio', default_value=str(RADIOport))],
            [sg.Text('MS-DMT port:',size=(14,1), justification="center"),sg.OptionMenu(serial_list, key='dmt', default_value=str(DMTport))],
            [sg.Text('MARS-ALE port:',size=(14,1), justification="center"),sg.OptionMenu(serial_list, key='ale', default_value=str(ALEport))]]
    layout = [[sg.Frame('',col1_layout, size=(110,1500)),sg.Column(col2_layout,vertical_alignment='t')]]
    #sg.change_look_and_feel('LightBlue')  #can't see disabled text in "Default" theme
    # Create the settings window
    window = sg.Window('DMT/ALE mux settings', layout)
    # Create the GUI event loop
    while True:
        event, values = window.read(timeout = 10,timeout_key = "__TIMEOUT__",close = False)
        if event == sg.WIN_CLOSED:    # catch window closing without save
            break
        if event in ('Save'):
            set_config('Common','logging',values['logging'])
            set_config('Common','minimize',values['minim'])
            set_config('Radio','baud',values['baud'])
            set_config('Radio','port',values['radio'])
            set_config('DMT','port',values['dmt'])
            set_config('ALE','port',values['ale'])

            window.close()
            mq.put('settings saved')
            break
 
def serial_handler():  # all of the "real work" happens in here
    init = 0   #we start with nothing
    while True:
        
        if init == 0:  #open the ports 
            mq.put('opening serial ports')
            baud = int(get_config('Radio','baud'))
            radio = serial.Serial(get_config('Radio','port'), baud, timeout=5)
            DMT = serial.Serial(get_config('DMT','port'),baud, timeout=5)    
            ALE = serial.Serial(get_config('ALE','port'),baud, timeout=5)
            init = 1
        reading = 0;  #initialize a variable
        if init == 1:
            if (radio.inWaiting()>0):
                reading = radio.read(radio.inWaiting())
                e = datetime.datetime.now()
                lq.put(e.strftime("%Y-%m-%d %H:%M:%S")+reading.hex(' '))
                DMT.write(reading)
                ALE.write(reading)
                if DEBUG:
                    print('..data from radio..')
            if (DMT.inWaiting()>0):
                reading = DMT.read(DMT.inWaiting())
                radio.write(reading)
                if DEBUG:
                    print('..data from DMT..')
            if (ALE.inWaiting()>0):
                reading = ALE.read(ALE.inWaiting())
                radio.write(reading)
                if DEBUG:
                    print('..data from ALE..')
        time.sleep(.001) #probably not needed with the other queue checking
        try:
            todo = sq.get(block=False,timeout=1)
            sq.task_done()
            if todo == 'DIE':
                mq.put('closing serial ports to exit')
                return
            elif todo == 'CLOSE':
                
                if DEBUG:
                    print('closing serial ports')
                init = 2
                mq.put('closing serial ports')
                radio.flushInput()
                radio.flushOutput()
                time.sleep(2)
                radio.flushInput()
                radio.flushOutput()
                radio.close()
                ALE.close()
                DMT.close()
            elif todo == 'OPEN':
                init = 0
        except queue.Empty:
            pass  # nothing to see here, move along
    
def mainwindow():  #this is the GUI
    
    buttons = []
    for i in range(1,7):  #if it's stupid but it works it isn't stupid  ;)
        buttons.append(str(get_config('Macro','m'+str(i))).split(','))
        if buttons[len(buttons)-1][0] == 'None':
            buttons.pop(len(buttons)-1)
    col3_layout = []
    print(len(buttons))
    for i in range(len(buttons)):
        button = (sg.Button(buttons[i][0],button_color=(buttons[i][1],buttons[i][2])))
        col3_layout.append(button)
    col3_layout = [col3_layout]
    
    isvis = get_config('Macro','show')
    if isvis in (None, 'False'):
        isvis = False
    # elif isvis == 'False':
        # isvis = False
    else:
        isvis = True
    
    col1_layout = [[sg.MLine(key='-ML1-',size=(80,30),auto_size_text=True)],[sg.Button('Clear',pad=((0,0),(6,6))),
                    sg.Frame('',col3_layout, border_width=0,visible=isvis, key='MACROS')]]
    col2_layout = [[sg.Button('Exit',size=(6,1),pad=((0,0),(0,1)))],[sg.Button('Macros',size=(6,1),pad=(0,0))],
                    [sg.Button('Settings',size=(6,1),pad=((0,0),(0,450)))]]
    
    layout = [[sg.Column(col1_layout),sg.Column(col2_layout)]]
    
    #start the serial stuff
    if DEBUG:
        print('start serial_handler thread')
    t = threading.Thread(target=serial_handler)
    t.start()
    if (get_config('Common','logging') == 'True'):
        if DEBUG:
            print('logging enabled')
        logging = True
    else:
        if DEBUG:
            print('logging disabled')
        logging = False
    logdata = None
    messagedata = None
    # Create the main window
    location = get_config('Common','location')
    if not location:
        locx = None
        locy = None
    else:
        locx,locy = location.split(',') 
    window = sg.Window('DMT/ALE mux', layout,resizable=True, auto_size_text=True,
                   auto_size_buttons=True, location=(locx,locy))
    # Create the GUI event loop
    while True:
        event, values = window.read(timeout = 10,timeout_key = "__TIMEOUT__",close = False)
        if event in (sg.WIN_CLOSED,'Exit'):    # catch window closing without save
            sq.put('DIE')  #tell serial_handler to shut down
            t.join()  # wait for the serial_handler thread to end
            break
        elif event == 'Settings':
            sq.put('CLOSE') #release serial ports 
            # while sq.qsize:
                # time.sleep(.5)
            # time.sleep(1)
            # s = threading.Thread(target=settings)
            # s.start()
            settings()
            if DEBUG:
                print('restarting serial_handler')
            
            sq.put('OPEN')  #tell serial_handler to reload config and open ports
            if (get_config('Common','logging') == 'True'):
                if DEBUG:
                    print('logging enabled')
                logging = True
            else:
                if DEBUG:
                    print('logging disabled')
                logging = False
        elif event == 'Clear':
            window['-ML1-'].update('')
        elif event == 'Macros':
            if isvis:
                window['MACROS'].update(visible=False)
                isvis = 0
            else:
                window['MACROS'].update(visible=True)
                isvis = 1
        else:
            for i in range(len(buttons)):
                if event == buttons[i][0]:
                    window['-ML1-'].print('Event:'+buttons[i][0])
        try:
            logdata = lq.get(block=False,timeout=1)
            lq.task_done()
        except queue.Empty:
            pass
        if logging and logdata != None:
            window['-ML1-'].print(logdata)  
        try:
            messagedata = mq.get(block=False,timeout=1)
            mq.task_done()
        except queue.Empty:
            pass
        if messagedata != None:
            window['-ML1-'].print(messagedata)
        logdata = None
        messagedata = None
    (locx, locy) = window.current_location()
    set_config('Common','location',str(locx)+','+str(locy))
    exit()    

#__main__    
try:
    print('loading dmtalemux...')
    serial_list = serial_ports()
    lq = queue.Queue()  # modem log queue
    sq = queue.Queue()  # serial_handler control
    mq = queue.Queue()  # all the non-log console messages.
    
    check_config()
    if (get_config('Common','debug') == 'True'):
        DEBUG = True
    
    mainwindow()
    
    print('closing down...')

except KeyboardInterrupt:  #  catch control-l in the console window
    print('exiting...')
    sq.put('DIE')   #let the serial_handler know we are closing
    sys.exit()
