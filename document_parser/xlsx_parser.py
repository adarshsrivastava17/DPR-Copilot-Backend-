"""XLSX parser using pandas and openpyxl."""
import pandas as pd


def parse_xlsx(file_path: str) -> dict:
    """
    Extract data from all sheets in an Excel file.
    Returns dict with keys: sheets, summary
    """
    xls = pd.ExcelFile(file_path)
    sheets = {}

    for sheet_name in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet_name)
        # Convert to list of dicts for JSON serialization
        records = df.fillna("").to_dict(orient="records")
        columns = list(df.columns)
        text_repr = df.to_string(index=False)

        sheets[sheet_name] = {
            "columns": columns,
            "records": records,
            "row_count": len(df),
            "text": text_repr,
        }

    return {
        "sheets": sheets,
        "sheet_names": list(xls.sheet_names),
        "total_sheets": len(xls.sheet_names),
    }
