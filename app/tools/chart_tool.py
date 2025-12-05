from typing import Annotated
import matplotlib.pyplot as plt
import json
from pathlib import Path

def create_chart(
    chart_type: Annotated[str, "Type of chart: 'line', 'bar', 'scatter', or 'pie'"],
    data: Annotated[str, "JSON string with 'x_values', 'y_values', and 'labels' keys"],
    title: Annotated[str, "Chart title"],
    x_label: Annotated[str, "X-axis label"] = "X",
    y_label: Annotated[str, "Y-axis label"] = "Y",
    filename: Annotated[str, "Output filename"] = "chart.png"
) -> str:
    """
    Create a chart based on provided data and save it as an image.
    
    Args:
        chart_type: Type of chart ('line', 'bar', 'scatter', 'pie')
        data: JSON string containing chart data
        title: Chart title
        x_label: X-axis label
        y_label: Y-axis label
        filename: Output filename for the chart
    
    Returns:
        Status message with file path or error
    """
    try:
        # Parse the data
        chart_data = json.loads(data)
        x_values = chart_data.get("x_values", [])
        y_values = chart_data.get("y_values", [])
        labels = chart_data.get("labels", [])
        
        # Create figure and axis
        plt.figure(figsize=(10, 6))
        
        if chart_type == "line":
            plt.plot(x_values, y_values, marker='o', linewidth=2, markersize=8)
            plt.xlabel(x_label)
            plt.ylabel(y_label)
            
        elif chart_type == "bar":
            plt.bar(x_values, y_values, color='steelblue', alpha=0.8)
            plt.xlabel(x_label)
            plt.ylabel(y_label)
            if labels:
                plt.xticks(range(len(labels)), labels, rotation=45, ha='right')
                
        elif chart_type == "scatter":
            plt.scatter(x_values, y_values, s=100, alpha=0.6, c='steelblue')
            plt.xlabel(x_label)
            plt.ylabel(y_label)
            
        elif chart_type == "pie":
            plt.pie(y_values, labels=labels, autopct='%1.1f%%', startangle=90)
            plt.axis('equal')
            
        else:
            return json.dumps({
                "error": f"Unknown chart type: {chart_type}",
                "supported_types": ["line", "bar", "scatter", "pie"]
            })
        
        plt.title(title, fontsize=14, fontweight='bold', pad=20)
        plt.tight_layout()
        
        # Ensure output directory exists
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / filename
        
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return json.dumps({
            "status": "success",
            "message": f"Chart created successfully",
            "file_path": str(output_path),
            "chart_type": chart_type,
            "title": title
        }, indent=2)
        
    except json.JSONDecodeError as e:
        return json.dumps({
            "error": f"Invalid JSON data: {str(e)}",
            "hint": "Data should be JSON with 'x_values', 'y_values', and optionally 'labels'"
        })
    except Exception as e:
        return json.dumps({
            "error": f"Chart creation failed: {str(e)}"
        })