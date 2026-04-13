<?php
require_once 'includes/config.php';

// Check if user has passed screening
if (!isset($_SESSION['annotator_id']) || !isset($_SESSION['screening_passed']) || !$_SESSION['screening_passed']) {
    header('Location: index.php');
    exit;
}

// If already passed attention check, go directly to annotation
if (isset($_SESSION['attention_passed']) && $_SESSION['attention_passed']) {
    header('Location: annotate.php');
    exit;
}

$csrf_token = generateCSRFToken();
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Instructions - Annotation Study</title>
    <link rel="stylesheet" href="css/styles.css">
    <style>
        .instructions-container {
            max-width: 800px;
            margin: 40px auto;
            padding: 20px;
        }
        
        .critical-notice {
            background: #fff3cd;
            border: 3px solid #ff6b6b;
            border-radius: 8px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(255, 107, 107, 0.3);
        }
        
        .critical-notice h1 {
            color: #d32f2f;
            margin-top: 0;
            display: flex;
            align-items: center;
            gap: 12px;
            font-size: 28px;
        }
        
        .warning-icon {
            font-size: 36px;
            color: #d32f2f;
        }
        
        .critical-text {
            font-size: 18px;
            line-height: 1.6;
            color: #333;
            margin: 20px 0;
        }
        
        .critical-text strong {
            color: #d32f2f;
            font-weight: 600;
        }
        
        .guidelines-button-container {
            text-align: center;
            margin: 30px 0;
        }
        
        .btn-guidelines {
            background: #d32f2f;
            color: white;
            border: none;
            padding: 20px 40px;
            font-size: 20px;
            font-weight: 600;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 4px 12px rgba(211, 47, 47, 0.4);
            display: inline-flex;
            align-items: center;
            gap: 12px;
        }
        
        .btn-guidelines:hover {
            background: #b71c1c;
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(211, 47, 47, 0.5);
        }
        
        .btn-guidelines::before {
            content: "📄";
            font-size: 24px;
        }
        
        .info-list {
            background: white;
            border-radius: 8px;
            padding: 25px;
            margin: 25px 0;
            border-left: 4px solid #2196F3;
        }
        
        .info-list h3 {
            color: #2196F3;
            margin-top: 0;
        }
        
        .info-list ul {
            list-style: none;
            padding: 0;
        }
        
        .info-list li {
            padding: 10px 0;
            padding-left: 30px;
            position: relative;
        }
        
        .info-list li::before {
            content: "✓";
            position: absolute;
            left: 0;
            color: #4CAF50;
            font-weight: bold;
            font-size: 18px;
        }
        
        .confirmation-section {
            background: white;
            border-radius: 8px;
            padding: 30px;
            margin-top: 30px;
            border: 2px solid #e0e0e0;
        }
        
        .checkbox-container {
            display: flex;
            align-items: flex-start;
            gap: 15px;
            margin: 20px 0;
            padding: 20px;
            background: #f5f5f5;
            border-radius: 8px;
            cursor: pointer;
            transition: background 0.2s ease;
        }
        
        .checkbox-container:hover {
            background: #eeeeee;
        }
        
        .checkbox-container input[type="checkbox"] {
            width: 24px;
            height: 24px;
            margin-top: 3px;
            cursor: pointer;
            flex-shrink: 0;
        }
        
        .checkbox-container label {
            cursor: pointer;
            font-size: 16px;
            line-height: 1.5;
            margin: 0;
            flex: 1;
        }
        
        .btn-continue {
            width: 100%;
            padding: 16px;
            font-size: 18px;
            background: #4CAF50;
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.3s ease;
        }
        
        .btn-continue:hover:not(:disabled) {
            background: #45a049;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(76, 175, 80, 0.3);
        }
        
        .btn-continue:disabled {
            background: #cccccc;
            cursor: not-allowed;
            opacity: 0.6;
        }
        
        .attention-notice {
            background: #e3f2fd;
            border-left: 4px solid #2196F3;
            padding: 15px 20px;
            margin: 20px 0;
            border-radius: 4px;
        }
        
        .attention-notice strong {
            color: #1976D2;
        }
    </style>
</head>
<body>
    <div class="instructions-container">
        <div class="critical-notice">
            <h1>
                <span class="warning-icon">⚠️</span>
                IMPORTANT: Read Instructions Before Starting
            </h1>
            
            <p class="critical-text">
                <strong>You MUST carefully read the annotation guidelines before beginning this task.</strong> 
                The guidelines contain essential information about how to properly categorize scientific paper sections. 
                Failing to read and understand these instructions will likely result in incorrect annotations.
            </p>
            
            <div class="guidelines-button-container">
                <button type="button" class="btn-guidelines" onclick="openGuidelines()">
                    Open Annotation Guidelines (Required Reading)
                </button>
            </div>
        </div>
        
        <div class="info-list">
            <h3>What to Expect:</h3>
            <ul>
                <li>You will read the annotation guidelines that explain each category and provide examples</li>
                <li>You will complete a screening study to verify your understanding</li>
                <li>You will then annotate sections from scientific papers</li>
            </ul>
        </div>
        
        <div class="attention-notice">
            <strong>Note:</strong> After reading the guidelines, you will complete a brief screening study to ensure you understand the task.
            This is a standard quality control measure, and the paper should be relatively straightforward and not too hard to label.
            If you misclassify a large proportion of the items, you will become ineligible to participate in the study.
        </div>
        
        <div class="confirmation-section">
            <form id="confirmation-form" action="proceed_to_attention.php" method="POST">
                <input type="hidden" name="csrf_token" value="<?php echo $csrf_token; ?>">
                
                <div class="checkbox-container">
                    <input type="checkbox" id="guidelines_read" name="guidelines_read" required>
                    <label for="guidelines_read">
                        <strong>I confirm that I have carefully read and understood the annotation guidelines.</strong>
                        I understand that I will need to demonstrate this understanding in a screening study.
                    </label>
                </div>
                
                <button type="submit" class="btn-continue" id="continue-btn" disabled>
                    Continue to Screening Study
                </button>
            </form>
        </div>
    </div>
    
    <script>
        let guidelinesOpened = false;
        
        function openGuidelines() {
            window.open('guidelines.pdf', '_blank');
            guidelinesOpened = true;
            updateContinueButton();
        }
        
        function updateContinueButton() {
            const checkbox = document.getElementById('guidelines_read');
            const continueBtn = document.getElementById('continue-btn');
            continueBtn.disabled = !checkbox.checked;
        }
        
        // Update button state when checkbox is changed directly
        document.getElementById('guidelines_read').addEventListener('change', function() {
            updateContinueButton();
        });
        
        // Warn if trying to continue without opening guidelines
        document.getElementById('confirmation-form').addEventListener('submit', function(e) {
            if (!guidelinesOpened) {
                if (!confirm('We noticed you haven\'t opened the guidelines yet. Are you sure you want to continue? Reading the guidelines is essential for completing this task correctly.')) {
                    e.preventDefault();
                }
            }
        });
    </script>
</body>
</html>