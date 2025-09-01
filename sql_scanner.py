#!/usr/bin/env python3
import os
import re
import glob
from datetime import datetime

def find_sql_queries():
    print("🔍 Starting universal SQL query scanner...")
    
    # Файлы для поиска (можно добавить любые другие)
    extensions = ['*.go', '*.py', '*.js', '*.java', '*.php', '*.rb', '*.ts', '*.cs']
    sql_pattern = re.compile(r'(SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP).*?;?$', re.IGNORECASE)
    
    with open('found_queries.sql', 'w', encoding='utf-8') as output_file:
        output_file.write(f"-- Found SQL queries on {datetime.now()}\n\n")
        
        for ext in extensions:
            for file_path in glob.glob(f'**/{ext}', recursive=True):
                if os.path.isfile(file_path):
                    print(f"Scanning: {file_path}")
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            lines = f.readlines()
                            
                        for line_num, line in enumerate(lines, 1):
                            if sql_pattern.search(line):
                                output_file.write(f"-- From: {file_path}:{line_num}\n")
                                output_file.write(f"{line.strip()}\n;\n\n")
                    except Exception as e:
                        print(f"Error reading {file_path}: {e}")
    
    print("✅ Scan completed! Check found_queries.sql")

if __name__ == "__main__":
    find_sql_queries()