### introduction


this project uses python 3.12 so you have to make a py -3.12 venv. 

for the LLM config it uses Llama 3.1 using Ollama

it produces charts based on data inputs that it can either pull from yahoo finance using the 
yfinance library. or from a csv file in the input folder. 

I have provided a file that contains multiple use-cases with the output and input from the user and agents respectively. including a full message log from one run. 


to run the code, be in the root folder and do a pip install -r requirements.txt into you venv
run your venv and then do

### run command

python -m app.agent.agent


from here you can input a user prompt. you could also manually add more csv files to the input folder and get data charts from them. after running you can do a new prompt or quit.