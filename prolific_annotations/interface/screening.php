<?php
require_once 'includes/config.php';

// Verify POST request and CSRF token
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    header('Location: index.php');
    exit;
}

if (!verifyCSRFToken($_POST['csrf_token'] ?? '')) {
    die('Invalid request. Please go back and try again.');
}

// Get and sanitize form data
$prolific_id = sanitize($_POST['prolific_id'] ?? '');
$education_level = sanitize($_POST['education_level'] ?? '');
$first_language = sanitize($_POST['first_language'] ?? '');
$consent = isset($_POST['consent']);

// Validate required fields
if (empty($prolific_id) || empty($education_level) || empty($first_language) || !$consent) {
    $_SESSION['error'] = 'Please fill in all required fields.';
    header('Location: index.php');
    exit;
}

// Screening criteria
$valid_education = ['masters', 'phd_in_progress', 'phd_completed', 'postdoc'];
$valid_first_language = ['english'];

$passed_screening = in_array($education_level, $valid_education) && 
                    in_array($first_language, $valid_first_language);

$pdo = getDBConnection();

// Check if this Prolific ID already exists
$stmt = $pdo->prepare("SELECT annotator_id, passed_screening, passed_attention_check FROM annotators WHERE prolific_id = ?");
$stmt->execute([$prolific_id]);
$existing = $stmt->fetch();

if ($existing) {
    // User already exists
    if ($existing['passed_screening'] && $existing['passed_attention_check']) {
        // Already passed everything, continue to annotation
        $_SESSION['annotator_id'] = $existing['annotator_id'];
        $_SESSION['screening_passed'] = true;
        $_SESSION['attention_passed'] = true;
        header('Location: annotate.php');
        exit;
    } elseif ($existing['passed_screening']) {
        // Passed screening but not attention check
        $_SESSION['annotator_id'] = $existing['annotator_id'];
        $_SESSION['screening_passed'] = true;
        header('Location: attention_check.php');
        exit;
    } else {
        // Previously failed screening
        header('Location: screened_out.php?reason=previous');
        exit;
    }
}

// Insert new annotator
$stmt = $pdo->prepare("
    INSERT INTO annotators (prolific_id, education_level, first_language, passed_screening) 
    VALUES (?, ?, ?, ?)
");
$stmt->execute([$prolific_id, $education_level, $first_language, $passed_screening]);
$annotator_id = $pdo->lastInsertId();

$_SESSION['annotator_id'] = $annotator_id;

if (!$passed_screening) {
    header('Location: screened_out.php?reason=criteria');
    exit;
}

$_SESSION['screening_passed'] = true;
header('Location: instructions.php');
exit;
?>
