"""
Generate instances for the dating simulator game.

Creates files in ./instances
"""
import random
import os
import json
from string import Template
# import tqdm

import clemgame
from clemgame.clemgame import GameInstanceGenerator

from utils import *
# from rizzSim.games.datingsim.utils import *

GAME_NAME = 'datingsim'
# we will create 10 instances for each experiment; vary this as you wish
N_INSTANCES = 20
# if the generation involves randomness, remember to set a random seed
SEED = 42

logger = clemgame.get_logger(__name__)


class DatingSimInstanceGenerator(GameInstanceGenerator):

    def __init__(self):
        super().__init__(GAME_NAME)
        # self.instances = dict(experiments=list())

    def load_instances(self):
        return self.load_json("in/instances")

    def on_generate(self):
        # get resources
        # load character sheets which will be our experiments
        # aka need to change the resources where we 
        # predefine the character sheet mash ups
        # example: one where both players are male,
        # one where both players are female, etc.
        # TO DO: prepare the datasets 
        char_sheets = get_random_npcs('games/datingsim/resources/testfile.json')
        n_turns = 15
        max_retries = 3
        re_prompt_allowed = True # adjustable per experiment

        # initial prompts for player A and player B
        # TO-DO: Change prompts
        initial_prompt_a = self.load_template('resources/initial_prompts/initialprompt_playerA.template') 
        initial_prompt_b = self.load_template('resources/initial_prompts/initialprompt_playerB.template')

        further_prompts = self.load_template('resources/prompts/further_prompts.template')

        reprompt_prompt = self.load_template('resources/prompts/reprompt.template')
        """
        maybe we can still leave this in and generate more experiments with
        the amount of character information they get 

        for mode in ["easy", "normal", "hard"]:
        """

        # build th file, one experiment at a time
        for index, experiment in enumerate(char_sheets):
            # create experiment, name is (WILL BE) in the char sheet
            experiment = self.add_experiment(f"Playthrough_{experiment['exp_name']}")
            experiment["n_turns"] = n_turns
            experiment["max_retries"] = max_retries
            experiment["re_prompt_allowed"] = re_prompt_allowed
            # build n instances for each experiment 
            for game_id in range(N_INSTANCES):
                # set parameters
                # give players the characters - for now random
                charsheet_a = random.choice(char_sheets[index]["chars"])
                charsheet_b = random.choice(char_sheets[index]["chars"])

                instance = self.add_game_instance(experiment, game_id)

                # populate game with parameters
                instance["char_a"] = charsheet_a
                instance["char_b"] = charsheet_b

                instance["initial_prompt_player_a"] = initial_prompt_a.replace("$charsheet_a", str(instance["char_a"])).replace("charsheet_b", str(instance["char_b"]))
                instance["initial_prompt_player_b"] = initial_prompt_b.replace("$charsheet_a", str(instance["char_a"])).replace("charsheet_b", str(instance["char_b"]))
                instance["further_prompts"] = further_prompts
                instance["reprompt_prompt"] = reprompt_prompt


if __name__ == '__main__':
    random.seed(SEED)
    # always call this, which will actually generate and save the JSON file
    DatingSimInstanceGenerator().generate(filename="instances.json")
