<?php
/**
 * Admin Dashboard
 * Simple dashboard to monitor annotation progress
 * 
 * IMPORTANT: In production, add authentication to this page!
 */

require_once 'includes/config.php';

// Simple password protection (change this or implement proper auth)
$admin_password = 'validationtest';

if (!isset($_SESSION['admin_logged_in'])) {
    if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['password'])) {
        if ($_POST['password'] === $admin_password) {
            $_SESSION['admin_logged_in'] = true;
        } else {
            $error = 'Invalid password';
        }
    }
    
    if (!isset($_SESSION['admin_logged_in'])) {
        ?>
        <!DOCTYPE html>
        <html><head><title>Admin Login</title><link rel="stylesheet" href="css/styles.css"></head>
        <body><div class="container"><div class="card welcome-card">
            <h1>Admin Login</h1>
            <?php if (isset($error)): ?><p style="color: red;"><?php echo $error; ?></p><?php endif; ?>
            <form method="POST"><div class="form-group">
                <label>Password</label>
                <input type="password" name="password" required>
            </div>
            <button type="submit" class="btn btn-primary">Login</button>
            </form>
        </div></div></body></html>
        <?php
        exit;
    }
}

$pdo = getDBConnection();

// Get statistics
$stats = [];

// Total papers
$stmt = $pdo->query("SELECT COUNT(*) FROM papers");
$stats['total_papers'] = $stmt->fetchColumn();

// Papers by annotation count
$stmt = $pdo->query("
    SELECT 
        SUM(CASE WHEN n_annotations = 0 THEN 1 ELSE 0 END) as zero,
        SUM(CASE WHEN n_annotations = 1 THEN 1 ELSE 0 END) as one,
        SUM(CASE WHEN n_annotations = 2 THEN 1 ELSE 0 END) as two,
        SUM(CASE WHEN n_annotations >= 3 THEN 1 ELSE 0 END) as three_plus
    FROM papers
");
$paper_counts = $stmt->fetch();

// Total annotators
$stmt = $pdo->query("SELECT COUNT(*) FROM annotators");
$stats['total_annotators'] = $stmt->fetchColumn();

// Qualified annotators (passed screening and attention)
$stmt = $pdo->query("SELECT COUNT(*) FROM annotators WHERE passed_screening = 1 AND passed_attention_check = 1");
$stats['qualified_annotators'] = $stmt->fetchColumn();

// Total annotations
$stmt = $pdo->query("SELECT COUNT(DISTINCT CONCAT(annotator_id, '-', paper_id)) FROM annotations");
$stats['total_paper_annotations'] = $stmt->fetchColumn();

// Recent annotators
$stmt = $pdo->query("
    SELECT a.prolific_id, a.created_at, a.passed_screening, a.passed_attention_check,
           COUNT(DISTINCT ap.paper_id) as papers_completed
    FROM annotators a
    LEFT JOIN annotator_papers ap ON a.annotator_id = ap.annotator_id AND ap.completed = 1
    GROUP BY a.annotator_id
    ORDER BY a.created_at DESC
    LIMIT 20
");
$recent_annotators = $stmt->fetchAll();

// Handle export request
if (isset($_GET['export'])) {
    header('Content-Type: text/csv');
    header('Content-Disposition: attachment; filename="annotations_export_' . date('Y-m-d_H-i-s') . '.csv"');
    
    $stmt = $pdo->query("
        SELECT 
            a.prolific_id,
            an.paper_id,
            ps.section_order,
            ps.start_position as start,
            an.label,
            CASE WHEN an.is_other_language THEN 'True' ELSE 'False' END as is_other_language,
            CASE WHEN an.is_annotator_confused THEN 'True' ELSE 'False' END as is_annotator_confused,
            an.created_at
        FROM annotations an
        JOIN annotators a ON an.annotator_id = a.annotator_id
        JOIN paper_sections ps ON an.section_id = ps.id
        ORDER BY a.prolific_id, an.paper_id, ps.section_order
    ");
    
    $output = fopen('php://output', 'w');
    fputcsv($output, ['prolific_id', 'paper_id', 'section_order', 'start', 'label', 'is_other_language', 'is_annotator_confused', 'created_at']);
    
    while ($row = $stmt->fetch()) {
        fputcsv($output, $row);
    }
    fclose($output);
    exit;
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Dashboard - Paper Annotation</title>
    <link rel="stylesheet" href="css/styles.css">
    <style>
        .dashboard { max-width: 1200px; margin: 0 auto; padding: 20px; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .stat-card { background: white; border-radius: 8px; padding: 20px; box-shadow: var(--card-shadow); }
        .stat-card h3 { margin: 0 0 10px 0; color: var(--text-secondary); font-size: 0.9rem; }
        .stat-card .value { font-size: 2rem; font-weight: 700; color: var(--primary-color); }
        .stat-card .sub { font-size: 0.85rem; color: var(--text-secondary); margin-top: 5px; }
        table { width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: var(--card-shadow); }
        th, td { padding: 12px 15px; text-align: left; border-bottom: 1px solid var(--border-color); }
        th { background: var(--panel-bg); font-weight: 600; }
        .badge { display: inline-block; padding: 3px 8px; border-radius: 4px; font-size: 0.8rem; }
        .badge-success { background: #d1fae5; color: #065f46; }
        .badge-error { background: #fee2e2; color: #991b1b; }
        .badge-warning { background: #fef3c7; color: #92400e; }
        .actions { margin-bottom: 20px; display: flex; gap: 10px; }
    </style>
</head>
<body style="background: #f3f4f6;">
    <div class="dashboard">
        <h1>Annotation Dashboard</h1>
        
        <div class="actions">
            <a href="?export=1" class="btn btn-primary">Export All Annotations (CSV)</a>
            <a href="?logout=1" class="btn btn-secondary">Logout</a>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <h3>Total Papers</h3>
                <div class="value"><?php echo number_format($stats['total_papers']); ?></div>
            </div>
            <div class="stat-card">
                <h3>Completed (3+ annotations)</h3>
                <div class="value"><?php echo number_format($paper_counts['three_plus'] ?? 0); ?></div>
                <div class="sub"><?php echo $stats['total_papers'] > 0 ? round(($paper_counts['three_plus'] ?? 0) / $stats['total_papers'] * 100, 1) : 0; ?>% complete</div>
            </div>
            <div class="stat-card">
                <h3>Papers In Progress</h3>
                <div class="value"><?php echo number_format(($paper_counts['one'] ?? 0) + ($paper_counts['two'] ?? 0)); ?></div>
                <div class="sub">1-2 annotations</div>
            </div>
            <div class="stat-card">
                <h3>Papers Pending</h3>
                <div class="value"><?php echo number_format($paper_counts['zero'] ?? 0); ?></div>
                <div class="sub">0 annotations</div>
            </div>
            <div class="stat-card">
                <h3>Total Annotators</h3>
                <div class="value"><?php echo number_format($stats['total_annotators']); ?></div>
                <div class="sub"><?php echo $stats['qualified_annotators']; ?> qualified</div>
            </div>
            <div class="stat-card">
                <h3>Paper-Annotations</h3>
                <div class="value"><?php echo number_format($stats['total_paper_annotations']); ?></div>
                <div class="sub">Unique annotator-paper pairs</div>
            </div>
        </div>
        
        <h2>Recent Annotators</h2>
        <table>
            <thead>
                <tr>
                    <th>Prolific ID</th>
                    <th>Joined</th>
                    <th>Screening</th>
                    <th>Attention Check</th>
                    <th>Papers Completed</th>
                </tr>
            </thead>
            <tbody>
                <?php foreach ($recent_annotators as $ann): ?>
                <tr>
                    <td><?php echo htmlspecialchars($ann['prolific_id']); ?></td>
                    <td><?php echo date('M j, Y H:i', strtotime($ann['created_at'])); ?></td>
                    <td>
                        <?php if ($ann['passed_screening']): ?>
                            <span class="badge badge-success">Passed</span>
                        <?php else: ?>
                            <span class="badge badge-error">Failed</span>
                        <?php endif; ?>
                    </td>
                    <td>
                        <?php if ($ann['passed_attention_check']): ?>
                            <span class="badge badge-success">Passed</span>
                        <?php elseif ($ann['passed_screening']): ?>
                            <span class="badge badge-warning">Pending</span>
                        <?php else: ?>
                            <span class="badge badge-error">N/A</span>
                        <?php endif; ?>
                    </td>
                    <td><?php echo $ann['papers_completed']; ?>/10</td>
                </tr>
                <?php endforeach; ?>
            </tbody>
        </table>
    </div>
</body>
</html>
<?php
if (isset($_GET['logout'])) {
    unset($_SESSION['admin_logged_in']);
    header('Location: admin.php');
    exit;
}
?>
