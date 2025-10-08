import pdfplumber
import re
import json
from pathlib import Path
from typing import Dict, List, Optional

class DataExtractor:
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.data = {
            'employees': []
        }
    
    def clean_currency(self, value: str) -> Optional[float]:
        if not value or value.strip() == '':
            return None
        try:
            cleaned = re.sub(r'[^\d.-]', '', str(value))
            return float(cleaned) if cleaned else None
        except (ValueError, AttributeError):
            return None
    
    def extract(self) -> Dict:
        with pdfplumber.open(self.pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                
                if text:
                    self.parse_text_data(text)
        
        return self.data
    
    def parse_text_data(self, text: str) -> None:
        lines = text.split('\n')
        
        current_employee = None
        # in_earnings = False
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            # Match employee header pattern: "ID – Name, Name"
            employee_match = re.match(r'^(\d+)\s*[–-]\s*([A-Za-z]+,\s*[A-Za-z]+)', line)
            if employee_match:
                emp_id = employee_match.group(1)
                emp_name = employee_match.group(2).strip()
                
                current_employee = {
                    'employee_id': emp_id,
                    'employee_name': emp_name,
                    'earnings': []
                }
                self.data['employees'].append(current_employee)
                # in_earnings = False

            if current_employee:
                # Pattern: "Hourly- 09/10/25 5.00 4.00 100.00"
                earning_match = re.search(
                    r'(Hourly-)\s+(\d{2}/\d{2}/\d{2})\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)',
                    line
                )
                
                if earning_match:
                    earning_type = earning_match.group(1).strip('-').strip()
                    date = earning_match.group(2)
                    rate = self.clean_currency(earning_match.group(3))
                    hours = self.clean_currency(earning_match.group(4))
                    amount = self.clean_currency(earning_match.group(5))
                    
                    current_employee['earnings'].append({
                        'type': earning_type,
                        'date': date,
                        'rate': rate,
                        'hours': hours,
                        'amount': amount
                    })
                    continue
            
            # Check for Total Earnings
            if current_employee and 'Total Earnings:' in line:
                total_match = re.search(r'Total Earnings:\s+([\d.]+)\s+([\d.]+)', line)
                if total_match:
                    current_employee['total_hours'] = self.clean_currency(total_match.group(1))
                    current_employee['total_amount'] = self.clean_currency(total_match.group(2))
                continue
    
    def to_json(self, output_path: Optional[str] = None) -> str:
        """Export data to JSON."""
        json_data = json.dumps(self.data, indent=2)
        
        if output_path:
            with open(output_path, 'w') as f:
                f.write(json_data)
        
        return json_data
    
if __name__ == "__main__":
    extractor = DataExtractor("invoice.pdf")
    data = extractor.extract()
    
    # Print results in table format
    print(f"\nTotal Employees Found: {len(data['employees'])}")
    print("\n" + "="*120)
    print(f"{'Employee ID & Name':<35} {'Earnings':<60}")
    print(f"{'':<35} {'Type':<15}{'Change Date':<15} {'Rate':<10} {'Hours':<10} {'Amount':<15}")
    print("="*120)
    
    for employee in data['employees']:
        emp_info = f"{employee['employee_id']} – {employee['employee_name']}"
        
        # Print employee info with first earning
        if employee['earnings']:
            first_earning = employee['earnings'][0]
            print(f"{emp_info:<35} {first_earning['type']:<15} "
                  f"{first_earning['date']:<15} "
                  f"{first_earning['rate']:<10.2f} {first_earning['hours']:<10.2f} "
                  f"{first_earning['amount']:<15.2f}")
            
            # Print remaining earnings
            for earning in employee['earnings'][1:]:
                print(f"{'':<35} {earning['type']:<15} "
                      f"{earning['date']:<15} "
                      f"{earning['rate']:<10.2f} {earning['hours']:<10.2f} "
                      f"{earning['amount']:<15.2f}")
        print("\n")
        # Print total earnings
        if employee.get('total_amount'):
            print(f"{'':<35} {'Total Earnings:':<31} "
                  f"{'':<10} {employee['total_hours']:<10.2f} "
                  f"{employee['total_amount']:<15.2f}")
            print("-"*120)
    
    print("="*120)
    
    # Export to JSON
    extractor.to_json("output.json")
    print("\n✓ JSON exported to: output.json")
    