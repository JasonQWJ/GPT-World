import re
import json
import copy
from typing import Dict, List
import tiktoken
import logging
import datetime
from datetime import datetime as dt
# from gptworld.core.environment import GPTWorldEnv
from gptworld.life_utils.agent_reflection_memory import ReflectionMemory
from gptworld.life_utils.agent_tool import as_tool, Tool
from gptworld.utils import request_GPT
from gptworld.utils.logging import get_logger
import os


logger = get_logger(__file__)
logger.debug = print
logger.info = print

"""
Agent class implements the static, mind, inner, and cognitive process
"""

# # The color for intermediate result
# RESET = "\033[0m"  # reset color output
# GREEN = "\033[92m"  # Green text
# MAGENTA = "\033[35m"  # Magenta text
# RED = "\033[31m"  # Red text
# BOLD = "\033[1m"  # Bold text
# BLUE = "\033[34m"  # Blue text
#
# MAX_SHORT_TERM_MEMORY = 1500
# MAX_LONG_TERM_MEMORY = 1500


class GPTAgent:
    """ Simple Implementation of Chain of Thought & Task Based Agent
    """

    def __init__(self,
                 state_dict: Dict,
                 file_dir
                 # llm: callable,
                 # tools: List[Tool],
                 # prompt_template: str
                 ):
        """ Intialize an agent.
        state_dict: Dict -> a state dict which contains all the information about the agent
        llm: callable -> a function which could call llm and return response
        tools: List[Tool] -> a list of Tool
        prompt_template: str -> a template for prompt

        """

        self.file_dir = file_dir

        self.state_dict = state_dict

        self.incoming_interactions = [{"sender": "A", "message": "XXX"}]

        self.incomming_objection = ["XXXX",]

        self.incomming_invoice = []

        self.location = [10,10]

        self.summary = "XXXX"

        self.plan = [{"task": "XXX", "start_time": datetime.datetime(2023,4, 1), "end_time": datetime.datetime(2023,4, 1)}]

        
        # 记录当前对话历史
        self.incoming_interactions = state_dict.get('IncomingInteractions',[])

        # 记录下一轮需要处理的新observation
        self.incoming_observation = state_dict.get('IncomingObservation',[])

        # Parse initial location from state dict. format: {"eid": "e_004", "pos": [1,1]}
        self.location = state_dict.get('Location',None)

        # self summary of current state.
        self.summary = state_dict.get( 'Summary', None)

        # Broad Stroke Plan
        self.WholeDayPlan = state_dict.get('WholeDayPlan',None)

        # fine-grained plan list for next task searching
        # format: [{"task": "XXX", "start_time": datetime.datetime(2023,4, 1), "end_time": datetime.datetime(2023,4, 1)}]
        self.plan = state_dict.get('Plan',[])

        # Long term memory is serialized/deserialized by orjson so only file name is provided here.
        self.LongTermMemory=ReflectionMemory(state_dict,file_dir)

        # Short term memory is a queue of observations recording recent observations.
        self.ShortTermMemory=state_dict.get('shortTermMemory',[])

        # basic fingerprint
        self.name = state_dict.get("Name", None)

        self.age=state_dict.get("Age",None)

        self.traits=state_dict.get("Traits",None)

        self.movement = state_dict.get("movement", "static")

        self.max_velocity = state_dict.get("VelocityUpperBound", 1)

        # Type of the agent, either 'objective' or 'subjective'
        self.type = state_dict.get("type", None)

        # Initialized at mount time
        self.environment = None
        self.environment_id = None

        # The thinking kernel
        # self.llm = llm

        # The chain of thought prompt
        # self.prompt_template = prompt_template # template of promot, defined by user 

        # A List of Tool
        # self.tools = tools

        # Mapping from action name to action Tool object
        # self.tool_map = {}
        # self.tool_names = []
        # for tool in self.tools:
        #     self.tool_names.append(tool.tool_name)
        #     self.tool_map[tool.tool_name] = tool

        # self.tool_names_and_descriptions = "\n".join(
        #     [tool.tool_name + " - " + tool.tool_description for tool in self.tools])  # tool names and desctiptions

        # Whether the agent is moving ("moving" or "static")

        # The actual velocity
        self.velocity = 0

        # Child agent (something append to self)
        self.child = state_dict.get("child_agent", [])

        # Money
        self.money = state_dict.get("money", 100)

        # Mental state score, from 0 to 100
        self.mental_score = 50

        # Energetic score, from 0 to 100
        self.energetic_score = 100

        # the agent is calling language model
        self.blocking = False

        return
    
    def invoice(self, ):
        # 往 incomming invoice 里
        pass

    @classmethod
    def from_file(cls, file_dir, file_name):
        logger.debug(file_dir)
        agent_path = os.path.join(file_dir, file_name)
        if os.path.exists(agent_path):
            with open(os.path.join(file_dir, file_name), 'r') as f:
                data = json.load(f)
            return cls(**{"state_dict": data, "file_dir": file_dir})
        else:
            logger.warning(f"No config of {agent_path} found!")
            return None

    def available_actions(self):
        """ return available actions I can handle
        """
        return self.tool_names

    def observe(self):
        """ Update observation of around environment
        """
        self.observation = self.environment.get_neighbor_environment(self.location)
        return

    def reflect(self,time:datetime):
        """ While the time is right, do reflection for memory
        """
        return self.LongTermMemory.maybe_reflect(time)

    def generate_summary(self,time:dt):
        """
        # Generating summary for myself
        :param agent:
        :return: summary string
        """

        # retrieved_record = """
        # Chris is a undergraduate student in Tsinghua University, Love to play tennis and expand knowledge on
        # many different regions. Major in Electrical Engineering, but join in the Natural Language Processing Research Team
        # , very busy at his schoolwork.
        # """
        qResList1 = self.LongTermMemory.query(f"{self.name}'s core characteristics",10,time)
        qResList2 = self.LongTermMemory.query(f"{self.name}'s current daily plan",10,time)
        qResList3 = self.LongTermMemory.query(f"{self.name}'s feeling about his recent progress in life",10,time)

        q1,q2,q3=map(lambda k: '\n'.join(k),(qResList1,qResList2,qResList3))

        query1 = f"""
        How would one describe {self.name}'s core characteristics given the following statements?
        {q1}
        """
        result1 = request_GPT.request(query1)

        # 'daily occupation' is ambiguous and performs bad in searching daily requirements and summarizing schedule.
        query2 = f"""
        What is {self.name}'s current daily plan given the following statements?
        {q2}
        """

        result2 = request_GPT.request(query2)

        query3 = f"""
        What might be {self.name}'s feeling about his recent progress in life given the following statements?
        {q3}
        """

        result3 = request_GPT.request(query3)

        BasicInfo=f"""\
Name: {self.name} (age: {self.age})
Innate traits: {self.traits}"""

        # Notice the order of these results in the example of GA paper/
        return BasicInfo+result1 + result3 + result2

    def plan_in_broad_strokes(agent, date: datetime.date) -> List[dict]:
        """
        broad strokes planning of an agent
        :param agent: agent object
        :param date: str representing the current day
        :return: plans, each element is a plan
                 "task", "start time": datetime.datetime, "end time":datetime.datetime
        """

        text_base = f"""
        Name:{agent.Name} (age: {agent.Age})
        Innate traits: {agent.Personality}
        {agent.Summarize}
        {agent.Memory}
        Today is {date}. Here is {agent.Name}’s plan date in broad strokes:
        [Example format: 
         1) wake up and complete the morning routine at 8:00am,
         2) go to Oak Hill College to take classes from 10:00am to 12:00pm]

        """

        request_result = request_GPT.request(text_base)

        # a typical example to test the regex expressions without access to the GPT
        # request_result = """
        # 1) Wake up at 8:00am and have breakfast,
        # 2) Go to the library to do some research from 10:00am to 12:00pm,
        # 3) Have lunch at 12:30pm,
        # 4) Play tennis from 2:00pm to 4:00pm,
        # 5) Go back to the library to do research from 4:30pm to 6:30pm,
        # 6) Have dinner at 7:00pm,
        # 7) Relax and watch a movie from 8:00pm to 10:00pm.
        # """

        logging.info(f"Request GPT result(Broad strokes):\n{request_result}")

        pattern = r"(?:\d+\))((.+) (from|at) ((?:\d+:\d+)\s*(?:am|pm))(?: to ((?:\d+:\d+)\s*(?:am|pm)))?)"
        matches = re.findall(pattern, request_result)

        if matches:
            plans = []
            for match in matches:
                try:
                    # task = match[1]  # this neglected the time information, disposed
                    task = match[0]  # get the whole string, including the time info as the tast str
                    if match[2] == "from":
                        # from ... to ... structure
                        start_time = datetime.datetime.combine(date
                                                               , datetime.datetime.strptime(match[3].replace(" ", ""),
                                                                                            "%I:%M%p").time())
                        end_time = datetime.datetime.combine(date
                                                             , datetime.datetime.strptime(match[4].replace(" ", ""),
                                                                                          "%I:%M%p").time())
                    elif match[2] == 'at':
                        # at ... structure
                        start_time = end_time = datetime.datetime.combine(date
                                                                          , datetime.datetime.strptime(
                                match[3].replace(" ", ""), "%I:%M%p").time())
                    else:
                        raise Exception()
                    plans.append({
                        "task": task,
                        "start time": start_time,
                        "end time": end_time,
                    })
                except:
                    # logging.error("Bad Structure of GPT's response: Neither 'from...to...' or 'at...' structure")
                    logging.error(f"Response: {request_result}")
                    logging.error(e.__traceback__)
                    logging.error(e.__context__)

            logging.info(plans)
            return plans
        else:
            raise Exception(f"Regex parsing error after requesting plans. Request result: {request_result}")

    def plan_in_detail(agent, plan: dict, time_granularity: datetime.timedelta, date) -> List[dict]:
        """
        generate more detailed plan on the basis of a broad stroke plan(or just a relatively not detailed plan)
        :param agent:
        :param plan: a dict with keys of those mentioned in plan_in_broad_strokes
        :param time_granularity: the time granularity that the generated plan should be (e.g. 15 minutes) in NL
        :return: a more detailed list of plan

        """

        text_base = f"""
        Name:{agent.Name} (age: {agent.Age})
        Innate traits: {agent.Personality}
        {agent.Summarize}
        {agent.Name} plans to {plan['task']} date. {agent.Name} will do the following things in this time period
        [Example format: 
         4:00 pm: grab a light snack, such as a piece of fruit, a granola bar, or some nuts.
         4:05 pm: take a short walk around his workspace.]
         (Precise to {time_granularity.total_seconds() / 60} minutes):

        """

        request_result = request_GPT.request(text_base)

        # a sample
        # request_result = """
        # 9:00 am: Wake up, take a shower and get ready for the day.
        #  9:15 am: Eat a healthy breakfast such as oatmeal, eggs, or yogurt.
        #  9:30 am: Take a short walk to the university campus.
        #  9:45 am: Arrive at the university and prepare for classes.
        #  10:00 am: Attend classes and take notes.
        #  10:45 am: Take a break and review the notes taken in class.
        #  11:00 am: Get ready for the next class.
        # """

        pattern = r"((?:\d+:\d+)\s*(?:am|pm)).*:\s*(.+)"
        matches = re.findall(pattern, request_result)
        if matches:
            plans = []
            for i in range(len(matches)):
                match = matches[i]
                try:
                    # task = match[1]  # this neglected the time information, disposed
                    task = match[1]  # get the whole string, including the time info as the tast str
                    start_time = datetime.datetime.combine(date
                                                           , datetime.datetime.strptime(match[0].replace(" ", ""),
                                                                                        "%I:%M%p").time())
                    if i < len(matches) - 1:
                        end_time = datetime.datetime.combine(date
                                                             , datetime.datetime.strptime(
                                matches[i + 1][0].replace(" ", "")
                                , "%I:%M%p").time())
                    else:
                        end_time = plan['end time']
                    plans.append({
                        'task': task,
                        'start time': start_time,
                        'end time': end_time,
                    })
                except Exception as e:
                    logging.error(f"Response: {request_result}")
                    logging.error(e.__traceback__)
                    logging.error(e.__context__)
                    # raise Exception("Bad Structure of GPT's response(detailed): Neither 'from...to...' or 'at...' structure")

            logging.info(plans)
            return plans
        else:
            raise Exception(f"Regex parsing error after requesting plans. Request result: {request_result}")

    def reprioritize(self, **kwargs):
        """ Reprioritize task list
        """
        # TODO: implement reprioritize : 凡哥、京伟
        return

    def action(self, receiver: str, action_type: str, content: str):
        """ Create an action targeted on other agents
        :param receiver: the name of receiver like "Alex", "Tree", "Starship"
        :param action_type: if you want to use a function of that agent, use the name of the function, otherwise use "misc"
        :param content: the content of the action like "Hi, how is it going?" (should be complete and in natural language.)
        """
        self.outgoing_interactions.append(
            {"sender": self.name, "action_type": action_type, "receiver": receiver, "content": content})
        return

    def mount_to_environment(self, environment, environment_id: str = None, location: List[List[int]] = None):
        """ Mount the agent to the environment
        :param environment: the environment to which the agent will be mounted
        :param environment_id: the unique id of this environment
        :param location: the initial location of this agent in the environment
        """

        self.environment = environment
        self.environment_id = environment_id

        # If location is not specified, allocate an available seat to this agent
        if location is None:
            location = self.environment.pop_available_seats()
        self.location = location

        # Call environment method to sync the change to environment
        self.environment.mount_agent(self, self.location)

        return

    def post_in_interaction(self, action_type: str, content: str, sender: str):
        """ Handle the action from other agents and store in queue
        :param action_type: the type of the action, either tool names or "misc"
        :param content: the content of action
        :param sender: the sender of action
        """
        self.incoming_interactions.append({"sender": sender, "content": content})
        return

    def get_out_interaction(self) -> List:
        """ Get my outgoing interactions queue
        """
        return self.outgoing_interactions

    def step(self, current_time):
        """ Call this method at each time frame
        """

        logger.debug("Agent {}, Current Time: {}".format(self.state_dict['name'], str(current_time)) )
        
        # # 测试异步
        # if self.state_dict['name'].startswith("A"):
        #     time.sleep(20)
        # logger.debug("Agent {} is done".format(self.state_dict['name']))


        # TODO LIST， 每个人写一个if, 然后if里面用自己的成员函数写，避免大面积冲突。

        # 1. 如果当前正在向openai请求，调过这一步

        # 2. 检查自己当前动作是否需要结束，如果需要，则检查plan，开启下一个动作 （如果下一步没有 fine-grained sroke, 就plan）。 @TODO jingwei

        # 3. 检查当前有没有new_observation (或 incoming的interaction 或 invoice), 如果有要进行react, react绑定了reflect和plan的询问。 @TODO zefan
        #    多个observation一起处理，处理过就扔进短期记忆。
        #    短期记忆是已经处理过的observation。

        # 4. 周期性固定工作 reflect, summary. (暂定100个逻辑帧进行一次) @TODO jingwei

        # 5. 每个帧都要跑下寻路系统。 @TODO xingyu


        return
    
    def step_test(self, current_time):
        """ Call this method at each time frame
        """

        logger.debug("Agent {}, Current Time: {}".format(self.state_dict['name'], str(current_time)) )

        # # 测试异步
        # if self.state_dict['name'].startswith("A"):
        #     time.sleep(20)
        # logger.debug("Agent {} is done".format(self.state_dict['name']))


        # TODO LIST， 每个人写一个if, 然后if里面用自己的成员函数写，避免大面积冲突。

        # 1. 如果当前正在向openai请求，调过这一步

        # 2. 检查自己当前动作是否需要结束，如果需要，则检查plan，开启下一个动作 （如果下一步没有 fine-grained sroke, 就plan）。 @TODO jingwei

        # 3. 检查当前有没有new_observation (或 incoming的interaction 或 invoice), 如果有要进行react, react绑定了reflect和plan的询问。 @TODO zefan
        #    多个observation一起处理，处理过就扔进短期记忆。
        #    短期记忆是已经处理过的observation。

        # 4. 周期性固定工作 reflect, summary. (暂定100个逻辑帧进行一次) @TODO jingwei

        # 5. 每个帧都要跑下寻路系统。 @TODO xingyu


        return

    def compose_dev(self):
        """ Truncation:  Compose the context feed to large language model in this step (with trucation to avoid overflow of total tokens)
        When finished, this will become depreciated.
        """
        # first truncation
        tokenizer = tiktoken.get_encoding("cl100k_base")

        # count system prompt length
        formatted_prompt = self.prompt_template.format(
            tool_names_and_descriptions=self.tool_names_and_descriptions,
            tool_names=f"[{', '.join(self.tool_names)}]",
            task=self.task,
            agent_playground=""
        )

        num_tokens_system = len(tokenizer.encode(formatted_prompt))
        available_tokens_for_agent_playground = MAX_SHORT_TERM_MEMORY - num_tokens_system

        # reverse self.history
        history_copy = copy.deepcopy(self.history)
        history_copy.reverse()

        # truncate agent_playground
        agent_playground = []
        num_tokens = 0
        for message in history_copy:
            length_message = len(tokenizer.encode(message))
            if (num_tokens + length_message + 4) <= available_tokens_for_agent_playground:
                num_tokens += 4
                num_tokens += length_message
                agent_playground.append(message)

        # reverse back
        agent_playground.reverse()  # recover the original agent_playground

        # finally ground the prompt template
        formatted_prompt = self.prompt_template.format(
            tool_names_and_descriptions=self.tool_names_and_descriptions,
            tool_names=f"[{', '.join(self.tool_names)}]",
            task=self.task,
            agent_playground="".join(agent_playground)
        )

        # TODO: Use all the short term context to compute semnatic embedding -> use cosine similarity to compute the most relevant items and append them to the context

        # MAX_LONG_TERM_MEMORY

        return formatted_prompt

    def step_dev(self):
        """ Single action step"""

        # First update the observation
        self.observe()

        # Fetch incoming interactions
        self.incoming_interactions

        # if exception occurs, retry 3 times at most

        while (not no_exception) and (num_trial < 3):
            num_trial += 1

            # generate response
            response = self.llm(formatted_prompt)
            if response == "":
                continue

            print(f"Thought: {response}")

            # extract the Action
            pattern = r'Action: (.+?)\n'
            match = re.search(pattern, response)
            if match:
                action_content = match.group(1)
                print(f"{GREEN}{BOLD}Action: {action_content}{RESET}")
            else:
                print(f"{RED}{BOLD}Error: cannot find Action{RESET}")
                continue

            # TODO: this is legacy, maybe we need to modify this
            pattern = r'Action Input:\s*(\{.*\})'
            match = re.search(pattern, response)

            if match:
                action_input_content = match.group(1)
                print(f"{GREEN}{BOLD}Action Input: {action_input_content}{RESET}")
            else:
                print(f"{RED}{BOLD}Error: cannot find Action Input{RESET}")
                continue

            # find the tool of action
            action_tool = self.tool_map[action_content]

            # TODO: this is a legacy, need to be adapted 
            # pass the Action Input (in JSON format) to the action_tool function, get observation
            try:
                action_input_content = json.loads(action_input_content)  # parse str to json

                # TODO: use tools, need to be adapted
                action_input_content["environment"] = self.environment
                action_input_content["agent"] = self

                observation = action_tool(**action_input_content)

            except Exception as e:

                print(f"{RED}{BOLD}Exception, retrying...{RESET}")
                self.exception_count += 1
                observation = e

            self.history.append(response)
            self.history.append("\n")

            print(f"{MAGENTA}{BOLD}Observation: {observation}\n{RESET}")

            self.history.append(f"Observation: {observation}\n")
            self.history.append(f"Thought: ")

            if action_tool.tool_type == "finish":
                print(f"{BLUE}{BOLD}Task finished!{RESET}")
                self.finish = True

            no_exception = True

            # if too many exceptions 
            if self.exception_count > 10:
                self.finish = True
                print(f"{RED}{BOLD}Too many exceptions, terminated.{RESET}")
                return

        return
