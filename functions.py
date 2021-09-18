import random

hello_dict =['hi', 'Hi', 'Hello!', 'hello', 'sup']

def greetings():
    return random.choice(hello_dict)

welcome_dict = ['Hey! Welcome',
                'Welcome to the server',
                'Nice to meet you, welcome',
                'Glad you could join us',
                'Nice to have you!',
                'Welcome to the jungle!']
def welcome():
    return random.choice(welcome_dict)

# Used to set roles via reactions.
emoji_roles = {
    "\U0001F396":'Gamer',
    "\U0001F3C6":'Tournaments',
    "\U0001F4DA":'Student'
}

def reaction_permission(reaction):
    return f'I am un-able to assign/remove \'{reaction}\' role\n please remeber to set my role higher then the roles you wish me to assign.'

# Command information.
dd_help = "Delete callers messages takes a value otherwise deletes most recent 3."
dD_help = "Mod command that deletes all user messages in a channel."
