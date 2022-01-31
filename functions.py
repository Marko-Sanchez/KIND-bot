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

"""
    Cache implementation to limit api calls to mongoDB server involving command prefix
    opertions, which occur frequently with limited changes.
"""
prefixCache = {}

# Checks if server prefix exst in cache:
def prefixExist(guildID):
    global prefixCache
    if guildID in prefixCache:
        return True
    return False

# Get  prefix for specifed server:
def grabPrefix(guildID):
    global prefixCache
    pre = prefixCache[guildID]
    pload()
    return pre

# Adds prefix onto cache for fast retrieval:
def addPrefix(guildID, prefix):
    global prefixCache
    pload()
    prefixCache[guildID] = prefix

# Resets Cache once a certain amount of calls havev been made:
# A load counts as retrieiving a prefix or adding a prefix to the cache.
def pload():
    global prefixCache
    if "Loads" not in prefixCache:
        prefixCache["Loads"] = 0
    elif prefixCache["Loads"] >= 50:
        # Empty Cache and set loads to 0:
        prefixCache = {"Loads": 0}
    else:
        prefixCache["Loads"] += 1
