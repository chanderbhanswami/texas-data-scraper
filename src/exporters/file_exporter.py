"""
File export utilities for multiple formats
With checksum generation for data integrity
"""
import json
import csv
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
from src.utils.logger import get_logger

# Import checksum utility
try:
    from src.utils.checksum import generate_export_checksum, verify_export_file
    CHECKSUM_AVAILABLE = True
except ImportError:
    CHECKSUM_AVAILABLE = False

logger = get_logger(__name__)


class FileExporter:
    """Export data to various file formats with optional checksum verification"""
    
    def __init__(self, export_dir: Path, generate_checksums: bool = True):
        """
        Initialize file exporter
        
        Args:
            export_dir: Directory for exported files
            generate_checksums: Whether to generate checksum files
        """
        self.export_dir = Path(export_dir)
        self.export_dir.mkdir(parents=True, exist_ok=True)
        self.generate_checksums = generate_checksums and CHECKSUM_AVAILABLE
        
    def export_json(self, data: List[Dict], filename: str, indent: int = 2) -> Path:
        """
        Export data to JSON file
        
        Args:
            data: Data to export
            filename: Output filename
            indent: JSON indentation
            
        Returns:
            Path to exported file
        """
        filepath = self.export_dir / filename
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=indent, ensure_ascii=False)
            
            # Generate checksum
            if self.generate_checksums:
                generate_export_checksum(filepath, len(data))
            
            logger.info(f"Exported {len(data)} records to JSON: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Error exporting JSON: {e}")
            raise
    
    def export_csv(self, data: List[Dict], filename: str, 
                   encoding: str = 'utf-8-sig') -> Path:
        """
        Export data to CSV file
        
        Args:
            data: Data to export
            filename: Output filename
            encoding: File encoding (utf-8-sig for Excel compatibility)
            
        Returns:
            Path to exported file
        """
        filepath = self.export_dir / filename
        
        if not data:
            logger.warning("No data to export")
            return filepath
        
        try:
            # Get all unique keys from all records
            fieldnames = set()
            for record in data:
                fieldnames.update(record.keys())
            fieldnames = sorted(fieldnames)
            
            with open(filepath, 'w', newline='', encoding=encoding) as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(data)
            
            # Generate checksum
            if self.generate_checksums:
                generate_export_checksum(filepath, len(data))
            
            logger.info(f"Exported {len(data)} records to CSV: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Error exporting CSV: {e}")
            raise
    
    def export_excel(self, data: List[Dict], filename: str, 
                     sheet_name: str = "Data") -> Path:
        """
        Export data to Excel file
        
        Args:
            data: Data to export
            filename: Output filename
            sheet_name: Excel sheet name
            
        Returns:
            Path to exported file
        """
        filepath = self.export_dir / filename
        
        if not data:
            logger.warning("No data to export")
            return filepath
        
        try:
            # Convert to DataFrame
            df = pd.DataFrame(data)
            
            # Export to Excel with formatting
            with pd.ExcelWriter(filepath, engine='xlsxwriter') as writer:
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                
                # Get workbook and worksheet
                workbook = writer.book
                worksheet = writer.sheets[sheet_name]
                
                # Add header formatting
                header_format = workbook.add_format({
                    'bold': True,
                    'bg_color': '#4472C4',
                    'font_color': 'white',
                    'border': 1
                })
                
                # Apply header format
                for col_num, value in enumerate(df.columns.values):
                    worksheet.write(0, col_num, value, header_format)
                
                # Auto-adjust column widths
                for i, col in enumerate(df.columns):
                    max_length = max(
                        df[col].astype(str).apply(len).max(),
                        len(str(col))
                    )
                    worksheet.set_column(i, i, min(max_length + 2, 50))
            
            # Generate checksum
            if self.generate_checksums:
                generate_export_checksum(filepath, len(data))
            
            logger.info(f"Exported {len(data)} records to Excel: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Error exporting Excel: {e}")
            raise
    
    def export_all_formats(self, data: List[Dict], base_filename: str) -> Dict[str, Path]:
        """
        Export data to all formats (JSON, CSV, Excel)
        
        Args:
            data: Data to export
            base_filename: Base filename (without extension)
            
        Returns:
            Dictionary mapping format to filepath
        """
        results = {}
        
        try:
            # Export JSON
            json_path = self.export_json(data, f"{base_filename}.json")
            results['json'] = json_path
            
            # Export CSV
            csv_path = self.export_csv(data, f"{base_filename}.csv")
            results['csv'] = csv_path
            
            # Export Excel
            excel_path = self.export_excel(data, f"{base_filename}.xlsx")
            results['excel'] = excel_path
            
            logger.info(f"Exported data to all formats: {base_filename}")
            return results
            
        except Exception as e:
            logger.error(f"Error exporting to multiple formats: {e}")
            raise
    
    def load_json(self, filepath: Path, verify: bool = True) -> List[Dict]:
        """Load data from JSON file with optional checksum verification"""
        try:
            # Verify checksum first if requested
            if verify and CHECKSUM_AVAILABLE:
                is_valid, msg = verify_export_file(filepath)
                if not is_valid:
                    logger.warning(f"Checksum verification failed for {filepath}: {msg}")
            
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            logger.info(f"Loaded {len(data)} records from JSON: {filepath}")
            return data
            
        except Exception as e:
            logger.error(f"Error loading JSON: {e}")
            raise
    
    def load_csv(self, filepath: Path, verify: bool = True) -> List[Dict]:
        """Load data from CSV file with optional checksum verification"""
        try:
            # Verify checksum first if requested
            if verify and CHECKSUM_AVAILABLE:
                is_valid, msg = verify_export_file(filepath)
                if not is_valid:
                    logger.warning(f"Checksum verification failed for {filepath}: {msg}")
            
            with open(filepath, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                data = list(reader)
            
            logger.info(f"Loaded {len(data)} records from CSV: {filepath}")
            return data
            
        except Exception as e:
            logger.error(f"Error loading CSV: {e}")
            raise
    
    def load_excel(self, filepath: Path, sheet_name: str = None, verify: bool = True) -> List[Dict]:
        """Load data from Excel file with optional checksum verification"""
        try:
            # Verify checksum first if requested
            if verify and CHECKSUM_AVAILABLE:
                is_valid, msg = verify_export_file(filepath)
                if not is_valid:
                    logger.warning(f"Checksum verification failed for {filepath}: {msg}")
            
            df = pd.read_excel(filepath, sheet_name=sheet_name or 0)
            data = df.to_dict('records')
            
            logger.info(f"Loaded {len(data)} records from Excel: {filepath}")
            return data
            
        except Exception as e:
            logger.error(f"Error loading Excel: {e}")
            raise
    
    def auto_load(self, filepath: Path) -> List[Dict]:
        """
        Automatically load data based on file extension
        
        Args:
            filepath: Path to file
            
        Returns:
            Loaded data
        """
        filepath = Path(filepath)
        suffix = filepath.suffix.lower()
        
        if suffix == '.json':
            return self.load_json(filepath)
        elif suffix == '.csv':
            return self.load_csv(filepath)
        elif suffix in ['.xlsx', '.xls']:
            return self.load_excel(filepath)
        else:
            raise ValueError(f"Unsupported file format: {suffix}")


class MultiSheetExcelExporter:
    """Export multiple datasets to Excel with multiple sheets"""
    
    def __init__(self, export_dir: Path):
        self.export_dir = Path(export_dir)
        self.export_dir.mkdir(parents=True, exist_ok=True)
        
    def export_multi_sheet(self, datasets: Dict[str, List[Dict]], 
                          filename: str) -> Path:
        """
        Export multiple datasets to Excel with separate sheets
        
        Args:
            datasets: Dictionary mapping sheet name to data
            filename: Output filename
            
        Returns:
            Path to exported file
        """
        filepath = self.export_dir / filename
        
        try:
            with pd.ExcelWriter(filepath, engine='xlsxwriter') as writer:
                workbook = writer.book
                
                # Header format
                header_format = workbook.add_format({
                    'bold': True,
                    'bg_color': '#4472C4',
                    'font_color': 'white',
                    'border': 1
                })
                
                for sheet_name, data in datasets.items():
                    if not data:
                        continue
                    
                    # Convert to DataFrame
                    df = pd.DataFrame(data)
                    
                    # Write to sheet
                    df.to_excel(writer, sheet_name=sheet_name[:31], index=False)
                    
                    # Get worksheet
                    worksheet = writer.sheets[sheet_name[:31]]
                    
                    # Apply formatting
                    for col_num, value in enumerate(df.columns.values):
                        worksheet.write(0, col_num, value, header_format)
                        
                        # Auto-adjust width
                        max_length = max(
                            df[df.columns[col_num]].astype(str).apply(len).max(),
                            len(str(value))
                        )
                        worksheet.set_column(col_num, col_num, min(max_length + 2, 50))
            
            logger.info(f"Exported multi-sheet Excel: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Error exporting multi-sheet Excel: {e}")
            raise