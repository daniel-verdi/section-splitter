<?php
require_once 'includes/config.php';
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Desktop Required</title>
    <link rel="stylesheet" href="css/styles.css">
    <style>
        .mobile-notice {
            background: #fff3cd;
            border: 3px solid #ffc107;
            border-radius: 8px;
            padding: 30px;
            margin: 20px 0;
            text-align: center;
        }
        
        .mobile-notice h1 {
            color: #856404;
            margin-top: 0;
            font-size: 28px;
        }
        
        .mobile-notice p {
            font-size: 16px;
            line-height: 1.6;
            margin: 15px 0;
        }
        
        .device-icon {
            font-size: 64px;
            margin: 20px 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="card welcome-card">
            <div class="mobile-notice">
                <div class="device-icon">💻</div>
                <h1>Desktop or Laptop Required</h1>
                <p>Thank you for your interest in this study. However, it is critical that you <strong>complete this task on a laptop or desktop computer</strong>, and our data indicates that you are using a mobile device.</p>
                <p style="margin-top: 30px; color: #666;">Please access this study from a desktop or laptop computer to continue.</p>
                <p> If you don't have access to a desktop or laptop computer, unfortunately you won't be able to continue with the experiment. Please return your submission on Prolific by clicking the 'stop without completing' button.</p>
            </div>
            
        </div>
    </div>
</body>
</html>
