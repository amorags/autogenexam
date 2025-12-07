import os
import json
import pandas as pd

def load_csv(filename: str) -> str:
    """
    Load CSV from input/filename and return JSON describing columns and data.
    """
    try:
        input_path = os.path.join("input", filename)
        if not os.path.exists(input_path):
            return json.dumps({"error": f"File '{filename}' not found in input/ folder."})

        df = pd.read_csv(input_path)
        return json.dumps({
            "source": "csv",
            "filename": filename,
            "columns": list(df.columns),
            "data": df.to_dict(orient="list")
        })
    except Exception as e:
        return json.dumps({"error": str(e)})