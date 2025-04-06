from django.urls import path
from .views import FileUploadAndReconcileView, ReconciliationReportDetailView,ReconiliationReportListView


urlpatterns = [
    # This is the endpoint for file upload and reconciliation
    path('reconcile/', FileUploadAndReconcileView.as_view(), name='reconcile'), 
    
    # This is the endpoint for retrieving reconciliation reports, we use it to retrieve and download a specific report report.
    path('reports/<int:id>', ReconciliationReportDetailView.as_view({'get': 'retrieve'}), name='reconciliation-report-detail'),
    
    # This is the endpoint for retrieving all reconciliation reports
    path('reports', ReconiliationReportListView.as_view(), name='reportlist'),

]