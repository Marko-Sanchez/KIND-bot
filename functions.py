import random

hello_dict =['hi', 'Hi', 'Hello!', 'hello', 'sup'] 

def greetings():
    return hello_dict[random.randrange(len(hello_dict))]
