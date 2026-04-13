#!/usr/bin/env python3
"""
Script to import papers from CSV into the annotation database.

Usage:
    python import_papers.py papers.csv
    python import_papers.py attention_check.csv --attention-check

CSV format expected:
    corpusid,section_text,extracted,start
    
For attention check papers, add a 'correct_label' column:
    corpusid,section_text,extracted,start,correct_label
"""

import csv
import sys
import argparse
import mysql.connector
from mysql.connector import Error

# Database configuration - update these values
DB_CONFIG = {
    'host': 'localhost',
    'database': 'paper_annotations',
    'user': 'your_username',
    'password': 'your_password'
}

def get_connection():
    """Create database connection."""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Error as e:
        print(f"Error connecting to database: {e}")
        sys.exit(1)

def import_regular_papers(csv_file):
    """Import regular papers for annotation."""
    conn = get_connection()
    cursor = conn.cursor()
    
    papers_added = 0
    sections_added = 0
    
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            current_paper_id = None
            section_order = 0
            
            for row in reader:
                paper_id = row.get('corpusid', '').strip()
                section_text = row.get('section_text', '').strip()
                extracted = row.get('extracted', '').strip()
                start = row.get('start', 0)
                
                if not paper_id or not section_text:
                    continue
                
                # Check if this is a new paper
                if paper_id != current_paper_id:
                    # Insert paper if it doesn't exist
                    cursor.execute(
                        "INSERT IGNORE INTO papers (paper_id) VALUES (%s)",
                        (paper_id,)
                    )
                    if cursor.rowcount > 0:
                        papers_added += 1
                    
                    current_paper_id = paper_id
                    section_order = 0
                
                # Insert section
                cursor.execute(
                    """INSERT INTO paper_sections 
                       (paper_id, section_order, section_text, extracted_headers, start_position)
                       VALUES (%s, %s, %s, %s, %s)""",
                    (paper_id, section_order, section_text, extracted, start)
                )
                sections_added += 1
                section_order += 1
        
        conn.commit()
        print(f"Successfully imported {papers_added} papers with {sections_added} sections.")
        
    except Exception as e:
        conn.rollback()
        print(f"Error importing papers: {e}")
        sys.exit(1)
    finally:
        cursor.close()
        conn.close()

def import_attention_check(csv_file):
    """Import attention check papers with correct labels."""
    conn = get_connection()
    cursor = conn.cursor()
    
    papers_added = 0
    sections_added = 0
    
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            current_paper_id = None
            section_order = 0
            
            for row in reader:
                paper_id = row.get('corpusid', '').strip()
                section_text = row.get('section_text', '').strip()
                extracted = row.get('extracted', '').strip()
                correct_label = row.get('correct_label', '').strip()
                
                if not paper_id or not section_text or not correct_label:
                    print(f"Warning: Skipping row - missing required fields")
                    continue
                
                # Check if this is a new paper
                if paper_id != current_paper_id:
                    # Insert attention check paper
                    cursor.execute(
                        "INSERT IGNORE INTO attention_check_papers (paper_id) VALUES (%s)",
                        (paper_id,)
                    )
                    if cursor.rowcount > 0:
                        papers_added += 1
                    
                    current_paper_id = paper_id
                    section_order = 0
                
                # Insert section with correct label
                cursor.execute(
                    """INSERT INTO attention_check_sections 
                       (paper_id, section_order, section_text, extracted_headers, correct_label)
                       VALUES (%s, %s, %s, %s, %s)""",
                    (paper_id, section_order, section_text, extracted, correct_label)
                )
                sections_added += 1
                section_order += 1
        
        conn.commit()
        print(f"Successfully imported {papers_added} attention check papers with {sections_added} sections.")
        
    except Exception as e:
        conn.rollback()
        print(f"Error importing attention check papers: {e}")
        sys.exit(1)
    finally:
        cursor.close()
        conn.close()

def main():
    parser = argparse.ArgumentParser(description='Import papers into annotation database')
    parser.add_argument('csv_file', help='Path to CSV file')
    parser.add_argument('--attention-check', action='store_true', 
                        help='Import as attention check paper (requires correct_label column)')
    
    args = parser.parse_args()
    
    if args.attention_check:
        import_attention_check(args.csv_file)
    else:
        import_regular_papers(args.csv_file)

if __name__ == '__main__':
    main()
