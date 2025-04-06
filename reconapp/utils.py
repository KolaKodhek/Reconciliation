import pandas as pd
import logging
import io
from bs4 import BeautifulSoup # type: ignore
from typing import Union, List, Dict, Optional, Any

logger = logging.getLogger(__name__)

def normalize_dataframe(
    dataframe: pd.DataFrame,
    date_fmt: Optional[str] = None,
    ignore_case: bool = True,
    strip_whitespace: bool = True,
    fill_na_value: Optional[Any] = None
) -> pd.DataFrame:
    """Normalize a pandas DataFrame, including column names."""
    df = dataframe.copy()

    # Normalize column names
    if ignore_case:
        df.columns = [col.lower() for col in df.columns]
    if strip_whitespace:
        df.columns = [col.strip() for col in df.columns]

    # Normalize data within object columns
    for column in df.select_dtypes(include='object').columns:
        if strip_whitespace:
            df[column] = df[column].str.strip()
        if ignore_case:
            df[column] = df[column].str.lower()

        if date_fmt:
            try:
                df[column] = pd.to_datetime(df[column], format=date_fmt, errors='coerce')
            except Exception as e:
                logger.warning(f"Date conversion failed for column '{column}': {e}")

    if fill_na_value is not None:
        df = df.fillna(fill_na_value)

    return df

def safe_dataframe(data: Union[pd.DataFrame, List[Dict], Dict, None]) -> pd.DataFrame:
    """Convert data safely to a DataFrame."""
    if isinstance(data, pd.DataFrame):
        return data
    elif isinstance(data, list):
        return pd.DataFrame(data)
    
    elif isinstance(data, dict):
        return pd.DataFrame([data])
    elif data is None:
        return pd.DataFrame()
    else:
        logger.warning(f"Unsupported type for DataFrame conversion: {type(data)}")
        return pd.DataFrame()

class ReportFormatter:
    def __init__(
        self,
        summary: Optional[Dict] = None,
        missing_source: Optional[Union[pd.DataFrame, List[Dict]]] = None,
        missing_target: Optional[Union[pd.DataFrame, List[Dict]]] = None,
        discrepancies: Optional[Union[pd.DataFrame, List[Dict]]] = None
    ):
        self.summary = summary
        self.missing_source = safe_dataframe(missing_source)
        self.missing_target = safe_dataframe(missing_target)
        self.discrepancies = safe_dataframe(discrepancies)
        
    def to_csv(self) -> str:
        try:
            output = io.StringIO()
            combined_data = pd.DataFrame()
            logger.info(f"Combined CSV Data:\n{combined_data.head()}")
            for df, section in [
                (self.missing_source, "Missing in Source"),
                (self.missing_target, "Missing in Target"),
                (self.discrepancies, "Discrepancies")
            ]:
                if not df.empty:
                    temp_df = df.copy()
                    temp_df.insert(0, "Section", section)
                    combined_data = pd.concat([combined_data, temp_df], ignore_index=True)

            combined_data.to_csv(output, index=False)
            return output.getvalue()
        except Exception as e:
            logger.error(f"Error in to_csv: {e}")
            return f"Error: {e}"

    def to_html(self) -> str:
        try:
            html_report = ""

            def process_df(df: pd.DataFrame, title: str) -> str:
                if not df.empty:
                    html = f"<h3>{title}</h3>{df.to_html(index=False)}"
                    return BeautifulSoup(html, 'html.parser').prettify()
                return ""

            html_report += process_df(self.missing_source, "Missing in Source")
            html_report += process_df(self.missing_target, "Missing in Target")
            html_report += process_df(self.discrepancies, "Discrepancies")

            return html_report
        except Exception as e:
            logger.error(f"Error generating HTML: {e}")
            return f"<p>Error generating HTML: {e}</p>"



def reconcile_data(
    source_df: pd.DataFrame,
    target_df: pd.DataFrame,
    join_columns: List[str],
    ignore_columns: Optional[List[str]] = None,
    debit_column: str = 'debit',  
    credit_column: str = 'credit'
) -> tuple[List[dict], List[dict], List[dict], dict]:
    """
    _This is the function that does the reconciliation.
    _We are utilizing pandas to help us merge the source file and the target file. 
    _We then start by looking for records that are there in source but are not in target
    _Then we follow by checking the once that are mising in source but are in target
    _We then check for discrepancies:
        1: We follow the double entry accounting rule to concider a transaction valid, that is if a transaction is a
            debit in source,it should be a credit in target and vice versa.
        2: We check for duplicates in both source and target.
        3: We check for any inconsistency of the transaction, be it date, amount, etc in both source and target.
   """
    if not join_columns:
        raise ValueError("Join columns (unique transaction number) must be specified.")
    if len(join_columns) != 1:
        raise ValueError("Only one join column (unique transaction number) should be specified for this type of reconciliation.")
    join_column = join_columns[0]

    for col in [join_column, debit_column, credit_column]:
        if col not in source_df.columns or col not in target_df.columns:
            raise ValueError(f"Required column '{col}' not found in both DataFrames after normalization.")

    # Missing in target
    merged_left = pd.merge(source_df, target_df, on=join_column, how='left', indicator=True, suffixes=('_source', '_target'))
    missing_in_target_df = merged_left[merged_left['_merge'] == 'left_only'].drop(columns=['_merge'])
    missing_in_target = missing_in_target_df.to_dict('records')


    #Missing in source
    merged_right = pd.merge(target_df, source_df, on=join_column, how='left', indicator=True, suffixes=('_target', '_source'))
    missing_in_source_df = merged_right[merged_right['_merge'] == 'left_only'].drop(columns=['_merge'])
    missing_in_source = missing_in_source_df.to_dict('records')

    common_records = pd.merge(source_df, target_df, on=join_columns, suffixes=('_source', '_target'))
    discrepancies = []
    # Identify duplicate transaction numbers within each DataFrame
    source_duplicates = source_df[source_df.duplicated(subset=join_columns, keep=False)][join_columns[0]].tolist()
    target_duplicates = target_df[target_df.duplicated(subset=join_columns, keep=False)][join_columns[0]].tolist()

    # Add duplicate transaction numbers as a discrepancy
    for txn in set(source_duplicates + target_duplicates):
        discrepancy_record = {join_columns[0]: txn}
        discrepancy_details = {}
        if txn in source_duplicates:
            discrepancy_details["duplicate_in_source"] = True
        if txn in target_duplicates:
            discrepancy_details["duplicate_in_target"] = True
        discrepancy_record["discrepancies"] = discrepancy_details
        discrepancies.append(discrepancy_record)
        for _, row in common_records.iterrows():
            transaction_number = row[join_columns[0]]
            discrepancy_details = {}
            is_discrepancy = False

        source_debit = row.get(f"{debit_column}_source", 0.0)
        source_credit = row.get(f"{credit_column}_source", 0.0)
        target_debit = row.get(f"{debit_column}_target", 0.0)
        target_credit = row.get(f"{credit_column}_target", 0.0)

        source_amount = source_debit if pd.notna(source_debit) and source_debit != 0 else source_credit if pd.notna(source_credit) else None
        target_amount = target_debit if pd.notna(target_debit) and target_debit != 0 else target_credit if pd.notna(target_credit) else None

        source_is_debit = pd.notna(source_debit) and source_debit != 0
        source_is_credit = pd.notna(source_credit) and source_credit != 0
        target_is_debit = pd.notna(target_debit) and target_debit != 0
        target_is_credit = pd.notna(target_credit) and target_credit != 0

        # Check Debit/Credit rule
        if source_is_debit and not target_is_credit:
            discrepancy_details["debit_credit_mismatch"] = "Source is Debit, Target is not Credit"
            is_discrepancy = True
        elif source_is_credit and not target_is_debit:
            discrepancy_details["debit_credit_mismatch"] = "Source is Credit, Target is not Debit"
            is_discrepancy = True
        elif not source_is_debit and not source_is_credit and (target_is_debit or target_is_credit):
            discrepancy_details["debit_credit_mismatch"] = "Source has no amount, Target has amount"
            is_discrepancy = True
        elif (source_is_debit or source_is_credit) and not target_is_debit and not target_is_credit:
            discrepancy_details["debit_credit_mismatch"] = "Source has amount, Target has no amount"
            is_discrepancy = True

        # Check Amount discrepancy
        if source_amount is not None and target_amount is not None and source_amount != target_amount:
            discrepancy_details["amount_mismatch"] = {"source": source_amount, "target": target_amount}
            is_discrepancy = True
        elif (source_amount is None and target_amount is not None) or (source_amount is not None and target_amount is None):
            # This case should ideally be caught by the debit/credit mismatch check,
            # but adding it for robustness.
            discrepancy_details["amount_mismatch"] = {"source": source_amount, "target": target_amount}
            is_discrepancy = True

        # Check for other column discrepancies
        for col in source_df.columns:
            if col not in join_columns and col not in [debit_column, credit_column] and (ignore_columns is None or col not in ignore_columns):
                source_value = row.get(f"{col}_source")
                target_value = row.get(f"{col}_target")
                if source_value != target_value:
                    discrepancy_details.setdefault("other_discrepancies", {})[col] = {"source": source_value, "target": target_value}
                    is_discrepancy = True

        if is_discrepancy:
            discrepancy_record = {join_columns[0]: transaction_number}
            discrepancy_record["discrepancies"] = discrepancy_details
            discrepancies.append(discrepancy_record)
    summary = {
        'missing_in_target_count': len(missing_in_target),
        'missing_in_source_count': len(missing_in_source),
        'discrepancy_count': len(discrepancies),
    }

    return missing_in_source, missing_in_target, discrepancies, summary
    