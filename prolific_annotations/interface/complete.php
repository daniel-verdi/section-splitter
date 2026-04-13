<?php
require_once 'includes/config.php';

// Verify session
if (!isset($_SESSION['annotator_id'])) {
    header('Location: index.php');
    exit;
}

$annotator_id = $_SESSION['annotator_id'];
$pdo = getDBConnection();

// Get annotator info
$stmt = $pdo->prepare("SELECT prolific_id FROM annotators WHERE annotator_id = ?");
$stmt->execute([$annotator_id]);
$annotator = $stmt->fetch();

// Generate completion code (combination of timestamp and annotator id)
$completion_code = 'CSNQ3YBB';

// Export annotations to file
$stmt = $pdo->prepare("
    SELECT 
        a.prolific_id,
        an.paper_id,
        ps.section_order,
        ps.start_position,
        an.label,
        an.is_other_language,
        an.is_annotator_confused,
        an.created_at
    FROM annotations an
    JOIN annotators a ON an.annotator_id = a.annotator_id
    JOIN paper_sections ps ON an.section_id = ps.id
    WHERE an.annotator_id = ?
    ORDER BY an.paper_id, ps.section_order
");
$stmt->execute([$annotator_id]);
$annotations = $stmt->fetchAll();

// Save to file
$filename = $annotator['prolific_id'] . '_' . date('Y-m-d_H-i-s') . '.csv';
$filepath = __DIR__ . '/exports/' . $filename;

// Ensure exports directory exists
if (!is_dir(__DIR__ . '/exports')) {
    mkdir(__DIR__ . '/exports', 0755, true);
}

// Write CSV
$fp = fopen($filepath, 'w');
fputcsv($fp, ['prolific_id', 'paper_id', 'section_order', 'start', 'label', 'is_other_language', 'is_annotator_confused', 'created_at']);
foreach ($annotations as $row) {
    fputcsv($fp, [
        $row['prolific_id'],
        $row['paper_id'],
        $row['section_order'],
        $row['start_position'],
        $row['label'],
        $row['is_other_language'] ? 'True' : 'False',
        $row['is_annotator_confused'] ? 'True' : 'False',
        $row['created_at']
    ]);
}
fclose($fp);

// Clear session
unset($_SESSION['annotator_id']);
unset($_SESSION['screening_passed']);
unset($_SESSION['attention_passed']);
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Study Complete - Thank You!</title>
    <link rel="stylesheet" href="css/styles.css">
</head>
<body>
    <div class="container">
        <div class="card message-card success">
            <div class="icon-circle success">
                <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <polyline points="20 6 9 17 4 12"></polyline>
                </svg>
            </div>
            
            <h1>Thank You!</h1>
            <p>You have successfully completed the annotation study.</p>
            
            <div class="completion-code">
                <p>Your completion code:</p>
                <div class="code-box">
                    <code id="completion-code"><?php echo $completion_code; ?></code>
                    <button type="button" class="btn btn-small btn-secondary" onclick="copyCode()">Copy</button>
                </div>
            </div>

            <div class="info-box">
                <p><strong>Important:</strong> Please copy this code and paste it into the Prolific submission page or click the button bellow to complete the study.</p>
            </div>

            <div class="prolific-redirect">
                <p>Click below to return to Prolific:</p>
                <a href="https://app.prolific.co/submissions/complete?cc=<?php echo urlencode($completion_code); ?>" 
                   class="btn btn-primary btn-large" target="_blank">
                    Complete on Prolific
                </a>
            </div>
        </div>
    </div>

    <script>
        function copyCode() {
            const code = document.getElementById('completion-code').textContent;
            navigator.clipboard.writeText(code).then(function() {
                alert('Completion code copied to clipboard!');
            }).catch(function(err) {
                // Fallback for older browsers
                const textArea = document.createElement('textarea');
                textArea.value = code;
                document.body.appendChild(textArea);
                textArea.select();
                document.execCommand('copy');
                document.body.removeChild(textArea);
                alert('Completion code copied to clipboard!');
            });
        }
    </script>
</body>
</html>
