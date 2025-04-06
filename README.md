# Reconciliation Application
Reconciliation API with DRF 
## Overview:
* This is an API that takes two csv files, the source and target file.
* It then perfoms a reconciliation to detect discripancies, the mimatching values in both files.
* Once reconciliation is done, the user can the down the report in either csv, html or json file types.
## Process Flow:
1. The user uploads two csv file, source file and target file.
2. The system performs validation:
   * File type validation.
   * Required columns validation (Txn Refno- unique transaction refrence number, Debit and Credit columns)
   * data normalization to align cases to lower, removes white spaces, date etc.
3. The system perform reconciliation:
   * The system is following the double entry accounting princcipal (For a transaction to be considered valid, there must be a debit and a credit entry)
   * The system check missing values in both target and source files.
   * The system identifies duplicated transactions among other discrepancies.
4. Once reconciliation is done, a report is generated, the user can then download the files in both CSV, HTML and JSON formats.

## Sample Files:
 * ![Source file](https://github.com/KolaKodhek/Reconciliation/blob/main/sourcefile.csv)
 * ![Target file](https://github.com/KolaKodhek/Reconciliation/blob/main/targetfile.csv)
 * The Reqired columns are Txn Refno, Debit and Credit
   * ![image](https://github.com/user-attachments/assets/2d3a0516-1db3-4991-8f24-e8ac4387df7b)
## Installation Process:
```
# Clone the repository
git clone (https://github.com/KolaKodhek/Reconciliation.git)
cd reconciliation

# Set up virtual environment
pipenv shell

# Install dependencies
python -m pip install Django
pip install djangorestframework
pip install markdown 
pip install pandas
pip install beautifulsoup4
pip install drf-spectacular

# Run migrations
python manage.py makemigrations
python manage.py migrate

# Run the server
python manage.py runserver
```
## API Endpoint:
* When you run the server in dafault port, you will access the application via ``` http://127.0.0.1:8000/ ```
* To upload the files and perfomr reconciliation, the url is POST ``` /api/reconcile/ ```
* To view all the reconciliation reports: GET ```/api/reports ```
* To view the reports (json), use: GET  ```/api/reports/1 ``` 
* Note that you are passing the report id which you can get through the successful reconciliation response or through the view all reports endpoint.
* For CSV and HTML, you need to pass the format type parameter after the report id :GET ```http://127.0.0.1:8000/api/reports/1?type=html```
* To test via the browser, simply add ```/api/schema/swagger-ui/# ``` after you server port, ie ```http://127.0.0.1:8000/api/schema/swagger-ui/#/```
* To run unit test, use ``` python manage.py test reconapp```
## Limitations:
* The system accepts only csv file types for source and target files
* Txn Refno, Debit and Credit columns must be valid columns in the files uploaded



