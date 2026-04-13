<?php
require_once 'includes/config.php';

// Block mobile and tablet users - must use desktop
$user_agent = $_SERVER['HTTP_USER_AGENT'] ?? '';
$is_mobile = preg_match('/Mobile|Android|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini|Tablet/i', $user_agent);

if ($is_mobile) {
    header('Location: mobile_blocked.php');
    exit;
}

// Clear any existing session data for fresh start
if (!isset($_GET['continue'])) {
    unset($_SESSION['annotator_id']);
    unset($_SESSION['screening_passed']);
    unset($_SESSION['attention_passed']);
}

$csrf_token = generateCSRFToken();
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Scientific Paper Annotation Study</title>
    <link rel="stylesheet" href="css/styles.css">
</head>
<body>
    <div class="container">
        <div class="card welcome-card">
            <h1>Scientific Paper Section Annotation Study</h1>
            
            <div class="info-box">
                <h3>About This Study</h3>
                <p>We are evaluating a classifier that categorizes sections of scientific papers. Your task will be to read paper sections and assign the correct category label to each one.</p>
                <!--
                <p><strong>Estimated time:</strong> 30-45 minutes</p>
                <p><strong>You will annotate:</strong> 10 scientific papers</p>
                -->
                <button type="button" class="btn btn-primary btn-small" onclick="window.open('guidelines.pdf', '_blank')">
                    ⚠️ IMPORTANT: Read Annotation Guidelines
                </button>
            </div>
            
            <!--

            <div class="info-box requirements">
                <h3>Requirements</h3>
                <ul>
                    <li>Fluent in English</li>
                    <li>Currently completing or have completed a PhD</li>
                    <li>At least 2 years of research experience</li>
                </ul>
            </div>
            
            -->

            <form id="screening-form" action="screening.php" method="POST">
                <input type="hidden" name="csrf_token" value="<?php echo $csrf_token; ?>">
                
                <div class="form-group">
                    <label for="prolific_id">Prolific ID <span class="required">*</span></label>
                    <input type="text" id="prolific_id" name="prolific_id" required 
                           placeholder="Enter your Prolific ID" maxlength="100">
                </div>

                <div class="form-group">
                    <label for="education_level">Which of these is the highest level of education you have completed? <span class="required">*</span></label>
                    <select id="education_level" name="education_level" required>
                        <option value="">-- Select your education level --</option>
                        <option value="high_school">High School / GED</option>
                        <option value="bachelors">Bachelor's Degree</option>
                        <option value="masters">Master's Degree</option>
                        <option value="phd_in_progress">PhD (In Progress)</option>
                        <option value="phd_completed">PhD (Completed)</option>
                        <option value="postdoc">Postdoctoral / Higher</option>
                    </select>
                </div>

                <div class="form-group">
                    <label for="first_language">What is your first language? <span class="required">*</span></label>
                    <select id="first_language" name="first_language" required>
                        <option value="">-- Select your first language --</option>
                        <option value="english">English</option>
                        <option value="spanish">Spanish</option>
                        <option value="mandarin">Mandarin Chinese</option>
                        <option value="hindi">Hindi</option>
                        <option value="arabic">Arabic</option>
                        <option value="portuguese">Portuguese</option>
                        <option value="bengali">Bengali</option>
                        <option value="russian">Russian</option>
                        <option value="japanese">Japanese</option>
                        <option value="punjabi">Punjabi</option>
                        <option value="german">German</option>
                        <option value="french">French</option>
                        <option value="italian">Italian</option>
                        <option value="korean">Korean</option>
                        <option value="turkish">Turkish</option>
                        <option value="vietnamese">Vietnamese</option>
                        <option value="polish">Polish</option>
                        <option value="dutch">Dutch</option>
                        <option value="other">Other</option>
                    </select>
                </div>

                <!--
                <div class="form-group">
                    <label for="research_experience">Years of Research Experience <span class="required">*</span></label>
                    <select id="research_experience" name="research_experience" required>
                        <option value="">-- Select your experience --</option>
                        <option value="0">Less than 1 year</option>
                        <option value="1">1 year</option>
                        <option value="2">2 years</option>
                        <option value="3">3 years</option>
                        <option value="4">4 years</option>
                        <option value="5">5+ years</option>
                    </select>
                </div>
                -->

                <div class="form-group consent-group">
                    <label class="checkbox-label">
                        <input type="checkbox" id="consent" name="consent" required>
                        <span>I understand that my responses will be used for research purposes and I consent to participate in this study. <span class="required">*</span></span>
                    </label>
                </div>

                <button type="submit" class="btn btn-primary btn-large">
                    Continue to Study
                </button>
            </form>
        </div>
    </div>

    <script>
        document.getElementById('screening-form').addEventListener('submit', function(e) {
            const prolificId = document.getElementById('prolific_id').value.trim();
            if (prolificId.length < 5) {
                e.preventDefault();
                alert('Please enter a valid Prolific ID.');
                return;
            }
        });
    </script>
</body>
</html>
