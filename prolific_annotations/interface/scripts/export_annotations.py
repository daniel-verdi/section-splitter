#!/usr/bin/env python3
"""
Script to export all annotations from the database.

Usage:
    python export_annotations.py output.csv
    python export_annotations.py output.csv --paper-id 12345
    python export_annotations.py output.csv --annotator prolific_id
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

def export_annotations(output_file, paper_id=None, annotator_id=None):
    """Export annotations to CSV."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        query = """
            SELECT 
                a.prolific_id,
                an.paper_id,
                ps.section_order,
                ps.start_position as start,
                an.label,
                an.is_other_language,
                an.is_annotator_confused,
                an.created_at
            FROM annotations an
            JOIN annotators a ON an.annotator_id = a.annotator_id
            JOIN paper_sections ps ON an.section_id = ps.id
            WHERE 1=1
        """
        params = []
        
        if paper_id:
            query += " AND an.paper_id = %s"
            params.append(paper_id)
        
        if annotator_id:
            query += " AND a.prolific_id = %s"
            params.append(annotator_id)
        
        query += " ORDER BY a.prolific_id, an.paper_id, ps.section_order"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        if not rows:
            print("No annotations found matching the criteria.")
            return
        
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['prolific_id', 'paper_id', 'section_order', 'start', 
                         'label', 'is_other_language', 'is_annotator_confused', 'created_at']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for row in rows:
                row['is_other_language'] = 'True' if row['is_other_language'] else 'False'
                row['is_annotator_confused'] = 'True' if row['is_annotator_confused'] else 'False'
                writer.writerow(row)
        
        print(f"Successfully exported {len(rows)} annotations to {output_file}")
        
    except Exception as e:
        print(f"Error exporting annotations: {e}")
        sys.exit(1)
    finally:
        cursor.close()
        conn.close()

def get_summary():
    """Print annotation summary statistics."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Total annotators
        cursor.execute("SELECT COUNT(*) as count FROM annotators WHERE passed_attention_check = 1")
        annotators = cursor.fetchone()['count']
        
        # Total papers
        cursor.execute("SELECT COUNT(*) as count FROM papers")
        papers = cursor.fetchone()['count']
        
        # Papers with annotations
        cursor.execute("""
            SELECT 
                SUM(CASE WHEN n_annotations = 0 THEN 1 ELSE 0 END) as zero,
                SUM(CASE WHEN n_annotations = 1 THEN 1 ELSE 0 END) as one,
                SUM(CASE WHEN n_annotations = 2 THEN 1 ELSE 0 END) as two,
                SUM(CASE WHEN n_annotations >= 3 THEN 1 ELSE 0 END) as three_plus
            FROM papers
        """)
        paper_stats = cursor.fetchone()
        
        # Total annotations
        cursor.execute("SELECT COUNT(*) as count FROM annotations")
        annotations = cursor.fetchone()['count']
        
        print("\n=== Annotation Summary ===")
        print(f"Total qualified annotators: {annotators}")
        print(f"Total papers in database: {papers}")
        print(f"Total section annotations: {annotations}")
        print(f"\nPapers by annotation count:")
        print(f"  - 0 annotations: {paper_stats['zero'] or 0}")
        print(f"  - 1 annotation:  {paper_stats['one'] or 0}")
        print(f"  - 2 annotations: {paper_stats['two'] or 0}")
        print(f"  - 3+ annotations: {paper_stats['three_plus'] or 0}")
        
    except Exception as e:
        print(f"Error getting summary: {e}")
    finally:
        cursor.close()
        conn.close()

def main():
    parser = argparse.ArgumentParser(description='Export annotations from database')
    parser.add_argument('output_file', nargs='?', help='Output CSV file path')
    parser.add_argument('--paper-id', help='Filter by paper ID')
    parser.add_argument('--annotator', help='Filter by Prolific ID')
    parser.add_argument('--summary', action='store_true', help='Show summary statistics only')
    
    args = parser.parse_args()
    
    if args.summary:
        get_summary()
    elif args.output_file:
        export_annotations(args.output_file, args.paper_id, args.annotator)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
