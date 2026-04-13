<?php
require_once 'includes/config.php';

// Verify session
if (!isset($_SESSION['annotator_id']) || !isset($_SESSION['screening_passed']) || !isset($_SESSION['attention_passed'])) {
    header('Location: index.php');
    exit;
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    header('Location: annotate.php');
    exit;
}

if (!verifyCSRFToken($_POST['csrf_token'] ?? '')) {
    die('Invalid request. Please go back and try again.');
}

$annotator_id = $_SESSION['annotator_id'];
$paper_id = $_POST['paper_id'] ?? '';
$paper_index = intval($_POST['paper_index'] ?? 0);
$labels = $_POST['labels'] ?? [];
$is_other_language = isset($_POST['is_other_language']);
$is_confused = isset($_POST['is_confused']);
$action = $_POST['action'] ?? 'next';

if (empty($paper_id)) {
    header('Location: annotate.php');
    exit;
}

$pdo = getDBConnection();

// Begin transaction
$pdo->beginTransaction();

try {
    // Delete any existing section annotations
    $stmt = $pdo->prepare("DELETE FROM annotations WHERE annotator_id = ? AND paper_id = ?");
    $stmt->execute([$annotator_id, $paper_id]);

    // Insert new section annotations
    $insert_stmt = $pdo->prepare("
        INSERT INTO annotations (annotator_id, paper_id, section_id, label)
        VALUES (?, ?, ?, ?)
    ");

    foreach ($labels as $section_id => $label) {
        if (!empty($label)) {
            $insert_stmt->execute([
                $annotator_id, $paper_id, intval($section_id), $label
            ]);
        }
    }
    
    // Determine completion status
    $mark_completed = ($action === 'next') ? "completed = TRUE," : "";

    // UPDATE the annotator_papers table with the flags and completion status
    $stmt = $pdo->prepare("
        UPDATE annotator_papers 
        SET $mark_completed
            is_other_language = ?, 
            is_annotator_confused = ?
        WHERE annotator_id = ? AND paper_id = ?
    ");
    $stmt->execute([$is_other_language, $is_confused, $annotator_id, $paper_id]);

    // Handle n_annotations increment (Only if marking complete for the first time)
    if ($action === 'next') {
        $stmt = $pdo->prepare("SELECT completed FROM annotator_papers WHERE annotator_id = ? AND paper_id = ?");
        $stmt->execute([$annotator_id, $paper_id]);
        $was_completed = $stmt->fetchColumn();

        if (!$was_completed) {
            // Removed the "AND n_annotations < 3" limit here so you get true counts
            $stmt = $pdo->prepare("UPDATE papers SET n_annotations = n_annotations + 1 WHERE paper_id = ?");
            $stmt->execute([$paper_id]);
        }
    }

    $pdo->commit();

    // Determine where to redirect
    if ($action === 'previous' && $paper_index > 0) {
        // Go to previous paper
        header('Location: annotate.php?paper=' . ($paper_index - 1));
    } elseif ($action === 'save') {
        // Stay on same paper
        header('Location: annotate.php?paper=' . $paper_index);
    } else {
        // Next paper (annotate.php will handle completion check)
        // header('Location: annotate.php');
        // Explicitly go to the next index!
        header('Location: annotate.php?paper=' . ($paper_index + 1));
    }
    exit;

} catch (Exception $e) {
    $pdo->rollBack();
    error_log("Annotation save error: " . $e->getMessage());
    $_SESSION['error'] = 'Failed to save annotations. Please try again.';
    header('Location: annotate.php');
    exit;
}
?>
