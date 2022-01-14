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

tip_of_the_day = ['smh my head',
                  '!help for a list of commands',
                  'Chose your role in the \#roles channel',
                  'At your service']
def reply():
    return random.choice(tip_of_the_day)

def reaction_permission(reaction):
    return f'I am un-able to assign/remove \'{reaction}\' role\n please remeber to set my role higher then the roles you wish me to assign. Under Server settings -> Roles'

# Command information.
roles_help = "Let members self assign roles via reaction, creates message in #roles"
addRolesH = "Add new role to embed message in #role:\n !addRoles (emote) (roleName)"
removeRolesH = "Removes role from embed message in #role:\n !removeRoles (emote)"
listRolesH = "List all roles"
