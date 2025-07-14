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
$env:FLASK_APP = "app"
flask run --port=8000

# check all of content of the books folder: 
Get-ChildItem books -Filter "*.pdf" | Select-Object Name,Length