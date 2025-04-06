from rest_framework import serializers
from .models import  ReconciliationReport

class FileUploadSerializer(serializers.Serializer):
    source_file = serializers.FileField(help_text="Upload the source CSV file.")
    target_file = serializers.FileField(help_text="Upload the target CSV file.")
    date_format = serializers.CharField(required=False, allow_blank=True,
                                       help_text="Optional date format string (e.g., '%Y-%m-%d').")
    ignore_case = serializers.BooleanField(default=True, help_text="Ignore case sensitivity during comparison.")
    strip_whitespace = serializers.BooleanField(default=True, help_text="Remove leading/trailing spaces.")
    ignore_columns = serializers.CharField(required=False, allow_blank=True,
                                           help_text="Optional comma-separated list of columns to ignore during discrepancy checks.")

    
    def validate_ignore_columns(self, value):
        return [col.strip() for col in value.split(',')] if value else []
    
    def validate(self, data):
        source_file = data.get('source_file')
        target_file = data.get('target_file')
        if source_file and not source_file.name.endswith('.csv'):
            raise serializers.ValidationError("Source file must be a CSV file.")
        if target_file and not target_file.name.endswith('.csv'):
            raise serializers.ValidationError("Target file must be a CSV file.")
        return data

class ReconciliationReportSerializer(serializers.ModelSerializer):
    source_file_name = serializers.CharField(source='source_file.original_filename', read_only=True)
    target_file_name = serializers.CharField(source='target_file.original_filename', read_only=True)

    class Meta:
        model = ReconciliationReport
        fields = '__all__'
        read_only_fields = ['reconciliation_timestamp', 'source_file', 'target_file', 'summary_json',
                            'missing_in_source_json', 'missing_in_target_json', 'discrepancies_json']