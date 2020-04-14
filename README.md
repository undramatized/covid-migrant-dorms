# covid-migrant-dorms
Data Visualisation for COVID19 Migrant Dorms

### Usage
- Setup python virtual environment
- Install packages in requirements.txt
```
$ pip install -r requirements.txt
```
- Add your GoogleAPI credentials JSON file as 'google_secrets.json' in the root folder
- Add a `.env` file in the root folder with the following:
```
export GOOGLE_APPLICATION_CREDENTIALS = google_secrets.json
```
- Run application
```
$ python app.py
```
- View app in the browser
http://127.0.0.1:8050/
