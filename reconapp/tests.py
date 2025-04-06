from django.test import TestCase, Client
from rest_framework import status
from django.urls import reverse
import pandas as pd
from io import StringIO
from .utils import normalize_dataframe, reconcile_data
from .views import validate_file_columns
from .serializers import FileUploadSerializer
from .models import UploadedFile, ReconciliationReport

class UtilityFunctionTests(TestCase):
    def test_normalize_dataframe_lowercase(self):
        # Test case for lowercase normalization
        data = {'Column A': [1, 2]}
        df = pd.DataFrame(data)
        normalized_df = normalize_dataframe(df)
        self.assertEqual(list(normalized_df.columns), ['column a'])

    def test_validate_file_columns_success(self):
        # Test case for successful validation
        data = {'Txn RefNo': [1], 'Debit': [10.0], 'Credit': [0.0]}
        df = pd.DataFrame(data)
        required_columns = ['Txn RefNo', 'Debit', 'Credit']
        try:
            validate_file_columns(df, required_columns)
            self.assertTrue(True)
        except ValueError:
            self.fail("Validation failed unexpectedly")

    def test_reconcile_data_no_discrepancies(self):
        # Test case for reconciliation with no discrepancies
        source_data = {'txn refno': [1], 'debit': [10.0], 'credit': [0.0]}
        target_data = {'txn refno': [1], 'debit': [10.0], 'credit': [0.0]}
        source_df = pd.DataFrame(source_data)
        target_df = pd.DataFrame(target_data)
        missing_source, missing_target, discrepancies, summary = reconcile_data(source_df, target_df, join_columns=['txn refno'])
        self.assertEqual(len(discrepancies), 0)
       

class FileUploadAndReconcileViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.reconcile_url = reverse('reconcile') 

    def test_file_upload_success(self):
        # Test successful file upload and reconciliation
        source_data = "Txn RefNo,Debit,Credit\n1,10.0,0.0"
        target_data = "Txn RefNo,Debit,Credit\n1,10.0,0.0"
        source_file = StringIO(source_data)
        target_file = StringIO(target_data)
        source_file.name = 'source.csv'
        target_file.name = 'target.csv'

        post_data = {'source_file': source_file, 'target_file': target_file}
        response = self.client.post(self.reconcile_url, post_data, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)

    def test_file_upload_missing_columns(self):
        # Test file upload with missing required columns
        source_data = "RefNo,Amount\n1,10.0"
        target_data = "Txn RefNo,Debit,Credit\n1,10.0,0.0"
        source_file = StringIO(source_data)
        target_file = StringIO(target_data)
        source_file.name = 'source.csv'
        target_file.name = 'target.csv'

        response = self.client.post(
            self.reconcile_url,
            {'source_file': source_file, 'target_file': target_file},
            format='multipart'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)


class ReconciliationReportModelTests(TestCase):
       def test_create_reconciliation_report(self):
        # Create dummy UploadedFile instances
        source_uploaded_file = UploadedFile.objects.create(
            file='dummy_source.csv',
            original_filename='source.csv'
        )
        target_uploaded_file = UploadedFile.objects.create(
            file='dummy_target.csv',
            original_filename='target.csv'
        )

        report = ReconciliationReport.objects.create(
            source_file=source_uploaded_file,
            target_file=target_uploaded_file,
            join_columns='txn refno',
            summary_json={'matched': 10, 'discrepancies': 2}
        )
        self.assertEqual(report.source_file.original_filename, 'source.csv')
        self.assertEqual(report.summary_json['matched'], 10)