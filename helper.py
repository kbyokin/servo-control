import time
import utime

def parse_post_data(data):
    """Parse x-www-form-urlencoded data into a dictionary."""
    parameters = {}
    if data:
        pairs = data.split("&")
        for pair in pairs:
            key, value = pair.split("=")
            parameters[key] = value
    return parameters

def handle_client(client_socket, protocol):
    res = None
    start_time = time.time() * 1000  # Record start time
    current_time = utime.localtime()
    current_time_str = "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(
        current_time[0], current_time[1], current_time[2],
        current_time[3], current_time[4], current_time[5]
    )
    if protocol == 'HTTP':
        request_line = client_socket.readline().decode('utf-8').rstrip('\r\n')
        headers = ""

        # Read and store the headers
        while True:
            line = client_socket.readline().decode('utf-8').rstrip('\r\n')
            if line == "":
                break  # End of headers
            headers += line + '\n'

        # Find the content length
        content_length = 0
        for header in headers.split('\n'):
            if header.lower().startswith('content-length:'):
                content_length = int(header.split(':')[1].strip())

        # Read the body based on content length
        body = client_socket.recv(content_length).decode('utf-8')

        # Parse and print POST data if it's a POST request
        if request_line.startswith('POST'):
            res = parse_post_data(body)

        # Send HTTP response
        client_socket.send(b'HTTP/1.1 200 OK\n')
        client_socket.send(b'Content-Type: text/plain\n')
        client_socket.send(b'Connection: close\n\n')
        client_socket.sendall(b'Received your request')

    elif protocol == 'TCP':
        try:
            data = client_socket.recv(1024).decode()  # Receive data from the client
            print(f'Received data: {data}')

            # Parse the received data (assuming two integers separated by a comma)
            try:
                values = data.split(',')
                print(f'{current_time}: Received data: {data}')
                int_values = [int(x) for x in values]
                print(f'{current_time}: Received integers: {int_values}')
                res = int_values

                # Process the received values (e.g., control motors)
                # Example: AZ_motor.angle = int_values[0]
                # Example: ALT_motor.angle = int_values[1]
            except ValueError:
                print("Invalid data format")
        except Exception as e:
            print(f'{current_time}: An error occurred: {e}')
            
    end_time = time.time() * 100  # Record end time
    elapsed_time = end_time - start_time  # Calculate elapsed time
    
    print(f'{current_time}: Elapsed time for {protocol} method: {elapsed_time} milliseconds')
    
    try:
        client_socket.close()  # Close the connection
    except Exception as e:
        print(f'{current_time}: An error occurred while closing the connection: {e}')

    return res