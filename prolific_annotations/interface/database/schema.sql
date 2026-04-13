-- Database schema for Scientific Paper Annotation System
-- Run this script to set up the database

CREATE DATABASE IF NOT EXISTS paper_annotations;
USE paper_annotations;

-- Table for papers to be annotated
CREATE TABLE IF NOT EXISTS papers (
    paper_id VARCHAR(100) PRIMARY KEY,
    n_annotations INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table for paper sections (the actual content to annotate)
CREATE TABLE IF NOT EXISTS paper_sections (
    id INT AUTO_INCREMENT PRIMARY KEY,
    paper_id VARCHAR(100) NOT NULL,
    section_order INT NOT NULL,
    section_text TEXT NOT NULL,
    extracted_headers TEXT,
    start_position INT,
    FOREIGN KEY (paper_id) REFERENCES papers(paper_id) ON DELETE CASCADE,
    INDEX idx_paper_id (paper_id)
);

-- Table for annotators
CREATE TABLE IF NOT EXISTS annotators (
    annotator_id INT AUTO_INCREMENT PRIMARY KEY,
    prolific_id VARCHAR(100) UNIQUE NOT NULL,
    education_level VARCHAR(50) NOT NULL,
    english_fluency VARCHAR(50) NOT NULL,
    research_experience INT NOT NULL,
    passed_screening BOOLEAN DEFAULT FALSE,
    passed_attention_check BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table tracking which papers each annotator has seen
CREATE TABLE IF NOT EXISTS annotator_papers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    annotator_id INT NOT NULL,
    paper_id VARCHAR(100) NOT NULL,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (annotator_id) REFERENCES annotators(annotator_id) ON DELETE CASCADE,
    FOREIGN KEY (paper_id) REFERENCES papers(paper_id) ON DELETE CASCADE,
    UNIQUE KEY unique_annotator_paper (annotator_id, paper_id)
);

-- Table for storing annotations
CREATE TABLE IF NOT EXISTS annotations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    annotator_id INT NOT NULL,
    paper_id VARCHAR(100) NOT NULL,
    section_id INT NOT NULL,
    label VARCHAR(50) NOT NULL,
    is_other_language BOOLEAN DEFAULT FALSE,
    is_annotator_confused BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (annotator_id) REFERENCES annotators(annotator_id) ON DELETE CASCADE,
    FOREIGN KEY (paper_id) REFERENCES papers(paper_id) ON DELETE CASCADE,
    FOREIGN KEY (section_id) REFERENCES paper_sections(id) ON DELETE CASCADE,
    UNIQUE KEY unique_annotation (annotator_id, section_id)
);

-- Table for attention check papers (gold standard)
CREATE TABLE IF NOT EXISTS attention_check_papers (
    paper_id VARCHAR(100) PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table for attention check sections with correct answers
CREATE TABLE IF NOT EXISTS attention_check_sections (
    id INT AUTO_INCREMENT PRIMARY KEY,
    paper_id VARCHAR(100) NOT NULL,
    section_order INT NOT NULL,
    section_text TEXT NOT NULL,
    extracted_headers TEXT,
    correct_label VARCHAR(50) NOT NULL,
    FOREIGN KEY (paper_id) REFERENCES attention_check_papers(paper_id) ON DELETE CASCADE
);
