
def put_message_client(msg):
    global remote_msg
    remote_msg = msg

def get_message_client():
    global client_msg
    return client_msg

def put_message_remote(msg):
    global client_msg
    client_msg = msg

def get_message_remote():
    global remote_msg
    return remote_msg


    
client_msg = "No Updates..."
remote_msg = "No Updates..."