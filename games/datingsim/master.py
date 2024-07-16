import copy
import re
from typing import Dict, List
from string import Template
import numpy as np
import re

from backends import Model
from clemgame import get_logger
from clemgame.metrics import METRIC_ABORTED, METRIC_SUCCESS, METRIC_LOSE, METRIC_REQUEST_COUNT, \
    METRIC_REQUEST_COUNT_VIOLATED, METRIC_REQUEST_COUNT_PARSED, METRIC_REQUEST_SUCCESS, BENCH_SCORE
from clemgame.clemgame import GameMaster, GameBenchmark, GameScorer, DialogueGameMaster
from games.datingsim.player import *

GAME_NAME = "datingsim"
logger = get_logger(__name__)



class DatingSimGameMaster(GameMaster):
    def __init__(self, game_name: str, experiment: Dict, player_models: List[Model]):
        super().__init__(game_name, experiment, player_models)

        # regex patterns here

        self.experiment = experiment
        self.name = experiment['name']
        # self.penalty_rules = experiment['penalty_rules']
        self.model_a = player_models[0]
        self.model_b = player_models[1]

        self.max_prompt_retries = experiment["max_retries"]

        # initialise attributes that will be used for the evaluation scores
        self.aborted: bool = False
        self.lose: bool = False
        self.complete_turns: int = 0

        # define game status
        self.proceed = True

        # boolean to see game status
        # self.game_status = True
        # check for invalid responses 
        # self.invalid_response = False
        # self.score = {}  # this was affinity points

        self.player_model_names = list()
        for player_model in player_models:
            name = player_model.get_name()
            self.player_model_names.append(name)
        self.player_model_names = [ # what does this do
            player_model.get_name() for player_model in player_models]

        self.writer_history = []
        self.responder_history = []

    def add_player(self, player: Player) -> None:
        idx = len(self.player_model_names)
        # print(self.player_model_names)
        # print(idx)
        # player writer and responder
        if idx == 0:
            player.descriptor = f"Writer"
            self.player_model_names[idx] = player.descriptor
            # self.writer_history = list()
        elif idx == 1:
            player.descriptor = f"Responder"
            self.player_model_names[idx] = player.descriptor
            # self.responder_history = list()
        else:
            logger.warning("Invalid player index: %d", idx)
        logger.info(f"Added player {player.descriptor} with index {idx}")

    def add_message(self, player: Player, utterance: str, role="user") -> None:
        # write function, this needs to be merged with what is in GameMaster of dating_simulator/master.py
        if player == self.player_a:
            self.writer_history.append({'role': role, 'content': utterance})
            action = {'type': 'send message', 'content': utterance}
            self.log_event(from_='GM', to="Player_1", action=action)
        else:
            self.responder_history.append({'role': role, 'content': utterance})
            action = {'type': 'send message', 'content': utterance}
            self.log_event(from_='GM', to="Player_2", action=action)

    def get_answer(self, player: Player) -> str:
        if player == self.player_a:
            prompt, raw_answer, answer = player(self.writer_history, self.current_turn)
            action = {"type": "get message", 'content': answer}
            self.log_event(from_="Player_1", to="GM", action=action,
                        call=(copy.deepcopy(prompt), raw_answer))
            
            self.writer_history.append({'role': "assistant", 'content': answer})
        else:
            prompt, raw_answer, answer = player(self.responder_history, self.current_turn)
            action = {'type': 'get message', 'content': answer}
            self.log_event(from_="Player_2", to="GM", action=action,
                        call=(copy.deepcopy(prompt), raw_answer))
            self.responder_history.append({'role': "assistant", 'content': answer})


        # figure out how to add to history after parsing
        # this is a suggestion from Nic, not sure how to solve it yet
        # if restart_history == True:
        #     player.history = []
        print(answer)
        return answer

    # def get_answer(self, player: Player, restart_history=False) -> str:
    #     # this needs to be merged with what is in GameMaster of dating_simulator/master.py
    #     print(f"Debug: player.history before generating response: {player.history}")
    #     if not player.history:
    #         print("Error: player history is empty!")
    #         return ""
    #
    #     prompt, raw_answer, answer = player(player.history, self.current_turn)
    #     action = {'type': 'get message', 'content': answer}
    #     self.log_event(from_=str(player), to="GM", action=action,
    #                    call=(copy.deepcopy(prompt), raw_answer))
    #     # figure out how to add to history after parsing
    #     # this is a suggestion from Nic, not sure how to solve it yet
    #     # if restart_history:
    #     #     player.history = []
    #     return answer

    def setup(self, **game_instance) -> None:
        """
        The function sets up the game with the given game instance configuration.
        """
        logger.info("Setup")

        # import game instances
        self.game_instance = game_instance
        self.game_id = self.game_instance["game_id"]

        self.current_turn = 0
        self.n_turns = self.experiment['n_turns']
        self.num_prompt_retries = 0
        self.num_completed_turns = 0

        self.last_message = None

        # initialise metrics
        self.request_counts = [0] * (self.n_turns + 1)
        self.parsed_request_counts = [0] * (self.n_turns + 1)
        self.violated_request_counts = [0] * (self.n_turns + 1)
        
        # create player/s here
        self.player_a = Dater(self.model_a, "Writer")
        self.player_b = Dater(self.model_b, "Responder")
        
        self.initial_prompt_player_a = self.game_instance["initial_prompt_player_a"]
        self.initial_prompt_player_b = self.game_instance["initial_prompt_player_b"]
        self.location = self.game_instance['location']
        self.log_players({
            "GM": "Game master for datingsim",
            "Player_1": self.player_models[0].get_name(),
            "Player_2": self.player_models[1].get_name()}
        )

        self.log_key("n_turns", self.n_turns)

        self.further_prompt = self.game_instance["further_prompts"]
        self.further_prompt_a = self.further_prompt.replace("$character_name", self.game_instance["char_b"]["NAME"])
        self.further_prompt_b = self.further_prompt.replace("$character_name", self.game_instance["char_a"]["NAME"])

    # TO DO: include checking every response of LLMs if they are following the pattern
    def play(self):

        while self.proceed:

            self.log_next_turn()
            # self.turn()

            print(f"current turn:{self.current_turn}")

            # this would be the initial prompt
            # and the FIRST TURN
            if self.current_turn == 0:

                # Step 1a
                # GM to P1
                # Provides character sheet
                # initial prompt is (same for both): game description, goal, game rules, char-sheet
                # write first ("you are this person (char sheet A) and you write to another person (char sheet B)")
                self.add_message(self.player_a, utterance=self.initial_prompt_player_a)

                # P1 to GM
                # Writes a beginning message to P2
                answer_a = self.get_answer(self.player_a)
                # print(f"First A answer:{answer_a}")

                # check if player a gives correct response
                is_valid_turn = self.check_validity(answer_a)
                self.proceed = is_valid_turn
                if is_valid_turn == False:
                    break

                self.last_message = self.update_answer(answer_a)
            
            # SECOND TURN - initial prompt for player2 
            elif self.current_turn == 1:


                # Step 1b - second TURN
                # GM to P2
                # Provides character sheet
                # initial prompt is (same for both): game description, goal, game rules, char-sheet
                # get written to ("you are this person (char sheet B) and another person (char sheet A) writes to you this *mess*")
                # + reply to P1

                b_initial_prompt = self.initial_prompt_player_b.replace("$message_player_A", self.last_message)
                # self.add_message(self.player_b, utterance=self.initial_prompt_player_b)
                self.add_message(self.player_b, utterance=b_initial_prompt)
                
                # P2 to GM
                # Answers begin message to P1
                answer_b = self.get_answer(self.player_b)

                # check if player a gives correct response
                is_valid_turn = self.check_validity(answer_b)
                self.proceed = is_valid_turn
                if is_valid_turn == False:
                    break

                self.last_message = self.update_answer(answer_b)

            
            else:
                # prepare prompt 
                # based on turn number we can determine which player is supposed to be adressed
                # even numbers: player1 (writer) -> number%2 == False
                # odd numbers: player2 (responder) -> number%2 == True
                #

                if self.current_turn%2 == False:
                    self.player = self.player_a
                else:
                    self.player = self.player_b
                
                self.add_message(self.player, utterance=self.further_prompt_a.replace("$response", self.last_message))

                # P1 to GM
                # Writes a beginning message to P2
                answer = self.get_answer(self.player)
                # check if player a gives correct response
                is_valid_turn = self.check_validity(answer)
                self.proceed = is_valid_turn
                if is_valid_turn == False:
                    break
                self.last_message = self.update_answer(answer)


            self.current_turn += 1
            self.complete_turns += 1

            if self.current_turn > self.n_turns:
                action = {'type': 'metadata', 'content': 'Game unsuccessful. Out of turns'}
                self.log_event(from_='GM', to='GM', action=action)
                self.proceed = False


    def check_validity(self, answer):
        """
        Check if given answer by yplayer is valid or
        if it must be re-entered.
        """
        # check, if answer begins and ends with 
        pattern_for_answer = r"\[reason\].+\[end\]\n\[sentiment\].+\[end\]\n\[response\].+\[end\]"
        
        if not re.fullmatch(pattern_for_answer, answer, re.DOTALL): # abort game

            self.aborted = True
            
            # log the abortion event
            action = {'type': 'invalid format', 'content': 'Aborted'}
            self.log_event(from_='GM', to='GM', action=action)
            logger.info(f"Invalid format.")

            # increase the counter of requests that violate form rules
            self.violated_request_counts[self.current_turn] += 1
            return False
        
        else:
        
            # increase the counter of requests that conform to form rules
            self.parsed_request_counts[self.current_turn] += 1
            # log the event that the string was valid (no strange characters)
            action = {'type': 'metadata', 'content': 'valid string'}
            self.log_event(from_='GM', to='GM', action=action)

            # log the fact that the answer was correct
            action = {'type': 'parse',
                    'content': f'{answer} conforms to rules'}

            self.log_event(from_='GM', to='GM', action=action)
            return True

    def update_answer(self, answer):
        """
        Update the last response said
        """
        # filter out the response 
        response_pattern = r"\[response\](.+)"
        response_match = re.search(response_pattern, answer, re.DOTALL)
        last_message = response_match.group(1)
        # print(f"Last message: {last_message}")
        return last_message


    

# This needs to be adjusted or removed completely (replaced)
# def enforce_template(pattern, game_transcript, specific_transcript):
#     """
#     Function which checks the given answer of the LLMS.
#     If they follow the given template, all gucci.
#     If not, generate new prompt where we enforce the
#     usage of the template
#     """
#
#     tries_to_genrate_correct_output = 0
#
#     while True:
#
#         response = game_transcript[-1]["content"]
#
#         # Search for the pattern in the output
#         match = re.search(pattern, response, re.DOTALL)
#
#         if match:
#             game_status = "ongoing"
#             break
#         elif tries_to_genrate_correct_output > 2:
#             game_status = "abort"
#             print(game_status)
#             break
#         elif not match:
#             # Handle cases where the output doesn't match the template
#             prompt = f"""ERROR: Your given ANSWER doess not follow the given TEMPLATE. Try again. Use the following TEMPLATE: {pattern}
#
# DO NOT APOLOGIZE OR WHATEVER. JUST USE THE PATTERN"""
#             tries_to_genrate_correct_output += 1
#             prompting(prompt, game_transcript, specific_transcript)
#
#     return response, game_status


# this needs to be completely changed according to our new rules when the game ends
# def check_if_continue_game(npc_reaction_values):
#     """
#     Function which checks the number of negative
#     responses of the NPC in a row.
#     """
#     if len(npc_reaction_values) >= 2:
#
#         # count negative values:
#         num_neg_values = 0
#         for value in npc_reaction_values[-1:-3]:
#             if value < 0:
#                 num_neg_values += 1
#         return num_neg_values
#
#     else:
#         num_neg_values = 0
#         return num_neg_values


##########################################################
##########################################################


class DatingSimGameScorer(GameScorer):
    def __init__(self, experiment: Dict, game_instance: Dict):
        super().__init__(GAME_NAME, experiment, game_instance)
        # might need to add response patterns of players

    def compute_scores(self, episode_interactions: Dict) -> None:
        """
        TODO: 3 main metrics: 
            ++ we need to evaluate both players
            efficiency: number of turns taken to agree / max pre-defined number of turns
            agreement rate
            error handling: error counter?
            (?) clemscore = efficiency * agreement rate - error handling
            (bonus) average dialogue length:
            (bonus) vocabulary size:
        
        """
        """Episode level scores"""
        max_n_turns = episode_interactions["max_n_turns"] # we need to add it to instance gen?
        turns = episode_interactions["turns"]

        #aborted = False # maybe not needed
        invalid_response = False
        total_agreements = 0 # TODO: ask Imge and Jerycho whether we can have more than one agreement per episode? does the game end when we have an agreement?
        turn_scores = []

        # TODO look at the implementation of generated expression length from referencegame
        # TODO differentiate between Player 1 and Player 2 when the game is aborted

        for turn_idx, turn in enumerate(turns):

            turn_score = {
                "agreement": 0,
                "request_count": 0,
                "violated_request_count": 0,
                "parsed_request_count": 0,
                "reprompts_count": 0,
                "error_turn_sum": 0,
            }

            for event in turn:
                action = event["action"]

                if action["type"] == "invalid format":
                    invalid_response = True

                if action["type"] == "agreement": # agreement rate
                    turn_score["current_point"] = action["content"]
                    turn_score["agreement"] = 1

                if action["type"] == "reprompt": # error handling
                    turn_score["turn_reprompts"] += 1
                    # should we add invalid_response here? im a bit confused

                if invalid_response:
                    turn_score["violated_request_count"] = 1
                    turn_score["parsed_request_count"] = 0
                else:
                    turn_score["violated_request_count"] = 0
                    turn_score["parsed_request_count"] = 1

                self.log_turn_score(turn_idx, 'Turn Agreement', turn_score["agreement"])
                self.log_turn_score(turn_idx, 'Turn Reprompts', turn_score['turn_reprompts'])
                self.log_turn_score(turn_idx, METRIC_REQUEST_COUNT_VIOLATED, turn_score["violated_request_count"])
                self.log_turn_score(turn_idx, METRIC_REQUEST_COUNT_PARSED, turn_score["parsed_request_count"])
                self.log_turn_score(turn_idx, METRIC_REQUEST_COUNT, turn_score["request_count"])
                turn_scores.append(turn_score)
        
        violated_request_count = sum([turn["violated_request_count"] for turn in turn_scores])
        self.log_episode_score(METRIC_REQUEST_COUNT_VIOLATED, violated_request_count)

        parsed_request_count = sum([turn["parsed_request_count"] for turn in turn_scores])
        self.log_episode_score(METRIC_REQUEST_COUNT_PARSED, parsed_request_count)

        request_count = violated_request_count + parsed_request_count
        self.log_episode_score(METRIC_REQUEST_COUNT, request_count)

        self.log_episode_score(METRIC_REQUEST_SUCCESS, parsed_request_count / request_count)

        # TODO: how to report these game-specific metrics in logs?
        episode_efficiency = len(turns) / max_n_turns 
        total_agreements = sum([turn["agreement"] for turn in turn_scores]) 
        error_handling = sum([turn["turn_reprompts"] for turn in turn_scores])

        # Common metrics
        if invalid_response:  # response not parsable
            self.log_episode_score(METRIC_ABORTED, 1)
            self.log_episode_score(METRIC_SUCCESS, 0)
            self.log_episode_score(METRIC_LOSE, 0)
            # Game-specific metrics 
            self.log_episode_score(BENCH_SCORE, np.nan)  # metric not applicable
        else:
            self.log_episode_score(METRIC_ABORTED, 0)
            if total_agreements > 0:
                self.log_episode_score(METRIC_SUCCESS, 1)
                self.log_episode_score(METRIC_LOSE, 0)
                self.log_episode_score(BENCH_SCORE, 100 / ((episode_efficiency * total_agreements)) - error_handling)
            else:
                self.log_episode_score(METRIC_SUCCESS, 0)
                self.log_episode_score(METRIC_LOSE, 1)
                self.log_episode_score(BENCH_SCORE, 0)


##########################################################
##########################################################


class DatingSimGameBenchmark(GameBenchmark):

    def __init__(self):
        super().__init__(GAME_NAME)

    # defines whether the game is single player or not
    def is_single_player(self):
        return False

    # add a description of your game
    def get_description(self):
        return "A game where LLMs date"

    def create_game_master(
            self, experiment: Dict, player_models: List[Model]
    ) -> GameMaster:
        return DatingSimGameMaster(game_name="datingsim", experiment=experiment, player_models=player_models)

    def create_game_scorer(self, experiment: Dict, game_instance: Dict) -> GameScorer:
        return DatingSimGameScorer(experiment, game_instance)
