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
$csrf_token = generateCSRFToken();

// 1. Define the specific paper ID you want to use
$target_paper_id = '10607276';

// 2. Prepare the statement with a WHERE clause
$stmt = $pdo->prepare("
    SELECT acs.*
    FROM attention_check_sections acs
    WHERE acs.paper_id = :pid
    ORDER BY acs.section_order
");

// 3. Execute with the ID
$stmt->execute(['pid' => $target_paper_id]);
$sections = $stmt->fetchAll();

// Set paper_id for the form
$paper_id = $target_paper_id;

/*
// Get attention check paper
$stmt = $pdo->query("
    SELECT acs.*, acp.paper_id 
    FROM attention_check_sections acs
    JOIN attention_check_papers acp ON acs.paper_id = acp.paper_id
    ORDER BY acs.paper_id, acs.section_order
");
$attention_sections = $stmt->fetchAll();

// Group by paper
$attention_paper = [];
foreach ($attention_sections as $section) {
    $attention_paper[$section['paper_id']][] = $section;
}

// Get first attention check paper (or you can randomize)
$paper_id = array_key_first($attention_paper);
$sections = $attention_paper[$paper_id] ?? [];
*/

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

$labels = ['introduction', 'lit_review', 'methods', 'results', 'discussion', 'conclusion', 'development', 'case_report', 'something_else', 'ambiguous'];
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Screening Study - Scientific Paper Annotation</title>
    <link rel="stylesheet" href="css/styles.css">
</head>
<body>
    <div class="container full-width">
        <div class="card attention-card">
            <div class="attention-header">
                <h1>Screening Study</h1>
                <p class="subtitle">Before we begin, please complete this practice annotation to ensure you understand the task.</p>
            </div>

            <div class="info-box instruction-box">
                <h3>Instructions</h3>
                <p>Select the most appropriate label from the dropdown menu according to the guidelines.</p>
                <button type="button" class="btn btn-primary btn-small" onclick="window.open('guidelines.pdf', '_blank')">
                    Annotation Guidelines
                </button>
            </div>

            <form id="attention-form" action="process_attention.php" method="POST">
                <input type="hidden" name="csrf_token" value="<?php echo $csrf_token; ?>">
                <input type="hidden" name="paper_id" value="<?php echo htmlspecialchars($paper_id); ?>">

                <div class="annotation-layout">
                    <aside class="headers-panel">
                        <h3>Extracted Headers</h3>
                        <ul id="headers-list">
                            <?php if (empty($headers)): ?>
                                <li class="no-headers">No headers found for this paper.</li>
                            <?php else: ?>
                                <?php foreach ($headers as $header): ?>
                                    <li><?php echo htmlspecialchars($header); ?></li>
                                <?php endforeach; ?>
                            <?php endif; ?>
                        </ul>
                    </aside>

                    <main class="annotation-content">
                        <?php if (empty($sections)): ?>
                            <div class="error-message">
                                <p>No attention check paper is configured. Please contact the study administrator.</p>
                            </div>
                        <?php else: ?>
                            <?php foreach ($sections as $index => $section): ?>
                                <div class="annotation-row">
                                    <div class="section-text">
                                        <?php echo nl2br(htmlspecialchars($section['section_text'])); ?>
                                    </div>
                                    <div class="section-controls">
                                        <select name="labels[<?php echo $section['id']; ?>]" class="annotation-select" required>
                                            <option value="">-- Select Label --</option>
                                            <?php foreach ($labels as $label): ?>
                                                <option value="<?php echo $label; ?>"><?php echo $label; ?></option>
                                            <?php endforeach; ?>
                                        </select>
                                    </div>
                                </div>
                            <?php endforeach; ?>
                        <?php endif; ?>
                    </main>
                </div>

                <?php if (!empty($sections)): ?>
                    <div class="form-actions">
                        <button type="submit" class="btn btn-primary btn-large">
                            Submit & Continue
                        </button>
                    </div>
                <?php endif; ?>
            </form>
        </div>
    </div>

    <script>
        document.getElementById('attention-form').addEventListener('submit', function(e) {
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
            if (!allSelected) {
                e.preventDefault();
                alert('Please select a label for all sections before submitting.');
            }
        });
    </script>
</body>
</html>
