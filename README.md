# Reconciliation Application
Reconciliation API with DRF 
## Overview
* This is an API that takes two csv files, the source and target file.
* It then perfoms a reconciliation to detect discripancies, the mimatching values in both files.
* Once reconciliation is done, the user can the down the report in either csv, html or json file types.
## Process Flow
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

## Sample Files
