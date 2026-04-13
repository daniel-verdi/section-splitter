<?php
require_once 'includes/config.php';

// Verify session and request
if (!isset($_SESSION['annotator_id']) || !isset($_SESSION['screening_passed'])) {
    header('Location: index.php');
    exit;
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    header('Location: screening_study.php');
    exit;
}

if (!verifyCSRFToken($_POST['csrf_token'] ?? '')) {
    die('Invalid request. Please go back and try again.');
}

$annotator_id = $_SESSION['annotator_id'];
$paper_id = $_POST['paper_id'] ?? '';
$labels = $_POST['labels'] ?? [];

if (empty($labels)) {
    $_SESSION['error'] = 'Please label all sections.';
    header('Location: screening_study.php');
    exit;
}

$pdo = getDBConnection();

// Get correct answers for the attention check
$stmt = $pdo->prepare("
    SELECT id, correct_label 
    FROM attention_check_sections 
    WHERE paper_id = ?
");
$stmt->execute([$paper_id]);
$correct_answers = $stmt->fetchAll(PDO::FETCH_KEY_PAIR);

// Calculate accuracy
$total = count($correct_answers);
$correct = 0;

foreach ($labels as $section_id => $user_label) {
    if (isset($correct_answers[$section_id]) && $correct_answers[$section_id] === $user_label) {
        $correct++;
    }
}

$accuracy = $total > 0 ? ($correct / $total) : 0;

// Get current number of attempts from database (not session)
$stmt = $pdo->prepare("SELECT attention_check_attempts FROM annotators WHERE annotator_id = ?");
$stmt->execute([$annotator_id]);
$result = $stmt->fetchColumn();

// Handle NULL or FALSE from database
if ($result === false || $result === null) {
    $current_attempts = 0;
} else {
    $current_attempts = intval($result);
}

// This will be their Nth attempt
$new_attempts = $current_attempts + 1;

// Increment attempts
$new_attempts = $current_attempts + 1;

// Require at least 70% accuracy to pass
$passed = $accuracy >= 0.7;

// Update annotator record with attempt count
$stmt = $pdo->prepare("UPDATE annotators SET passed_attention_check = ?, attention_check_attempts = ? WHERE annotator_id = ?");
$stmt->execute([$passed, $new_attempts, $annotator_id]);

if (!$passed) {
    // Check if this was the first attempt (allow retry)
    if ($new_attempts == 1) {
        // First failure - allow retry
        header('Location: attention_retry.php');
        exit;
    } else {
        // Second failure - screen out
        unset($_SESSION['annotator_id']);
        unset($_SESSION['screening_passed']);
        header('Location: screened_out.php?reason=attention');
        exit;
    }
}

// Passed! Continue to main annotation
$_SESSION['attention_passed'] = true;
header('Location: annotate.php');
exit;
?>
