<?php
require_once 'includes/config.php';

$reason = $_GET['reason'] ?? 'criteria';
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Study Requirements Not Met</title>
    <link rel="stylesheet" href="css/styles.css">
</head>
<body>
    <div class="container">
        <div class="card message-card">
            <div class="icon-circle error">
                <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="12" cy="12" r="10"></circle>
                    <line x1="15" y1="9" x2="9" y2="15"></line>
                    <line x1="9" y1="9" x2="15" y2="15"></line>
                </svg>
            </div>
            
            <h1>Thank You for Your Interest</h1>
            
            <?php if ($reason === 'previous'): ?>
                <p>Our records show you have previously participated in this study or did not meet the eligibility criteria.</p>
            <?php elseif ($reason === 'attention'): ?>
                <p>Unfortunately, you did not pass the screening study after two attempts.</p>
                <div class="info-box" style="background: #fff3cd; border-left: 4px solid #ffc107;">
                    <h3>What happened?</h3>
                    <p>The screening study is designed to ensure that annotators understand the task requirements and can apply the annotation guidelines accurately.</p>
                    <p>This does not reflect on your abilities - annotation tasks require specific familiarity with academic writing conventions and practice with the particular classification system used in this study.</p>
                </div>
            <?php else: ?>
                <p>Unfortunately, you do not meet the eligibility criteria for this study.</p>
                <div class="info-box">
                    <h3>Our Requirements</h3>
                    <ul>
                        <li>English as first language</li>
                        <li>Master's degree or currently completing or have completed a PhD</li>
                    </ul>
                </div>
            <?php endif; ?>
            
            <p>Please return this study on Prolific.</p>
            
            <div class="prolific-code">
                <?php if ($reason === 'attention'): ?>
                    <p><strong>Click the button below to return your submission:</strong></p>
                    <a href="https://app.prolific.com/submissions/complete?cc=C120KXHP" class="btn btn-primary btn-large" style="display: inline-block; margin-top: 15px; text-decoration: none;">
                        Return Submission
                    </a>
                <?php else: ?>
                    <p><strong>Click the button below to return your submission:</strong></p>
                    <a href="https://app.prolific.com/submissions/complete?cc=C14M9CAH" class="btn btn-primary btn-large" style="display: inline-block; margin-top: 15px; text-decoration: none;">
                        Return Submission
                    </a>
                <?php endif; ?>
            </div>
        </div>
    </div>
</body>
</html>
