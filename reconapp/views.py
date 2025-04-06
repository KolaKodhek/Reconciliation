from typing import List
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status,viewsets
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import generics
from .serializers import FileUploadSerializer, ReconciliationReportSerializer
from .models import UploadedFile, ReconciliationReport
from .utils import normalize_dataframe, reconcile_data, ReportFormatter
from django.conf import settings
from django.http import HttpResponse
from django.template.loader import render_to_string
import pandas as pd
import math
import logging
import json
import math
import numpy as np
from drf_spectacular.utils import extend_schema # type: ignore


logger = logging.getLogger(__name__)



class FileUploadAndReconcileView(APIView):
    parser_classes = (MultiPartParser, FormParser)
    @extend_schema(
        request={
            'multipart/form-data': {
                'type': 'object',
                'properties': {
                    'source_file': {
                        'type': 'string',
                        'format': 'binary',
                        'description': 'The source CSV file to upload.'
                    },
                    'target_file': {
                        'type': 'string',
                        'format': 'binary',
                        'description': 'The target CSV file to upload.'
                    },
                    
                },
                'required': ['source_file', 'target_file'],
            }
        },
        responses={
            200: 'application/json',
            400: 'application/json',
            500: 'application/json',
        }
    )
    
    def post(self, request, *args, **kwargs):
        
        """
        Uploads two CSV files (source and target) and performs reconciliation.

        Request Data:
            - source_file: The source CSV file.
            - target_file: The target CSV file.
            - ignore_case (optional, default=True): Whether to ignore case in column names.
            - strip_whitespace (optional, default=True): Whether to strip whitespace from column names.
            - ignore_columns (optional): Comma-separated list of columns to ignore during reconciliation.

        Response (on success - status 200):
            - message: "Reconciliation successful."
            - report_id: The ID of the generated reconciliation report.
            - summary: A summary of the reconciliation.
            - missing_in_target: List of records missing in the target file.
            - missing_in_source: List of records missing in the source file.
            - discrepancies: List of identified discrepancies.

        Response (on error - status 400 or 500):
            - error: A description of the error.
        """
        serializer = FileUploadSerializer(data=request.data)
        if serializer.is_valid():
            source_file_uploaded = serializer.validated_data['source_file']
            target_file_uploaded = serializer.validated_data['target_file']
            date_format = serializer.validated_data.get('date_format')
            ignore_case = serializer.validated_data.get('ignore_case', True)
            strip_whitespace = serializer.validated_data.get('strip_whitespace', True)
            ignore_columns = [col.strip() for col in serializer.validated_data.get('ignore_columns', '').split(',')] if serializer.validated_data.get('ignore_columns') else None

            required_columns = ['Txn RefNo', 'Debit', 'Credit']
            join_columns = ['txn refno']  # We have hardcoded the column we will use to join the two data sources

            try:
                # Save uploaded files
                source_file_instance = UploadedFile.objects.create(
                    file=source_file_uploaded,
                    original_filename=source_file_uploaded.name
                )

                target_file_instance = UploadedFile.objects.create(
                    file=target_file_uploaded,
                    original_filename=target_file_uploaded.name
                )

                # Read CSV files into pandas DataFrames
                source_df = pd.read_csv(source_file_instance.file.path)
                target_df = pd.read_csv(target_file_instance.file.path)

                logger.info(f"Source DataFrame Columns (Original): {source_df.columns.tolist()}")
                logger.info(f"Target DataFrame Columns (Original): {target_df.columns.tolist()}")

                # Validate required columns
                validate_file_columns(source_df, required_columns)
                validate_file_columns(target_df, required_columns)

                for df in [source_df, target_df]:
                    for col in ['Debit', 'Credit']:
                        if col in df.columns:
                            df[col] = pd.to_numeric(df[col], errors='coerce')
                            logger.info(f"Successfully converted column '{col}' to numeric with errors='coerce'.")
                        else:
                            logger.warning(f"Column '{col}' not found for numeric conversion.")
                # Data normalization
                normalized_source_df = normalize_dataframe(source_df.copy(), date_format, ignore_case, strip_whitespace)
                normalized_target_df = normalize_dataframe(target_df.copy(), date_format, ignore_case, strip_whitespace)

                logger.info(f"Source DataFrame Columns (Normalized): {normalized_source_df.columns.tolist()}")
                logger.info(f"Target DataFrame Columns (Normalized): {normalized_target_df.columns.tolist()}")
                logger.info(f"Join Columns (Hardcoded): {join_columns}")
                logger.info(f"Ignore Columns Received: {ignore_columns}")

                # Perform reconciliation
                missing_in_source, missing_in_target, discrepancies, summary = reconcile_data(
                    normalized_source_df,
                    normalized_target_df,
                    join_columns=join_columns,
                    ignore_columns=ignore_columns,
                    debit_column='debit',
                    credit_column='credit'
                )

                logger.info(f"Type of missing_in_source: {type(missing_in_source)}")
                logger.info(f"Content of missing_in_source: {missing_in_source}")

                def clean_floats(obj):
                    if isinstance(obj, dict):
                        return {k: clean_floats(v) for k, v in obj.items()}
                    elif isinstance(obj, list):
                        return [clean_floats(item) for item in obj]
                    elif isinstance(obj, float):
                        if math.isnan(obj) or math.isinf(obj):
                            return None
                    elif isinstance(obj, (pd.Timestamp, pd.NaT.__class__)):
                        if pd.isnull(obj):
                            return None
                        return obj.isoformat()  # convert Timestamp to ISO string
                    elif isinstance(obj, np.generic):
                        return obj.item()
                    return obj

                missing_in_source = clean_floats(missing_in_source)
                missing_in_target = clean_floats(missing_in_target)
                
                # Save reconciliation report
                report = ReconciliationReport.objects.create(
                    source_file=source_file_instance,
                    target_file=target_file_instance,
                    join_columns=','.join(join_columns),
                    ignore_columns=','.join(ignore_columns) if ignore_columns else None,
                    summary_json=summary,
                    missing_in_source_json=json.dumps(missing_in_source),
                    missing_in_target_json=json.dumps(missing_in_target),
                    discrepancies_json=discrepancies,
                )

                return Response({
                    'message': 'Reconciliation successful.',
                    'report_id': report.id,
                    'summary': summary,
                    'missing_in_target': missing_in_target,
                    'missing_in_source': missing_in_source,
                    'discrepancies': discrepancies,
                }, status=status.HTTP_200_OK)

            except FileNotFoundError:
                return Response({'error': 'One or both of the uploaded files could not be found.'}, status=status.HTTP_400_BAD_REQUEST)
            except pd.errors.EmptyDataError:
                return Response({'error': 'One or both of the uploaded files are empty.'}, status=status.HTTP_400_BAD_REQUEST)
            except pd.errors.ParserError:
                return Response({'error': 'Error parsing one or both of the CSV files. Please ensure they are valid CSV.'}, status=status.HTTP_400_BAD_REQUEST)
            except ValueError as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                logger.exception("An unexpected error occurred during reconciliation.")
                return Response({'error': 'An unexpected error occurred during reconciliation.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ReconiliationReportListView(generics.ListAPIView):
    queryset = ReconciliationReport.objects.all()
    serializer_class = ReconciliationReportSerializer 
class ReconciliationReportDetailView(viewsets.ViewSet):
    queryset = ReconciliationReport.objects.all()
    serializer_class = ReconciliationReportSerializer 
    type = None
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.queryset.filter(id=kwargs['id']).first()
        if instance is None:
            return Response({'error': 'Reconciliation report not found.'}, status=status.HTTP_404_NOT_FOUND)
      
        summary = instance.summary_json or {}
        missing_in_source = instance.missing_in_source_json or []
        missing_in_target = instance.missing_in_target_json or []
        discrepancies = instance.discrepancies_json or []
        
 
        #print(type(json.loads(missing_in_source)))
        formatter = ReportFormatter(
             summary=summary,
             missing_source=json.loads(missing_in_source),
             missing_target=json.loads(missing_in_target),
             discrepancies=discrepancies
        )
     
        
         #format_type = request.query_params.get('format', 'json').lower()
        format_type = request.query_params.get('type', 'json').lower()

        logger.info(f"Format requested: {format_type}")
        logger.info("Inside retrieve() method")
        logger.info(f"Request query params: {request.query_params}")

        #print(request.query_params.get('format', 'json').lower(),"The request format parameter")
        
        if format_type == "csv":
            try:
                csv_data = formatter.to_csv()
                response = HttpResponse(csv_data, content_type='text/csv')
                report_id = kwargs.get('id')  # Get the ID from the URL parameters
                filename = f"Reconciliation_Report_Idno_{report_id}.csv"
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
                return response
            except Exception as e:
                logger.error(f"Error generating CSV: {e}")
                return HttpResponse(f"Error generating CSV: {e}", status=500)

            #return HttpResponse(csv_data, content_type='text/csv')

        elif format_type == "html":
            try:
                html_data = formatter.to_html()
                report_id = kwargs.get('id') 
                response = HttpResponse(html_data, content_type='text/html')
                filename = f"Reconciliation_Report_Idno_{report_id}.html"
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
                return response
            except Exception as e:
                logger.error(f"Error generating HTML: {e}")
                return HttpResponse(f"<p>Error generating HTML: {e}</p>", status=500)


        else:
            return Response({
                    "summary": summary,
                    "missing_in_source": missing_in_source,
                    "missing_in_target": missing_in_target,
                    "discrepancies": discrepancies,
                })

def validate_file_columns(df: pd.DataFrame, required_columns: List[str]):
    """Validates if a DataFrame contains all the required columns (case-insensitive)."""
    df_lower_columns = {col.lower() for col in df.columns}
    missing_columns = []
    for req_col in required_columns:
        found = False
        for df_col_lower in df_lower_columns:
            if req_col.lower() == df_col_lower:
                found = True
                break
        if not found:
            missing_columns.append(req_col)
    if missing_columns:
        raise ValueError(f"Missing required columns (case-insensitive): {', '.join(missing_columns)}")