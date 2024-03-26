def reaction_permission(reaction):
    return f'I am un-able to assign/remove \'{reaction}\' role\n please remeber to set my role higher then the roles you wish me to assign. Under Server settings -> Roles'

# Command information.
roles_help = "Let members self assign roles via reaction, creates message in #roles"
addRolesH = "Add new role to embed message in #role:\n addRoles (emote) (roleName)"
removeRolesH = "Removes role from embed message in #role:\n removeRoles (emote)"
listRolesH = "List all roles in server"

"""
    Cache implementation to limit api calls to mongoDB server involving command prefix
    opertions, which occur frequently with limited changes.
"""
prefixCache = {}

# Checks if server prefix exst in cache:
def prefixExist(guildID:str):
    global prefixCache
    if guildID in prefixCache:
        return True
    return False

# Get  prefix for specifed server:
def grabPrefix(guildID:str):
    global prefixCache
    if guildID not in prefixCache:
        return None
    pre = prefixCache[guildID]
    pload()
    return pre

# Adds prefix onto cache for fast retrieval:
def addPrefix(guildID:str, prefix:str):
    global prefixCache
    pload()
    prefixCache[guildID] = prefix

# Resets Cache once a certain amount of calls have been made:
# Load count as retrieiving a prefix or adding a prefix to the cache.
def pload():
    global prefixCache
    if "Loads" not in prefixCache:
        prefixCache["Loads"] = 0
    elif prefixCache["Loads"] >= 50:
        # Empty Cache and set loads to 0:
        prefixCache = {"Loads": 0}
    else:
        prefixCache["Loads"] += 1
