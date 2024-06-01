import os
import json

# generate JSON file to save playthrough of game
save_dir = "./playthroughs/"
if not os.path.exists(save_dir):
    os.makedirs(save_dir)

# get number of playthroughs # should we divide between LLM and Human playthroughs?
nr_of_plays = len(os.listdir(save_dir))
# probably yes for evaluation
playthrough_json = f"./playthroughs/{nr_of_plays+1}_playthrough.json"

with open(playthrough_json, "w", encoding="UTF-8") as file:
    current_play_json = json.load(file)
print(current_play_json)
