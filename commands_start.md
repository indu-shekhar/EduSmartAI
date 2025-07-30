# change the system policy to allow running scripts
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
# start the environment
.\venv\Scripts\Activate.ps1
# run the development server
.\scripts\run_dev.ps1 or flask run

# to kill all of the running python processes
taskkill /f /im python.exe

# to run the document ingestion script
python ingest.py --refresh

# to run the flask app
.\.venv\Scripts\Activate.ps1
"$env:FLASK_APP = "app"
flask run --port=8000

# check all of content of the books folder: 
Get-ChildItem books -Filter "*.pdf" | Select-Object Name,Length
""
"####
---------------
# running on the macos setup
 for creating the environment 
 conda init zsh
 # now to not have the terminal always start with conda base environment
 conda config --set auto_activate_base false
 conda create --name edusmart python=3.11
 conda activate edusmart

 # for deactivating : 
 conda deactivate

 # but just for setting up conda 
 run the conda init  and then restart

 # install requirements (remove windows-specific packages first)
 pip install -r requirements.txt
 
 # if there are ChromaDB compatibility issues, rebuild the vector database:
 rm -rf storage/240d91de-f204-4136-9836-eb6983eb7950 storage/chroma.sqlite3
 python ingest.py --refresh
 
 # then run the app
 flask run

 # here are few things that we need to install and make the conda working
    conda install python=3.11