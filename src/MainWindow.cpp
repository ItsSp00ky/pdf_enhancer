#include "MainWindow.h"

#include "DocumentProcessor.h"

#include <QApplication>
#include <QDragEnterEvent>
#include <QFileDialog>
#include <QFileInfo>
#include <QFuture>
#include <QHBoxLayout>
#include <QIcon>
#include <QImage>
#include <QLabel>
#include <QMessageBox>
#include <QMimeData>
#include <QPixmap>
#include <QPushButton>
#include <QSlider>
#include <QUrl>
#include <QVBoxLayout>
#include <QDialog>
#include <QtConcurrent/QtConcurrent>
#include <QDesktopServices>

namespace {
bool isSupportedFile(const QString& path) {
    QString p = path.toLower();
    return p.endsWith(".pdf") ||
           p.endsWith(".jpg") ||
           p.endsWith(".jpeg") ||
           p.endsWith(".png") ||
           p.endsWith(".bmp") ||
           p.endsWith(".tiff") ||
           p.endsWith(".tif");
}
} // namespace

MainWindow::MainWindow(QWidget* parent) : QMainWindow(parent) {
    setWindowTitle("PDF Enhancer");
    resize(640, 480);
    setAcceptDrops(true);

    // Try loading application icon
    QString appDir = QApplication::applicationDirPath();
    if (QFileInfo::exists(appDir + "/scanner.png")) {
        setWindowIcon(QIcon(appDir + "/scanner.png"));
    } else if (QFileInfo::exists(appDir + "/scanner.ico")) {
        setWindowIcon(QIcon(appDir + "/scanner.ico"));
    }

    auto* central = new QWidget(this);
    auto* layout = new QVBoxLayout(central);
    layout->setSpacing(15);
    layout->setContentsMargins(25, 25, 25, 25);

    // 1. Title
    titleLabel_ = new QLabel("PDF Clean Scanner", this);
    QFont titleFont = titleLabel_->font();
    titleFont.setPointSize(20);
    titleFont.setBold(true);
    titleLabel_->setFont(titleFont);
    titleLabel_->setAlignment(Qt::AlignCenter);
    layout->addWidget(titleLabel_);

    // 2. File Selection Box
    auto* fileRow = new QHBoxLayout();
    fileLabel_ = new QLabel("Drag & drop files here or browse", this);
    fileLabel_->setStyleSheet("color: #888888; font-size: 13px;");
    browseButton_ = new QPushButton("Browse", this);
    browseButton_->setFixedHeight(36);
    fileRow->addWidget(fileLabel_, 1);
    fileRow->addWidget(browseButton_);
    layout->addLayout(fileRow);

    // 3. Quality Settings
    auto* settingsRow = new QVBoxLayout();
    dpiLabel_ = new QLabel("Scan Quality (DPI): 200", this);
    dpiSlider_ = new QSlider(Qt::Horizontal, this);
    dpiSlider_->setRange(100, 400);
    dpiSlider_->setSingleStep(50);
    dpiSlider_->setValue(200);
    settingsRow->addWidget(dpiLabel_);
    settingsRow->addWidget(dpiSlider_);
    layout->addLayout(settingsRow);

    // 4. Action Buttons
    auto* actionRow = new QHBoxLayout();
    previewButton_ = new QPushButton("Preview First", this);
    previewButton_->setFixedHeight(46);
    QFont btnFont = previewButton_->font();
    btnFont.setBold(true);
    previewButton_->setFont(btnFont);

    convertButton_ = new QPushButton("Convert & Save", this);
    convertButton_->setFixedHeight(46);
    convertButton_->setFont(btnFont);

    actionRow->addWidget(previewButton_);
    actionRow->addWidget(convertButton_);
    layout->addLayout(actionRow);

    // 5. Status
    statusLabel_ = new QLabel("Ready", this);
    statusLabel_->setAlignment(Qt::AlignCenter);
    statusLabel_->setStyleSheet("color: #888888; font-size: 12px;");
    layout->addWidget(statusLabel_);

    // 6. GitHub Footer
    auto* githubButton = new QPushButton("Developed by @ItsSp00ky | GitHub", this);
    githubButton->setFlat(true);
    githubButton->setCursor(Qt::PointingHandCursor);
    githubButton->setStyleSheet("color: #3B8ED0; text-decoration: underline; font-size: 11px;");
    layout->addWidget(githubButton, 0, Qt::AlignCenter);

    setCentralWidget(central);

    connect(browseButton_, &QPushButton::clicked, this, &MainWindow::browseFiles);
    connect(previewButton_, &QPushButton::clicked, this, &MainWindow::previewFirst);
    connect(convertButton_, &QPushButton::clicked, this, &MainWindow::convertAndSave);
    connect(dpiSlider_, &QSlider::valueChanged, this, &MainWindow::dpiChanged);
    connect(&watcher_, &QFutureWatcher<ProcessingResult>::finished, this, &MainWindow::onProcessingFinished);
    connect(githubButton, &QPushButton::clicked, this, []() {
        QDesktopServices::openUrl(QUrl("https://github.com/ItsSp00ky/pdf_enhancer"));
    });
}

MainWindow::~MainWindow() {
    watcher_.cancel();
    watcher_.waitForFinished();
}

void MainWindow::dragEnterEvent(QDragEnterEvent* event) {
    if (event->mimeData()->hasUrls()) {
        event->acceptProposedAction();
    }
}

void MainWindow::dropEvent(QDropEvent* event) {
    QStringList accepted;
    const auto urls = event->mimeData()->urls();
    for (const auto& url : urls) {
        QString path = url.toLocalFile();
        if (isSupportedFile(path)) {
            accepted << path;
        }
    }

    if (accepted.isEmpty()) {
        QMessageBox::warning(this, "Invalid Files", "Please drop a PDF or supported image files (JPG, PNG, BMP, TIFF).");
        return;
    }

    inputFiles_ = accepted;
    updateFileLabel();
    statusLabel_->setText(QString("Detected %1 via drag & drop. Ready.").arg(describeSelection(inputFiles_)));
    statusLabel_->setStyleSheet("color: #2ECC71; font-weight: bold;");
}

void MainWindow::browseFiles() {
    QStringList files = QFileDialog::getOpenFileNames(
        this,
        "Select PDF or Image Files",
        {},
        "Supported Files (*.pdf *.jpg *.jpeg *.png *.bmp *.tiff *.tif);;PDF Files (*.pdf);;Image Files (*.jpg *.jpeg *.png *.bmp *.tiff);;All Files (*)"
    );

    if (!files.isEmpty()) {
        inputFiles_ = files;
        updateFileLabel();
        statusLabel_->setText(QString("Detected %1. Ready.").arg(describeSelection(inputFiles_)));
        statusLabel_->setStyleSheet("color: #2ECC71; font-weight: bold;");
    }
}

void MainWindow::previewFirst() {
    if (!validateInput()) {
        return;
    }
    processAsync(QString(), true);
}

void MainWindow::convertAndSave() {
    if (!validateInput()) {
        return;
    }

    QString output = QFileDialog::getSaveFileName(
        this,
        "Save Scanned PDF As",
        defaultOutputName(),
        "PDF Files (*.pdf)"
    );

    if (output.isEmpty()) {
        return;
    }

    // Check that destination does not overwrite source
    for (const auto& in : inputFiles_) {
        if (QFileInfo(in).canonicalFilePath() == QFileInfo(output).canonicalFilePath()) {
            QMessageBox::critical(this, "Invalid Destination", "Please choose a different name so the source file is not overwritten.");
            return;
        }
    }

    processAsync(output, false);
}

void MainWindow::dpiChanged(int value) {
    dpiLabel_->setText(QString("Scan Quality (DPI): %1").arg(value));
}

void MainWindow::onProcessingFinished() {
    auto result = watcher_.result();
    setBusy(false, "Ready");

    if (!result.error.isEmpty()) {
        QMessageBox::critical(this, "Error", result.error);
        statusLabel_->setText("Processing failed.");
        statusLabel_->setStyleSheet("color: #E74C3C;");
        return;
    }

    if (pendingPreviewOnly_) {
        if (result.processed.empty()) {
            QMessageBox::warning(this, "Preview", "No pages available for preview.");
            return;
        }

        int currentDpi = dpiSlider_->value();
        cv::Mat first = result.processed.front();
        QImage preview = first.channels() == 1
            ? QImage(first.data, first.cols, first.rows, static_cast<int>(first.step), QImage::Format_Grayscale8).copy()
            : QImage(first.data, first.cols, first.rows, static_cast<int>(first.step), QImage::Format_RGB888).copy();

        auto* dlg = new QDialog(this);
        dlg->setWindowTitle(QString("Preview - %1×%2 px @ %3 DPI").arg(first.cols).arg(first.rows).arg(currentDpi));
        dlg->resize(620, 720);
        auto* l = new QVBoxLayout(dlg);

        auto* infoLabel = new QLabel(QString("Previewing First Page • %1×%2 px (%3 DPI)").arg(first.cols).arg(first.rows).arg(currentDpi), dlg);
        infoLabel->setAlignment(Qt::AlignCenter);
        QFont infoFont = infoLabel->font();
        infoFont.setBold(true);
        infoLabel->setFont(infoFont);
        l->addWidget(infoLabel);

        auto* imgLabel = new QLabel(dlg);
        imgLabel->setAlignment(Qt::AlignCenter);
        imgLabel->setPixmap(QPixmap::fromImage(preview).scaled(560, 640, Qt::KeepAspectRatio, Qt::SmoothTransformation));
        l->addWidget(imgLabel);
        dlg->setLayout(l);
        dlg->exec();
        dlg->deleteLater();
        return;
    }

    QString saveError;
    if (!DocumentProcessor::saveAsPdf(result.processed, pendingOutputPath_, dpiSlider_->value(), &saveError)) {
        QMessageBox::critical(this, "Save Failed", saveError);
        statusLabel_->setText("Failed to save PDF.");
        statusLabel_->setStyleSheet("color: #E74C3C;");
        return;
    }

    statusLabel_->setText("Conversion Complete!");
    statusLabel_->setStyleSheet("color: #2ECC71; font-weight: bold;");
    QMessageBox::information(this, "Success", QString("File saved successfully:\n%1").arg(pendingOutputPath_));
    QDesktopServices::openUrl(QUrl::fromLocalFile(pendingOutputPath_));
}

QString MainWindow::describeSelection(const QStringList& files) const {
    int pdfCount = 0;
    int imgCount = 0;
    for (const auto& file : files) {
        if (DocumentProcessor::isPdf(file)) {
            pdfCount++;
        } else {
            imgCount++;
        }
    }

    QStringList parts;
    if (pdfCount > 0) {
        parts << QString("%1 PDF%2").arg(pdfCount).arg(pdfCount > 1 ? "s" : "");
    }
    if (imgCount > 0) {
        parts << QString("%1 image%2").arg(imgCount).arg(imgCount > 1 ? "s" : "");
    }
    return parts.join(" + ");
}

void MainWindow::updateFileLabel() {
    if (inputFiles_.isEmpty()) {
        fileLabel_->setText("Drag & drop files here or browse");
        fileLabel_->setStyleSheet("color: #888888;");
        return;
    }
    if (inputFiles_.size() == 1) {
        fileLabel_->setText(QFileInfo(inputFiles_.first()).fileName());
    } else {
        fileLabel_->setText(QString("%1 files selected (%2)").arg(inputFiles_.size()).arg(describeSelection(inputFiles_)));
    }
    fileLabel_->setStyleSheet("color: #000000; font-weight: bold;");
}

bool MainWindow::validateInput() const {
    if (watcher_.isRunning()) {
        QMessageBox::information(const_cast<MainWindow*>(this), "Busy", "Processing is already in progress.");
        return false;
    }
    if (inputFiles_.isEmpty()) {
        QMessageBox::warning(const_cast<MainWindow*>(this), "Missing Input", "Please select or drop files first.");
        return false;
    }
    return true;
}

QString MainWindow::defaultOutputName() const {
    QString base = QFileInfo(inputFiles_.first()).completeBaseName();
    return QString("%1_scanned.pdf").arg(base);
}

void MainWindow::setBusy(bool busy, const QString& statusText) {
    browseButton_->setEnabled(!busy);
    previewButton_->setEnabled(!busy);
    convertButton_->setEnabled(!busy);
    dpiSlider_->setEnabled(!busy);
    convertButton_->setText(busy ? "Processing..." : "Convert & Save");
    statusLabel_->setText(statusText);
    statusLabel_->setStyleSheet("color: #E67E22;");
}

void MainWindow::processAsync(const QString& outputPath, bool previewOnly) {
    pendingOutputPath_ = outputPath;
    pendingPreviewOnly_ = previewOnly;

    setBusy(true, previewOnly ? "Generating preview..." : "Scanning pages...");

    QStringList files = previewOnly ? QStringList{inputFiles_.first()} : inputFiles_;
    int dpi = dpiSlider_->value();

    QFuture<ProcessingResult> future = QtConcurrent::run([files, dpi, previewOnly]() -> ProcessingResult {
        ProcessingResult result;
        QString error;
        auto pages = DocumentProcessor::loadPages(files, dpi, &error);
        if (!error.isEmpty()) {
            result.error = error;
            return result;
        }

        if (previewOnly && !pages.empty()) {
            result.processed.push_back(DocumentProcessor::processSinglePage(pages.front(), dpi));
        } else {
            for (const auto& page : pages) {
                result.processed.push_back(DocumentProcessor::processSinglePage(page, dpi));
            }
        }

        if (result.processed.empty()) {
            result.error = "No pages were processed.";
        }
        return result;
    });

    watcher_.setFuture(future);
}
