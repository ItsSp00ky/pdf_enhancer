#pragma once

#include <QFutureWatcher>
#include <QMainWindow>
#include <QStringList>

#include <opencv2/core.hpp>

class QLabel;
class QPushButton;
class QSlider;

class MainWindow : public QMainWindow {
    Q_OBJECT
public:
    explicit MainWindow(QWidget* parent = nullptr);
    ~MainWindow() override;

protected:
    void dragEnterEvent(QDragEnterEvent* event) override;
    void dropEvent(QDropEvent* event) override;

private slots:
    void browseFiles();
    void previewFirst();
    void convertAndSave();
    void dpiChanged(int value);
    void onProcessingFinished();

private:
    struct ProcessingResult {
        std::vector<cv::Mat> processed;
        QString error;
    };

    void updateFileLabel();
    bool validateInput() const;
    QString defaultOutputName() const;
    void setBusy(bool busy, const QString& statusText);
    void processAsync(const QString& outputPath, bool previewOnly);
    QString describeSelection(const QStringList& files) const;

    QLabel* titleLabel_{nullptr};
    QLabel* fileLabel_{nullptr};
    QPushButton* browseButton_{nullptr};
    QLabel* dpiLabel_{nullptr};
    QSlider* dpiSlider_{nullptr};
    QPushButton* previewButton_{nullptr};
    QPushButton* convertButton_{nullptr};
    QLabel* statusLabel_{nullptr};

    QStringList inputFiles_;
    QString pendingOutputPath_;
    bool pendingPreviewOnly_{false};
    QFutureWatcher<ProcessingResult> watcher_;
};
