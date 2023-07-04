import machine
import ssd1306
import time
import ujson
from machine import UART

# Initialize I2C pins
i2c = machine.I2C(0, scl=machine.Pin(1), sda=machine.Pin(0))

# Initialize UART communication with the GSM module
uart = machine.UART(1, baudrate=115200, tx=machine.Pin(4), rx=machine.Pin(5))

# Initialize OLED display
oled_width = 128
oled_height = 64
oled = ssd1306.SSD1306_I2C(oled_width, oled_height, i2c)

# Clear display
oled.fill(0)
oled.show()

# Set button pin
button1_pin = machine.Pin(15, machine.Pin.IN, machine.Pin.PULL_UP)
button2_pin = machine.Pin(14, machine.Pin.IN, machine.Pin.PULL_UP)

# Initial button state to not pressed
button1_pressed = False
button2_pressed = False

# Set the GSM module text mode
time.sleep(1)
uart.write("AT+CMGF=1\r\n".encode())
time.sleep(1)

# enable incoming messages
uart.write("AT+CNMI=2,2,0,0,0\r\n".encode())
time.sleep(1)

# Extract phone number from SMS message
def extract_phone_number(message, update_keyword):
    start_index = message.find(update_keyword)
    end_index = message.find("\r\n", start_index)
    return message[start_index:end_index]

# Store phone number permanently on board
def store_phone_number(phone_number_index, phone_number):
    data = {f"phone_number_{phone_number_index}": phone_number}
    with open(f"phone_number.json", "w") as f:
        f.write(ujson.dumps(data))        
        
# Load the phone number from the JSON file
def load_phone_number(phone_number_index):
    with open(f"phone_number.json", "r") as f:
        data = ujson.load(f)
        return data[f"phone_number_{phone_number_index}"]
    
# Send AT command to GSM and wait for response
def send_command(command, timeout=1000):
    uart.write(command + '\r\n')
    response = ''
    start = time.ticks_ms()
    while (time.ticks_ms() - start) < timeout:
        if uart.any():
            response += chr(uart.read(1)[0])
            time.sleep_ms(10)
    return response.strip()

# Update both phone numbers on oled display
def update_oled():
    oled.fill(0)
    oled.text("8400000001", 26, 0)
    
    number_1 = load_phone_number(1)
    number_1 = number_1.replace("+91", "")
    oled.text("Num.1:", 0, 15)
    oled.text(number_1, 49, 15)
    
    number_2 = load_phone_number(2)
    number_2 = number_2.replace("+91", "")
    oled.text("Num.2:", 0, 29)
    oled.text(number_2, 49, 29)
    
    number_3 = load_phone_number(3)
    number_3 = number_3.replace("+91", "")
    oled.text("Num.3:", 0, 43)
    oled.text(number_3, 49, 43)
    
    number_4 = load_phone_number(4)
    number_4 = number_4.replace("+91", "")
    oled.text("Num.4:", 0, 57)
    oled.text(number_4, 49, 57)
    
    oled.show()
    
def send_sms(phone_number):
    uart.write("AT\r\n")
    time.sleep(1)
    # Clear the memory
    uart.write("AT+CPMS=\"SM\"\r\n")
    time.sleep(1)
    uart.write("AT+CMGD=1,4\r\n")
    time.sleep(1)
        
    number = load_phone_number(phone_number)
    
    # Send SMS
    send_command('AT+CMGS="{}"'.format(number))
    send_command("{} Number Registered".format(number))
    uart.write(bytes([26]))
        
    # Wait for response from GSM
    response = ''
    start = time.ticks_ms()
    # wait up to 10 seconds for response  
    while (time.ticks_ms() - start) < 10000: 
        if uart.any():
            response += chr(uart.read(1)[0])
            time.sleep_ms(10)
        if '+CMGS:' in response:
            print('SMS sent successfully!')
            break
            if not '+CMGS:' in response:
                print('Error sending SMS:', response.strip())
                
def send_status(states_message): 
    # load the phone numbers from the JSON file
    phone_numbers = [load_phone_number(i) for i in range(1, 5)]

    for number in phone_numbers:
        sms_sent = False
        retries = 0
        while not sms_sent and retries < 3:
            # Send SMS
            send_command('AT+CMGS="{}"'.format(number))
            send_command(states_message)
            uart.write(bytes([26]))

            # Wait for response from GSM
            response = ''
            start = time.ticks_ms()
            # wait up to 10 seconds for response
            while (time.ticks_ms() - start) < 10000:
                if uart.any():
                    response += chr(uart.read(1)[0])
                    time.sleep_ms(10)
                if '+CMGS:' in response:
                    print('SMS sent successfully!')
                    sms_sent = True
                    break
            if not sms_sent:
                print('Error sending SMS to', number)
                retries += 1
                if retries == 3:
                    print('Maximum number of retries reached, moving to next number')

while True:
    update_oled()

    # Check if button 1 is pressed
    if not button1_pin.value() and not button1_pressed:
        # Set button state to pressed
        button1_pressed = True
        send_status('Breaker 1 Close')        

    # Check if button 1 is released
    if button1_pin.value() and button1_pressed:
        button1_pressed = False
        send_status('Breaker 1 Open')
        
    # Check if button 2 is pressed
    if not button2_pin.value() and not button2_pressed:
        button2_pressed = True
        send_status('Breaker 2 Close')
         
    # Check if button 2 is released
    if button2_pin.value() and button2_pressed:
        button2_pressed = False
        send_status('Breaker 2 Open')       

    # check if there is new data available on the UART
    if uart.any():
        # read the incoming message
        message = uart.read()

        # check if the message contains a phone number
        if b"Update1:" in message:
            # extract the phone number from the message
            phone_number_1 = extract_phone_number(message.decode(), "Update1:")
            # separate the phone number from the message
            phone_number_1 = phone_number_1.replace("Update1:", "")
            # store the phone number permanently on board
            store_phone_number(1, phone_number_1)
            # print the phone number to the console
            print("Received SMS from Supervisor 1: " + phone_number_1)
            send_sms(1)
                      
        if b"Update2:" in message:
            phone_number_2 = extract_phone_number(message.decode(), "Update2:")
            phone_number_2 = phone_number_2.replace("Update2:", "")
            store_phone_number(2, phone_number_2)
            print("Received SMS from Supervisor 2: " + phone_number_2)
            send_sms(2)

        if b"Update3:" in message:
            phone_number_3 = extract_phone_number(message.decode(), "Update3:")
            phone_number_3 = phone_number_3.replace("Update3:", "")
            store_phone_number(3, phone_number_3)
            print("Received SMS from Supervisor 3: " + phone_number_3)
            send_sms(3)

        if b"Update4:" in message:
            phone_number_4 = extract_phone_number(message.decode(), "Update4:")
            phone_number_4 = phone_number_4.replace("Update4:", "")
            store_phone_number(4, phone_number_4)
            print("Received SMS from Supervisor 4: " + phone_number_4)
            send_sms(4)
