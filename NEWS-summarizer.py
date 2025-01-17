import os
from openai import OpenAI
from dotenv import find_dotenv, load_dotenv
import requests
import json
import time
import streamlit as st

# Load the environment variables from the .env file
load_dotenv()

client = OpenAI()
model = "gpt-4o-mini"

# set news api key
news_api_key = os.environ.get("NEWS_API_KEY")

def get_news(topic):
    url = (
        f"https://newsapi.org/v2/everything?q={topic}&apiKey={news_api_key}"
    )

    try:
        response = requests.get(url)
        if response.status_code == 200:
            news = json.dumps(response.json(), indent=4)
            news_json = json.loads(news)

            data = news_json
            
            #access the essential fields of api response
            status = data["status"]
            total_results = data["totalResults"]
            articles = data["articles"]
            final_news = []

            #loop through articles
            for article in articles[:2]:
                source_name = article["source"]["name"]
                author = article["author"]
                title = article["title"]
                description = article["description"]
                url = article["url"]
                content = article["content"]
                title_description = f'''
                  Title: {title},
                  Author : {author},
                  source : {source_name},
                  Description : {description},
                  URL : {url}
                '''
                final_news.append(title_description)

            return final_news
        else:
             return ["error"]
        
    except requests.Exceptions.RequestException as e:
            print("error occured during api request", e)


class AssistantManager:
     thread_id = None
     assistant_id = "asst_YAfN9m4HlgngZS7fLBpnMac3"

     def __init__(self, model: str= model):
          self.client = client
          self.model = model
          self.assistant = None
          self.thread = None
          self.run = None
          self.summary = None
    
          if AssistantManager.assistant_id:
               self.assistant = self.client.beta.assistants.retrieve(
                    assistant_id=AssistantManager.assistant_id
               )
          if AssistantManager.thread_id:
               self.thread = self.client.beta.threads.retrieve(
                    thread_id=AssistantManager.thread_id
               )
     def create_assistant(self,name,instructions,tools):
          if not self.assistant:
               Assistant_obj = self.client.beta.assistants.create(
                    name=name,
                    instructions=instructions,
                    tools=tools,
                    model=self.model
               )
               AssistantManager.assistant_id= Assistant_obj.id
               self.assistant = Assistant_obj
               print(f"assisid::::{self.assistant_id}")

     def create_threaad(self):
          if not self.thread:
               thread_obj = self.client.beta.threads.create()
               AssistantManager.thread_id = thread_obj.id
               self.thread= thread_obj
               print(f"threadID:::{self.assistant_id}")

     def add_message_to__thread(self, role, content,):
          if self.thread:
               self.client.beta.threads.messages.create(
                    thread_id=self.thread.id,
                    role = role,
                    content = content


               )
     def run_assistant(self, instructions):
          if self.thread and self.assistant:
               self.run = self.client.beta.threads.runs.create(
                    thread_id=self.thread.id,
                    assistant_id=self.assistant.id,
                    instructions=instructions,
                
               )

     def process_message(self):
          if self.thread:
               messages = self.client.beta.threads.messages.list(
                    thread_id=self.thread.id
               )
               summary = []

               last_message = messages.data[0]
               role = last_message.role
               response = last_message.content[0].text.value
               summary.append(response)

               self.summary = "\n".join(summary)

               print(f"SUMMARY----->{role.capitalize()} ==> {response}")


            #    for msg in messages:
            #         role = msg.role,
            #         content = msg.content[0].text.value,
            #         print(f"SUMMARY----->{role.capitalize(): ==> {content}}")

     def call_required_functions(self, reqired_actions):
          if not self.run:
               return
          tool_output = []

          for action in reqired_actions["tool_calls"]:
               func_name = action["function"]["name"]
               arguments = json.loads(action["function"]["arguments"])

               if func_name == "get_news":
                    output = get_news(topic=arguments["topic"])
                    print(f"STUFFF:::::{output}")
                    final_str = ""
                    for item in output:
                         final_str += "".join(item)

                    tool_output.append({"tool_call_id": action["id"],
                                        "output": final_str})
                    
               else:
                    raise ValueError(f"unknown functions{func_name}")
               
               print("submitting outputs back to assistant")
               self.client.beta.threads.runs.submit_tool_outputs(
                    thread_id=self.thread.id,
                    run_id= self.run.id,
                    tool_outputs=tool_output
               )

                         
     #for streamlit
     def get_summary(self):
          return self.summary 

     

     def wait_for_completed(self):
          if self.thread and self.run:
               while True:
                     time.sleep(5)
                     run_status = self.client.beta.threads.runs.retrieve(
                          thread_id=self.thread.id, run_id= self.run.id
                     )
                     print(f"runStatus::::{run_status.model_dump_json(indent=4)}") 

                     if run_status.status == "completed":
                          self.process_message()
                          break
                     elif run_status.status == "requires_action":
                          print("FUNCTION CALLING NOW...")
                          self.call_required_functions(
                               reqired_actions=run_status.required_action.submit_tool_outputs.model_dump()
                          )
               
      #run the steps
     def run_steps(self):
          run_steps = self.client.beta.threads.runs.steps.list(
               thread_id=self.thread.id,
               run_id=self.run.id
          )      

          print(f"Run-steps:::{run_steps}")
          return run_steps.data


def main():
    # news = get_news("generative ai")          
    # print(news[0])
    manager = AssistantManager()


    #stramlit interface:
    st.title("News Summarizer\n CREATED BY RISHABH")

    with st.form(key="user_input_form"):
         instructions = st.text_input("Enter topic")
         submit_bottons = st.form_submit_button(label="Run assistant")

         if submit_bottons:
              manager.create_assistant(
                   name="News Summarizer",
                   instructions= "you are a personal article summarizer asssitant who knows how to take a list of articles, titiles and description and knows how to write a summary",
                   tools=[
                         {
                            "type": "function",
                            "function": {
                                 "name": "get_news",
                                  "description": "Retrieves news articles for a given topic.",
                                  "parameters": {
                                    "type": "object",
                                    "properties":  {
                                        "topic": {
                                           "type": "string",
                                           "description": "The topic for the news.",
                                   }
                                   
                                },
                                "required": ["topic"] 
                            }
                          }
                        }
                   ]

 
                   

              )
              manager.create_threaad()
              # add the message  and run the asssistant
              manager.add_message_to__thread(
                   role = "user",
                   content =f"summarize the news on this topic{instructions}"
              )
              manager.run_assistant(instructions="summarize the news")

              #wait for completion
              manager.wait_for_completed()

              summary = manager.get_summary()

              st.write(summary)
              st.text("Run steps:")
              st.code(manager.run_steps(),line_numbers=True)
              

if __name__ == "__main__":
     main()
    
                    
               

               




    
