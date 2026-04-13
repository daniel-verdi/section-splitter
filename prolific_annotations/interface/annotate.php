<?php
require_once 'includes/config.php';

// Verify session
if (!isset($_SESSION['annotator_id']) || !isset($_SESSION['screening_passed']) || !isset($_SESSION['attention_passed'])) {
    header('Location: index.php');
    exit;
}

$annotator_id = $_SESSION['annotator_id'];
$pdo = getDBConnection();
$csrf_token = generateCSRFToken();

// Get annotator's prolific ID for reference
$stmt = $pdo->prepare("SELECT prolific_id FROM annotators WHERE annotator_id = ?");
$stmt->execute([$annotator_id]);
$annotator = $stmt->fetch();

// Check if annotator already has assigned papers
$stmt = $pdo->prepare("
    SELECT ap.paper_id, ap.completed, ap.is_other_language, ap.is_annotator_confused 
    FROM annotator_papers ap 
    WHERE ap.annotator_id = ?
    ORDER BY ap.assigned_at
");
$stmt->execute([$annotator_id]);
$assigned_papers = $stmt->fetchAll();

// If no papers assigned yet, assign 10 random papers
if (empty($assigned_papers)) {
    // Get papers that:
    // 1. Have been ASSIGNED fewer than 3 times total
    // 2. Are not already assigned to THIS annotator
    /*
    $stmt = $pdo->prepare("
        SELECT p.paper_id 
        FROM papers p
        WHERE (
            SELECT COUNT(*) 
            FROM annotator_papers ap2 
            WHERE ap2.paper_id = p.paper_id
        ) < 3
        AND p.paper_id NOT IN (
            SELECT paper_id FROM annotator_papers WHERE annotator_id = ?
        )
        ORDER BY RAND()
        LIMIT 10
    ");
    */
    
     $stmt = $pdo->prepare("
     SELECT p.paper_id 
        FROM papers p
        WHERE (
            SELECT COUNT(DISTINCT annotator_id) 
            FROM annotations 
            WHERE paper_id = p.paper_id
        ) < 3
        AND p.paper_id NOT IN (
            SELECT paper_id FROM annotator_papers WHERE annotator_id = ?
        )
        ORDER BY RAND()
        LIMIT 10
    ");
    
    $stmt->execute([$annotator_id]);
    $new_papers = $stmt->fetchAll(PDO::FETCH_COLUMN);
    
    // Assign these papers to the annotator
    $insert_stmt = $pdo->prepare("INSERT INTO annotator_papers (annotator_id, paper_id) VALUES (?, ?)");
    foreach ($new_papers as $paper_id) {
        $insert_stmt->execute([$annotator_id, $paper_id]);
    }
    
    // Re-fetch assigned papers
    $stmt = $pdo->prepare("
        SELECT ap.paper_id, ap.completed, ap.is_other_language, ap.is_annotator_confused
        FROM annotator_papers ap 
        WHERE ap.annotator_id = ?
        ORDER BY ap.assigned_at
    ");
    $stmt->execute([$annotator_id]);
    $assigned_papers = $stmt->fetchAll();
}

// Check if all papers are completed
$all_completed = true;
$current_paper_index = 0;

// Check if a specific paper was requested via URL parameter (?paper=N)
$requested_paper = isset($_GET['paper']) ? intval($_GET['paper']) : null;

if ($requested_paper !== null && $requested_paper >= 0 && $requested_paper < count($assigned_papers)) {
    // Use the requested paper index (allows navigation to previous/specific papers)
    $current_paper_index = $requested_paper;
    // Check if all are completed
    foreach ($assigned_papers as $paper) {
        if (!$paper['completed']) {
            $all_completed = false;
            break;
        }
    }
} else {
    // Default behavior: find first incomplete paper
    foreach ($assigned_papers as $index => $paper) {
        if (!$paper['completed']) {
            $all_completed = false;
            $current_paper_index = $index;
            break;
        }
    }
}

if ($all_completed) {
    header('Location: complete.php');
    exit;
}

// Get the current paper to annotate
$current_paper_id = $assigned_papers[$current_paper_index]['paper_id'];

// Get sections for this paper
$stmt = $pdo->prepare("
    SELECT * FROM paper_sections 
    WHERE paper_id = ? 
    ORDER BY section_order
");
$stmt->execute([$current_paper_id]);
$sections = $stmt->fetchAll();

// Get any existing annotations for this paper by this annotator
$stmt = $pdo->prepare("
    SELECT section_id, label, is_other_language, is_annotator_confused 
    FROM annotations 
    WHERE annotator_id = ? AND paper_id = ?
");
$stmt->execute([$annotator_id, $current_paper_id]);
$existing_annotations = [];
foreach ($stmt->fetchAll() as $ann) {
    $existing_annotations[$ann['section_id']] = $ann;
}

// Get unique headers
$headers = [];
foreach ($sections as $section) {
    if (!empty($section['extracted_headers'])) {
        $header_lines = explode("\n", str_replace("\\n", "\n", $section['extracted_headers']));
        foreach ($header_lines as $h) {
            $h = trim($h);
            if (!empty($h) && !in_array($h, $headers)) {
                $headers[] = $h;
            }
        }
    }
}

// Retrieve paper-level flags directly from the assigned_papers array
$current_paper_data = $assigned_papers[$current_paper_index];
$is_other_language = $current_paper_data['is_other_language'] ? true : false;
$is_confused = $current_paper_data['is_annotator_confused'] ? true : false;

$total_papers = count($assigned_papers);
$labels = ['introduction', 'lit_review', 'methods', 'results', 'discussion', 'conclusion', 'development', 'case_report', 'something_else', 'ambiguous'];
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Annotate Paper - Scientific Paper Annotation</title>
    <link rel="stylesheet" href="css/styles.css">
</head>
<body>
    <div id="app-container">
        <header id="app-header">
            <div class="header-content">
                <h2 id="paper-info">
                    Paper <?php echo $current_paper_index + 1; ?> of <?php echo $total_papers; ?>
                    <span class="paper-id">ID: <?php echo htmlspecialchars($current_paper_id); ?></span>
                </h2>
                <div class="header-actions">
                    <button type="button" class="btn btn-primary btn-small" onclick="window.open('guidelines.pdf', '_blank')">
                        View Guidelines
                    </button>
                </div>
            </div>
            <div class="progress-bar">
                <div class="progress-fill" style="width: <?php echo (($current_paper_index) / $total_papers) * 100; ?>%"></div>
            </div>
        </header>

        <form id="annotation-form" action="save_annotation.php" method="POST">
            <input type="hidden" name="csrf_token" value="<?php echo $csrf_token; ?>">
            <input type="hidden" name="paper_id" value="<?php echo htmlspecialchars($current_paper_id); ?>">
            <input type="hidden" name="paper_index" value="<?php echo $current_paper_index; ?>">

            <div class="main-layout">
                <aside id="headers-panel" class="panel">
                    <h3>Extracted Headers</h3>
                    <ul id="headers-list">
                        <?php if (empty($headers)): ?>
                            <li class="no-headers">No headers found in "extracted" column.</li>
                        <?php else: ?>
                            <?php foreach ($headers as $header): ?>
                                <li><?php echo htmlspecialchars($header); ?></li>
                            <?php endforeach; ?>
                        <?php endif; ?>
                    </ul>
                </aside>

                <main id="annotation-panel-wrapper">
                    <div id="annotation-panel">
                        <?php if (empty($sections)): ?>
                            <div class="error-message">
                                <p>No sections found for this paper. Please contact the study administrator.</p>
                            </div>
                        <?php else: ?>
                            <?php foreach ($sections as $section): ?>
                                <?php 
                                    $existing = $existing_annotations[$section['id']] ?? null;
                                    $selected_label = $existing['label'] ?? '';
                                ?>
                                <div class="annotation-row">
                                    <div class="section-text"><?php echo nl2br(htmlspecialchars($section['section_text'])); ?></div>
                                    <div class="section-controls">
                                        <select name="labels[<?php echo $section['id']; ?>]" class="annotation-select">
                                            <option value="">-- Select Label --</option>
                                            <?php foreach ($labels as $label): ?>
                                                <option value="<?php echo $label; ?>" <?php echo $selected_label === $label ? 'selected' : ''; ?>>
                                                    <?php echo $label; ?>
                                                </option>
                                            <?php endforeach; ?>
                                        </select>
                                    </div>
                                </div>
                            <?php endforeach; ?>
                        <?php endif; ?>
                    </div>
                </main>
            </div>

            <footer id="controls">
                <div id="paper-flags">
                    <label>
                        <input type="checkbox" name="is_other_language" value="1" <?php echo $is_other_language ? 'checked' : ''; ?>>
                        Other Language
                    </label>
                    <label>
                        <input type="checkbox" name="is_confused" value="1" <?php echo $is_confused ? 'checked' : ''; ?>>
                        Annotator Unsure
                    </label>
                </div>
                <div class="control-buttons">
                    <?php if ($current_paper_index > 0): ?>
                        <button type="submit" name="action" value="previous" class="btn btn-secondary">
                            Previous Paper
                        </button>
                    <?php endif; ?>
                    <button type="submit" name="action" value="save" class="btn btn-secondary">
                        Save Progress
                    </button>
                    <button type="submit" name="action" value="next" class="btn btn-primary">
                        <?php echo $current_paper_index === $total_papers - 1 ? 'Finish & Submit' : 'Next Paper'; ?>
                    </button>
                </div>
            </footer>
        </form>
    </div>

    <script>
        document.getElementById('annotation-form').addEventListener('submit', function(e) {
            const action = e.submitter.value;
            
            // For previous button, don't validate - just save and go back
            if (action === 'previous') {
                // Let it submit without validation
                return;
            }
            
            if (action === 'next' || action === 'save') {
                const isOtherLanguage = document.querySelector('input[name="is_other_language"]').checked;
                const selects = document.querySelectorAll('.annotation-select');
                let allSelected = true;
                
                selects.forEach(select => {
                    if (!select.value) {
                        allSelected = false;
                        select.classList.add('error');
                    } else {
                        select.classList.remove('error');
                    }
                });
                
                // If trying to move to next paper without completing all sections
                if (!allSelected && action === 'next') {
                    // Allow if marked as other language
                    if (isOtherLanguage) {
                        return; // Allow submission
                    }
                    
                    // Otherwise, block and show error
                    e.preventDefault();
                    alert('You must label all sections before proceeding to the next paper. If this paper is in another language, please check the "Other Language" box.');
                    return;
                }
            }
        });

        // Remove error class on change
        document.querySelectorAll('.annotation-select').forEach(select => {
            select.addEventListener('change', function() {
                if (this.value) {
                    this.classList.remove('error');
                }
            });
        });
    </script>
</body>
</html>
