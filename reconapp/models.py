from django.db import models
from django.utils import timezone

class UploadedFile(models.Model):
    """_This is the Fileupload model.
       _We simply need the path we will upload the file to, the name of the file and when it was uploaded.
    """
    file = models.FileField(upload_to='reconciliation_uploads/')
    upload_timestamp = models.DateTimeField(default=timezone.now)
    original_filename = models.CharField(max_length=255)

    def __str__(self):
        return self.original_filename

class ReconciliationReport(models.Model):
    """
        _This is the ReconciliationReport model._
        _It has a one-to-one relationship with the UploadedFile model.
        _It has a one-to-one relationship with the SummaryReport model.

    """
    source_file = models.ForeignKey(UploadedFile, related_name='source_reports', on_delete=models.SET_NULL, null=True)
    target_file = models.ForeignKey(UploadedFile, related_name='target_reports', on_delete=models.SET_NULL, null=True)
    reconciliation_timestamp = models.DateTimeField(default=timezone.now)
    join_columns = models.CharField(max_length=255) #This is the column that will be used to join the source and target files for reconciliation
    ignore_columns = models.CharField(max_length=255, blank=True, null=True)
    summary_json = models.JSONField()
    missing_in_source_json = models.JSONField(null=True, blank=True)
    missing_in_target_json = models.JSONField(null=True, blank=True)
    discrepancies_json = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"Report for {self.source_file.original_filename} vs {self.target_file.original_filename} on {self.reconciliation_timestamp}"