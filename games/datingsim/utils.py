import json
import random


def get_random_npcs(npc_sheets):
    """
  Function which fetches the npc sheets
  and returns them shuffled.
  """
    with open(npc_sheets, "r", encoding="UTF-8") as file:
        npcs = json.load(file)
        random.shuffle(npcs)
        return npcs

# import string
# from together import Together # TODO: if there is a way to directy load via clembench. it'd have been better
# import re

# from utils import *

# with open("./key.txt", "r", encoding="UTF-8") as file: # better with clem prob, TODO: check a function using key.json
#     api_key = file.read()
# # client = Together(api_key=api_key)

# # Function to load the template from a file
# def load_template(file_path):
#     with open(file_path, 'r') as file:
#         template_content = file.read()
#     return string.Template(template_content)
