<?php
require_once 'includes/config.php';

// Check if user has passed screening
if (!isset($_SESSION['annotator_id']) || !isset($_SESSION['screening_passed'])) {
    header('Location: index.php');
    exit;
}

// If already passed attention check, go to annotation
if (isset($_SESSION['attention_passed']) && $_SESSION['attention_passed']) {
    header('Location: annotate.php');
    exit;
}

$pdo = getDBConnection();
$annotator_id = $_SESSION['annotator_id'];

// Check attempts from database (not session)
$stmt = $pdo->prepare("SELECT attention_check_attempts FROM annotators WHERE annotator_id = ?");
$stmt->execute([$annotator_id]);
$attempts = intval($stmt->fetchColumn()) ?? 0;

// Check if they've already used their retry (shouldn't be here if attempts > 1)
if ($attempts > 1) {
    header('Location: screened_out.php?reason=attention');
    exit;
}

$csrf_token = generateCSRFToken();
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Comprehension Check - Retry</title>
    <link rel="stylesheet" href="css/styles.css">
    <style>
        .retry-notice {
            background: #fff3cd;
            border: 3px solid #ffc107;
            border-radius: 8px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(255, 193, 7, 0.3);
        }
        
        .retry-notice h2 {
            color: #856404;
            margin-top: 0;
            display: flex;
            align-items: center;
            gap: 12px;
        }
        
        .retry-notice p {
            font-size: 16px;
            line-height: 1.6;
            color: #333;
            margin: 15px 0;
        }
        
        .retry-tips {
            background: #e3f2fd;
            border-left: 4px solid #2196F3;
            padding: 20px;
            margin: 20px 0;
            border-radius: 4px;
        }
        
        .retry-tips h3 {
            color: #1976D2;
            margin-top: 0;
        }
        
        .retry-tips ul {
            margin: 10px 0;
            padding-left: 25px;
        }
        
        .retry-tips li {
            margin: 8px 0;
            line-height: 1.5;
        }
        
        .warning-text {
            background: #ffebee;
            border-left: 4px solid #f44336;
            padding: 15px;
            margin: 20px 0;
            border-radius: 4px;
            font-weight: 600;
            color: #c62828;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="card welcome-card">
            <div class="retry-notice">
                <h2>
                    <span style="font-size: 32px;">⚠️</span>
                    Comprehension Check - Second Attempt
                </h2>
                
                <p>Your previous responses did not meet the accuracy threshold required to proceed. However, <strong>you have one more opportunity</strong> to complete the comprehension check.</p>
                
                <div class="retry-tips">
                    <h3>Before you try again:</h3>
                    <ul>
                        <li><strong>Review the annotation guidelines carefully</strong> - The button below will open them in a new window</li>
                        <li><strong>Read the entire paper structure</strong> - Look at all the headers in the left panel to understand the paper's flow</li>
                        <li><strong>Pay attention to context</strong> - A section's position in the paper often determines its label</li>
                        <li><strong>Use the label definitions</strong> - Make sure you understand what each category means</li>
                        <li><strong>Take your time</strong> - There is no time limit for this task</li>
                    </ul>
                </div>
                
                <div style="text-align: center; margin: 25px 0;">
                    <button type="button" class="btn btn-primary" 
                            style="background: #d32f2f; padding: 15px 30px; font-size: 16px;" 
                            onclick="window.open('guidelines.pdf', '_blank')">
                        📄 Read Annotation Guidelines (Required)
                    </button>
                </div>
                
                <div class="warning-text">
                    ⚠️ Important: This is your final attempt. If you do not meet the accuracy threshold this time, you will be unable to continue with the study.
                </div>
            </div>
            
            <form action="screening_study.php" method="GET">
                <div class="form-actions" style="margin-top: 30px;">
                    <button type="submit" class="btn btn-primary btn-large">
                        I'm Ready - Take Comprehension Check Again
                    </button>
                </div>
            </form>
        </div>
    </div>
</body>
</html>
