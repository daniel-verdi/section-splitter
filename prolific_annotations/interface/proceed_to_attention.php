<?php
require_once 'includes/config.php';

// Verify POST request and CSRF token
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    header('Location: index.php');
    exit;
}

// Check if user has passed screening
if (!isset($_SESSION['annotator_id']) || !isset($_SESSION['screening_passed']) || !$_SESSION['screening_passed']) {
    header('Location: index.php');
    exit;
}

// Verify the confirmation checkbox was checked
$guidelines_read = isset($_POST['guidelines_read']);

if (!$guidelines_read) {
    $_SESSION['error'] = 'You must confirm that you have read the guidelines.';
    header('Location: instructions.php');
    exit;
}

// Proceed to attention check
header('Location: screening_study.php');
exit;
?>