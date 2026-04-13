# Scientific Paper Annotation System

A web-based annotation system for collecting human annotations on scientific paper sections, designed for use with Prolific participants.

## Features

- **Screening questionnaire**: Filters participants based on education level, English fluency, and research experience
- **Attention check**: Ensures annotators understand the task before proceeding
- **Randomized paper assignment**: Each annotator gets 10 random papers (where n_annotations < 3)
- **No duplicate assignments**: Same paper is never shown twice to the same annotator
- **Progress tracking**: Annotations are saved automatically
- **Prolific integration**: Completion codes for payment verification
- **Admin dashboard**: Monitor progress and export data

## Requirements

- PHP 7.4+ with PDO MySQL extension
- MySQL 5.7+ or MariaDB 10.3+
- Web server (Apache/Nginx)
- Python 3.6+ (for import/export scripts)

## Installation

### 1. Database Setup

1. Create the database and tables:
```bash
mysql -u root -p < database/schema.sql
```

2. Update database credentials in `includes/config.php`:
```php
define('DB_HOST', 'localhost');
define('DB_NAME', 'paper_annotations');
define('DB_USER', 'your_username');
define('DB_PASS', 'your_password');
```

3. Also update credentials in Python scripts if using them:
   - `scripts/import_papers.py`
   - `scripts/export_annotations.py`

### 2. Web Server Setup

#### Apache
Ensure the document root points to the annotation_system folder.

#### Nginx
```nginx
server {
    listen 80;
    server_name your-domain.com;
    root /path/to/annotation_system;
    index index.php;

    location / {
        try_files $uri $uri/ /index.php?$query_string;
    }

    location ~ \.php$ {
        fastcgi_pass unix:/var/run/php/php-fpm.sock;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
        include fastcgi_params;
    }
}
```

### 3. Directory Permissions

```bash
mkdir -p exports
chmod 755 exports
chown www-data:www-data exports
```

### 4. Import Papers

Prepare your CSV file with columns:
- `corpusid`: Unique paper identifier
- `section_text`: The text content of each section
- `extracted`: Extracted headers (optional)
- `start`: Start position (optional)

```bash
python scripts/import_papers.py /path/to/papers.csv
```

### 5. Set Up Attention Check

Create a CSV with the same format plus `correct_label`:
```bash
python scripts/import_papers.py /path/to/attention_check.csv --attention-check
```

### 6. Add Guidelines PDF

Place your annotation guidelines at `guidelines.pdf`

### 7. Configure Admin Password

In `admin.php`, change:
```php
$admin_password = 'your_secure_password';
```

## Annotation Labels

- introduction, lit_review, methods, results, discussion, conclusion
- development, case_report, something_else, ambiguous

## Screening Criteria (Default)

- Education: PhD (in progress/completed) or Postdoc
- English: Native or Fluent
- Experience: 2+ years

Modify in `screening.php`.

## Admin Dashboard

Access at `/admin.php` to:
- View statistics
- Monitor completion
- Export all annotations

## Data Export

Via admin dashboard or Python:
```bash
python scripts/export_annotations.py output.csv
python scripts/export_annotations.py --summary
```

## Troubleshooting

- **No attention check**: Import one with `--attention-check`
- **Papers not assigned**: Verify `n_annotations < 3` in database
- **Session issues**: Check PHP session configuration

## Security Notes

For production:
1. Use HTTPS
2. Implement proper admin authentication
3. Add rate limiting
4. Consider CAPTCHA

## License

MIT License
